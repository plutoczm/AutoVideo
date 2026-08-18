# AutoVideo AI Studio

Creator-oriented AIGC story-to-video pipeline for producing vertical short films, AI comics/animation and novel adaptations for Douyin, TikTok and YouTube Shorts.

`main` is the continuously upgraded creator version. The original beginner demo is preserved on the `legacy/demo` branch.

## Product goal

AutoVideo is not designed as an AI slideshow maker. The project follows a creator workflow in which AI generates candidates and the user approves the visual identity and shots that are worth rendering.

```text
Story / novel excerpt / content idea
        ↓
LLM story adaptation
        ↓
Character bible + stable voice roles
        ↓
Storyboard / shot plan
        ↓
3x character candidates → human approval
        ↓
3x reference-conditioned keyframes → human approval
        ↓
2x image-to-video shots → human approval
        ↓
Narration + per-character dialogue TTS
        ↓
Native ambience + optional BGM mix
        ↓
Line-level subtitles + FFmpeg composition
        ↓
9:16 short film
```

For public demos, use original characters/stories or material you have permission to adapt.

## Why human review is built in

High-quality story video generation is mostly an iteration problem. A fully automatic pipeline tends to accept weak faces, broken hands, identity drift, bad staging and poor motion. AutoVideo therefore treats **candidate generation + selection** as part of the product rather than a manual workaround.

The current creator workflow supports:

- persistent project state under one episode directory;
- editable storyboard JSON before expensive media generation;
- multiple character-sheet candidates per character;
- approved reference images reused across scene generation;
- multiple keyframe candidates per scene;
- up to three selected character references supplied to supported image providers;
- multiple I2V candidates per scene;
- scene-level rerendering instead of restarting the whole episode;
- structured `dialogue_lines` with a stable voice role per character;
- finer subtitle timing from narration/dialogue segments;
- native ambience preservation plus optional user-supplied BGM;
- final H.264/AAC vertical MP4 composition.

## Current architecture

### Story planning

`autovideo/planner.py` converts an idea or novel excerpt into structured JSON containing:

- original character definitions;
- stable face / hair / wardrobe / color descriptions;
- voice roles;
- a short opening hook;
- 6-10 short-form scenes;
- keyframe prompts;
- motion/camera prompts;
- concise narration;
- per-character dialogue lines.

Example dialogue representation:

```json
{
  "narration": "暴风中心突然亮起一道金光。",
  "dialogue_lines": [
    {"character_id": "char_1", "text": "那不是闪电。"},
    {"character_id": "char_2", "text": "海图上根本没有那座岛。"}
  ]
}
```

### Creator project state

`autovideo/project_store.py` keeps generated assets and approvals under a project directory:

```text
outputs/projects/episode-01/
├── storyboard.json
├── selections.json
├── references/
│   └── char_1/
│       ├── candidate_01.png
│       ├── candidate_02.png
│       └── candidate_03.png
├── keyframes/
│   └── scene_01/
├── motion/
│   └── scene_01/
├── audio/
│   └── scene_01/
│       ├── segment_01.mp3
│       └── segment_02.mp3
├── scenes/
└── final/
    ├── final_story_no_bgm.mp4
    └── final_story.mp4
```

`selections.json` records the approved character image, keyframe and motion candidate for every item.

### Media providers

Two media paths are currently supported:

- `MEDIA_PROVIDER=gemini`: Gemini image generation + Veo image-to-video;
- `MEDIA_PROVIDER=comfy`: exported ComfyUI workflows for local/open-model experimentation.

The Python orchestration is model-agnostic. ComfyUI workflows can therefore be changed without rewriting story planning, review state, TTS or editing code.

### Character consistency

Character consistency is handled as a pipeline constraint instead of relying only on text prompts:

1. LLM produces one stable `visual_bible` per character.
2. Several character reference candidates are generated.
3. The creator approves one reference image.
4. Scene keyframes reuse approved reference assets.
5. Prompts explicitly preserve face, hair, wardrobe and palette while varying only composition/staging.
6. I2V prompts are constrained to preserve the approved keyframe rather than invent a new scene.

The exact identity-control mechanism depends on the selected provider. Gemini can use multiple reference images; ComfyUI can host IP-Adapter / PuLID / InstantID / StoryDiffusion-style workflows.

### Voice and sound

- Edge-TTS is the default no-cost fallback.
- `TTS_PROVIDER=http` can target a higher-quality CosyVoice/F5-TTS-compatible service.
- Narration uses the narrator voice role; each `dialogue_lines` item resolves to the corresponding character voice.
- Scene speech is synthesized in segments, concatenated, and reused for subtitle timing.
- If a generated video contains native ambience/effects, FFmpeg keeps it quietly underneath the controlled voice track.
- Final render can optionally loop a creator-supplied BGM track under the finished voice/ambience mix.

## Creator Review UI

The recommended way to work on publishable episodes is the staged Gradio review app:

```bash
python review_app.py
```

