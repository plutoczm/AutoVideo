import json
import os
from typing import Any

import requests


SYSTEM_PROMPT = """You are a short-form film storyboard planner.
Return strict JSON only. Build an ORIGINAL story suitable for Douyin/TikTok/YouTube Shorts.
Do not use copyrighted character names, logos, exact costumes, or copied dialogue. If the user references a known franchise,
translate the request into broad genre/visual traits and an original cast.

Schema:
{
  "title": "...",
  "hook_text": "a very short opening hook shown/spoken in the first seconds",
  "style_prompt": "consistent visual style shared by every shot",
  "negative_prompt": "...",
  "characters": [
    {
      "id": "char_1",
      "name": "original character name",
      "visual_bible": "stable appearance description, clothes, colors, age, hair, face",
      "voice": "narrator|young_female|young_male|mature_female|mature_male"
    }
  ],
  "scenes": [
    {
      "id": "scene_01",
      "narration": "0-2 concise Chinese sentences",
      "dialogue_lines": [
        {"character_id": "char_1", "text": "short spoken line"}
      ],
      "character_ids": ["char_1"],
      "image_prompt": "English cinematic keyframe prompt",
      "motion_prompt": "English image-to-video motion/camera prompt",
      "duration_hint": 5
    }
  ]
}

Rules:
- 6 to 10 scenes for a 45-90 second short video.
- The first scene must hook immediately; introduce conflict, danger, surprise, or a strong question within the first 2-3 seconds.
- Use dialogue when it improves drama. Keep 0-3 dialogue lines per scene and always attach a valid character_id.
- Keep narration concise so the visuals can breathe.
- Maintain character identity, clothes and color palette across scenes.
- Make prompts cinematic: composition, lighting, lens/camera angle, environment, action.
- motion_prompt should describe restrained coherent movement and camera motion, not a new scene.
- Build a complete micro-story with hook, escalation, climax and a satisfying ending or cliffhanger.
"""


def _extract_json(text: str) -> dict[str, Any]:
    text = text.strip()
    if text.startswith("```"):
        text = text.strip("`")
        if text.startswith("json"):
            text = text[4:].lstrip()
    start = text.find("{")
    end = text.rfind("}")
    if start < 0 or end < start:
        raise ValueError("LLM response does not contain JSON")
    return json.loads(text[start : end + 1])


def _normalize_dialogue(project: dict[str, Any]) -> None:
    valid_ids = {c.get("id") for c in project.get("characters", []) if c.get("id")}
    for scene in project.get("scenes", []):
        lines = scene.get("dialogue_lines") or []
        normalized = []
        for item in lines:
            if not isinstance(item, dict):
                continue
            character_id = str(item.get("character_id", "")).strip()
            text = str(item.get("text", "")).strip()
            if character_id in valid_ids and text:
                normalized.append({"character_id": character_id, "text": text})
        scene["dialogue_lines"] = normalized

        # Backward compatibility for older saved storyboards.
        if not normalized and scene.get("dialogue"):
            ids = scene.get("character_ids") or []
            if ids and ids[0] in valid_ids:
                scene["dialogue_lines"] = [
                    {"character_id": ids[0], "text": str(scene["dialogue"]).strip()}
                ]


def plan_story(source: str) -> dict[str, Any]:
    base_url = os.getenv("LLM_BASE_URL", "https://api.deepseek.com/v1").rstrip("/")
    api_key = os.getenv("LLM_API_KEY", "")
    model = os.getenv("LLM_MODEL", "deepseek-chat")
    if not api_key:
        raise RuntimeError("LLM_API_KEY is required")

    response = requests.post(
        f"{base_url}/chat/completions",
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        json={
            "model": model,
            "temperature": 0.7,
            "response_format": {"type": "json_object"},
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": "Convert the following idea / novel excerpt into a short-film storyboard:\n\n" + source,
                },
            ],
        },
        timeout=120,
    )
    response.raise_for_status()
    content = response.json()["choices"][0]["message"]["content"]
    project = _extract_json(content)

    if not project.get("scenes"):
        raise ValueError("Storyboard has no scenes")
    project.setdefault("characters", [])
    project.setdefault("hook_text", project.get("title", ""))
    project.setdefault("style_prompt", "cinematic anime-inspired illustration, consistent character design")
    project.setdefault("negative_prompt", "low quality, blurry, deformed hands, extra fingers, text, watermark")
    _normalize_dialogue(project)
    return project


def character_prompt(character: dict[str, Any], style_prompt: str) -> str:
    return (
        f"character reference sheet, single original character, front view and three-quarter view, "
        f"neutral pose, clean background, {character['visual_bible']}, {style_prompt}, "
        "high detail, consistent design, no text, no watermark"
    )


def scene_prompt(project: dict[str, Any], scene: dict[str, Any]) -> str:
    by_id = {c["id"]: c for c in project.get("characters", [])}
    people = [by_id[cid]["visual_bible"] for cid in scene.get("character_ids", []) if cid in by_id]
    identity = "; ".join(people)
    parts = [scene.get("image_prompt", ""), project.get("style_prompt", "")]
    if identity:
        parts.append("character identity: " + identity)
    return ", ".join(part for part in parts if part)