The UI has five stages:

1. **Storyboard** — create/load the episode, directly edit JSON, then save revised dialogue/prompts before media generation.
2. **Character Bible** — generate multiple character candidates and lock the chosen reference.
3. **Storyboard Keyframes** — generate multiple scene compositions using approved character references.
4. **I2V Shot Review** — generate and preview multiple motion candidates for the approved keyframe.
5. **Final Render** — run per-character TTS, preserve native ambience, optionally add BGM, burn subtitles and produce the final vertical MP4.

The first candidate is stored as a temporary default so rapid experiments can continue, but publishable work should explicitly review each important character and scene.

## First episode brief

A ready-to-use original episode brief is included at:

```text
examples/episode_01_story.txt
```

It describes a 45-60 second original cinematic-anime sea adventure called **《潮汐之眼》**, including character constraints, hook, plot beats, visual palette, sound requirements and continuity rules. It is intentionally original so it can be used as a public portfolio/creator test without relying on a named franchise.

Recommended first production run:

```text
1. python review_app.py
2. paste examples/episode_01_story.txt into Storyboard input
3. generate Storyboard and manually tighten dialogue/pacing
4. approve one character identity per role
5. approve one keyframe per scene
6. generate 2 I2V candidates for important scenes
7. add a licensed/owned BGM file if desired
8. render final_story.mp4
```

## Quick CLI

`studio.py` remains available as the automatic end-to-end path for quick experiments:

```bash
python studio.py "一个原创海上冒险故事：年轻航海士在暴风雨中发现一座会发光的失落岛屿"
```

For creator-quality work, prefer `review_app.py` because it avoids blindly accepting first generations.

## Installation

Python 3.11+ is recommended.

```bash
python -m venv .venv

# Windows
.venv\Scripts\activate

# macOS / Linux
source .venv/bin/activate

pip install -r requirements.txt
```

Install `ffmpeg` and `ffprobe` separately and make sure both commands are available on `PATH`.

## Configuration

```bash
cp .env.example .env
```

Default cloud creator path:

```text
LLM_API_KEY=...
LLM_BASE_URL=https://api.deepseek.com/v1
LLM_MODEL=deepseek-chat

MEDIA_PROVIDER=gemini
GEMINI_API_KEY=...
GEMINI_IMAGE_MODEL=gemini-3.1-flash-image-preview
GEMINI_VIDEO_MODEL=veo-3.1-fast-generate-preview
GEMINI_VIDEO_RESOLUTION=720p
GEMINI_VIDEO_DURATION=8

VIDEO_WIDTH=1080
VIDEO_HEIGHT=1920
```

Use the fast video model while iterating. Strong shots can later be rerendered with a higher-quality compatible model without changing the orchestration code.

For local workflows:

```text
MEDIA_PROVIDER=comfy
COMFYUI_URL=http://127.0.0.1:8188
COMFY_IMAGE_WORKFLOW=workflows/image_api.json
COMFY_VIDEO_WORKFLOW=workflows/video_api.json
```

See `workflows/README.md` for the API-format token convention.

## Project structure

```text
AutoVideo/
├── autovideo/
│   ├── planner.py          # story -> characters + storyboard + dialogue lines
│   ├── project_store.py    # project assets + approvals
│   ├── creator.py          # staged candidate/review/render pipeline
│   ├── gemini_media.py     # Gemini image + Veo I2V provider
│   ├── comfy.py            # model-agnostic ComfyUI adapter
│   ├── tts.py              # Edge-TTS / HTTP high-quality TTS adapter
│   └── composer.py         # FFmpeg audio, subtitles, BGM and final composition
├── examples/
│   └── episode_01_story.txt
├── workflows/              # optional local image/video workflows
├── review_app.py           # creator review UI
├── studio.py               # quick automatic CLI
├── requirements.txt
├── .env.example
├── UPSTREAM.md
└── README.md
```

## Next creator-quality milestones

The next work should improve actual publishable output rather than add unrelated infrastructure:

- direct high-quality multi-speaker CosyVoice integration instead of only the generic HTTP adapter;
- SFX library/generation and automatic ducking/loudness normalization;
- richer shot grammar (close-up / medium / wide / POV / insert / establishing shot);
- explicit continuity memory for props, damage, weather and time-of-day;
- automatic visual quality checks to flag identity drift and malformed frames before I2V;
- alternate video providers so the same keyframe can be compared across multiple models;
- episode metadata and reusable cast assets for a repeatable series workflow.

## Legacy demo

The earlier learning version based on `Stable Diffusion -> Edge-TTS -> image/video composition` is preserved on:

```text
legacy/demo
```

It remains useful for learning the basic pipeline, while `main` is reserved for the creator-facing system.

## Open-source provenance

The repository originally started from the MIT-licensed `vasanthgitt/GenAI-Video_Generation` learning project. The current creator branch has moved to a substantially different orchestration architecture, while the original attribution remains in `UPSTREAM.md` and `LICENSE`.
