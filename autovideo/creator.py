import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from autovideo.comfy import ComfyUIRunner
from autovideo.composer import (
    concat_and_subtitle,
    image_to_motion_fallback,
    media_duration,
    render_scene,
)
from autovideo.gemini_media import GeminiMediaProvider
from autovideo.planner import character_prompt, plan_story, scene_prompt
from autovideo.project_store import ProjectStore
from autovideo.tts import generate_tts


@dataclass
class CreatorSettings:
    media_provider: str
    image_workflow: str
    video_workflow: str
    width: int
    height: int
    base_seed: int


def settings_from_env() -> CreatorSettings:
    provider = os.getenv("MEDIA_PROVIDER", "gemini").lower()
    if provider not in {"gemini", "comfy"}:
        raise RuntimeError("MEDIA_PROVIDER must be gemini or comfy")
    return CreatorSettings(
        media_provider=provider,
        image_workflow=os.getenv("COMFY_IMAGE_WORKFLOW", "workflows/image_api.json"),
        video_workflow=os.getenv("COMFY_VIDEO_WORKFLOW", "workflows/video_api.json"),
        width=int(os.getenv("VIDEO_WIDTH", "1080")),
        height=int(os.getenv("VIDEO_HEIGHT", "1920")),
        base_seed=int(os.getenv("BASE_SEED", "42")),
    )


class CreatorPipeline:
    """Human-in-the-loop story-to-video pipeline.

    The pipeline is deliberately staged: plan -> character candidates -> approved character
    references -> keyframe candidates -> approved keyframes -> I2V candidates -> approved
    shots -> audio/edit. Expensive generation is therefore rerunnable at scene granularity.
    """

    def __init__(self, root: str | Path):
        self.store = ProjectStore(root)
        self.store.ensure()
        self.cfg = settings_from_env()
        self.gemini = GeminiMediaProvider() if self.cfg.media_provider == "gemini" else None
        self.comfy = ComfyUIRunner() if self.cfg.media_provider == "comfy" else None
        if self.comfy and not Path(self.cfg.image_workflow).exists():
            raise RuntimeError(
                f"Missing image workflow: {self.cfg.image_workflow}. See workflows/README.md."
            )

    def create_storyboard(self, source: str) -> dict[str, Any]:
        project = plan_story(source)
        self.store.save_storyboard(project)
        return project

    def _image(
        self,
        prompt: str,
        output_path: Path,
        *,
        references: list[Path] | None = None,
        seed: int = 42,
    ) -> Path:
        if self.gemini:
            return self.gemini.generate_image(
                prompt,
                output_path,
                reference_images=references or [],
            )
        assert self.comfy is not None
        return self.comfy.run(
            self.cfg.image_workflow,
            output_path,
            prompt=prompt,
            negative_prompt=self.store.load_storyboard().get("negative_prompt", ""),
            reference_image=(references or [None])[0],
            width=self.cfg.width,
            height=self.cfg.height,
            seed=seed,
        )

    def _video(self, prompt: str, keyframe: Path, output_path: Path, seed: int) -> Path:
        if self.gemini:
            return self.gemini.generate_video(prompt, keyframe, output_path)

        assert self.comfy is not None
        if Path(self.cfg.video_workflow).exists():
            return self.comfy.run(
                self.cfg.video_workflow,
                output_path,
                prompt=prompt,
                negative_prompt=self.store.load_storyboard().get("negative_prompt", ""),
                input_image=keyframe,
                width=self.cfg.width,
                height=self.cfg.height,
                seed=seed,
            )

        return image_to_motion_fallback(
            keyframe,
            output_path,
            duration=float(os.getenv("FALLBACK_SHOT_SECONDS", "5")),
            width=self.cfg.width,
            height=self.cfg.height,
        )

    def generate_character_candidates(
        self,
        count: int = 3,
        character_id: str | None = None,
    ) -> dict[str, list[Path]]:
        project = self.store.load_storyboard()
        results: dict[str, list[Path]] = {}
        characters = [
            c for c in project.get("characters", []) if not character_id or c["id"] == character_id
        ]
        if character_id and not characters:
            raise KeyError(f"Unknown character: {character_id}")

        for c_index, character in enumerate(characters, start=1):
            items: list[Path] = []
            base = character_prompt(character, project["style_prompt"])
            for candidate in range(1, count + 1):
                path = self.store.character_candidate(character["id"], candidate)
                path.parent.mkdir(parents=True, exist_ok=True)
                prompt = (
                    f"{base}. Candidate take {candidate}: preserve the exact identity bible; "
                    "vary only pose, facial micro-expression and composition."
                )
                self._image(
                    prompt,
                    path,
                    seed=self.cfg.base_seed + c_index * 100 + candidate,
                )
                items.append(path)
            results[character["id"]] = items
            if items and self.store.selected_character(character["id"]) is None:
                self.store.select_character(character["id"], items[0])
        return results

    def approve_character(self, character_id: str, candidate_number: int) -> Path:
        path = self.store.character_candidate(character_id, candidate_number)
        if not path.exists():
            raise FileNotFoundError(path)
        self.store.select_character(character_id, path)
        return path

    def generate_keyframe_candidates(
        self,
        count: int = 3,
        scene_id: str | None = None,
    ) -> dict[str, list[Path]]:
        project = self.store.load_storyboard()
        results: dict[str, list[Path]] = {}
        scenes = [s for s in project["scenes"] if not scene_id or s["id"] == scene_id]
        if scene_id and not scenes:
            raise KeyError(f"Unknown scene: {scene_id}")

        for s_index, scene in enumerate(scenes, start=1):
            refs: list[Path] = []
            for cid in scene.get("character_ids", []):
                selected = self.store.selected_character(cid)
                if selected and selected.exists():
                    refs.append(selected)
            if scene.get("character_ids") and not refs:
                raise RuntimeError(
                    f"Scene {scene['id']} has characters but no approved reference image."
                )

            base = scene_prompt(project, scene)
            items: list[Path] = []
            for candidate in range(1, count + 1):
                path = self.store.scene_candidate(scene["id"], candidate)
                path.parent.mkdir(parents=True, exist_ok=True)
                prompt = (
                    f"{base}. Vertical cinematic shot candidate {candidate}. Keep reference characters' "
                    "face, hair, clothing and palette unchanged; vary camera framing and staging only."
                )
                self._image(
                    prompt,
                    path,
                    references=refs[:3],
                    seed=self.cfg.base_seed + 1000 + s_index * 100 + candidate,
                )
                items.append(path)
            results[scene["id"]] = items
            if items and self.store.selected_scene(scene["id"]) is None:
                self.store.select_scene(scene["id"], items[0])
        return results

    def approve_keyframe(self, scene_id: str, candidate_number: int) -> Path:
        path = self.store.scene_candidate(scene_id, candidate_number)
        if not path.exists():
            raise FileNotFoundError(path)
        self.store.select_scene(scene_id, path)
        return path

    def generate_motion_candidates(
        self,
        count: int = 2,
        scene_id: str | None = None,
    ) -> dict[str, list[Path]]:
        project = self.store.load_storyboard()
        results: dict[str, list[Path]] = {}
        scenes = [s for s in project["scenes"] if not scene_id or s["id"] == scene_id]
        if scene_id and not scenes:
            raise KeyError(f"Unknown scene: {scene_id}")

        for s_index, scene in enumerate(scenes, start=1):
            keyframe = self.store.selected_scene(scene["id"])
            if not keyframe or not keyframe.exists():
                raise RuntimeError(f"Scene {scene['id']} has no approved keyframe")
            items: list[Path] = []
            for candidate in range(1, count + 1):
                path = self.store.motion_candidate(scene["id"], candidate)
                path.parent.mkdir(parents=True, exist_ok=True)
                base = scene.get("motion_prompt", "cinematic restrained motion")
                prompt = (
                    f"{base}. Motion take {candidate}. Preserve character identity, wardrobe, background "
                    "layout and shot continuity from the input frame. Avoid morphing and scene changes."
                )
                self._video(
                    prompt,
                    keyframe,
                    path,
                    self.cfg.base_seed + 2000 + s_index * 100 + candidate,
                )
                items.append(path)
            results[scene["id"]] = items
            if items and self.store.selected_motion(scene["id"]) is None:
                self.store.select_motion(scene["id"], items[0])
        return results

    def approve_motion(self, scene_id: str, candidate_number: int) -> Path:
        path = self.store.motion_candidate(scene_id, candidate_number)
        if not path.exists():
            raise FileNotFoundError(path)
        self.store.select_motion(scene_id, path)
        return path

    def render_episode(self) -> Path:
        project = self.store.load_storyboard()
        rendered_scenes: list[Path] = []
        subtitles: list[tuple[str, float]] = []
        characters = {c["id"]: c for c in project.get("characters", [])}

        for index, scene in enumerate(project["scenes"], start=1):
            scene_id = scene["id"]
            motion = self.store.selected_motion(scene_id)
            if not motion or not motion.exists():
                raise RuntimeError(f"Scene {scene_id} has no approved motion candidate")

            narration = scene.get("narration", "").strip()
            dialogue = scene.get("dialogue", "").strip()
            spoken_text = "\n".join(x for x in (narration, dialogue) if x)
            audio = self.store.audio_dir / f"{scene_id}.mp3"
            rendered = self.store.scenes_dir / f"{scene_id}.mp4"

            ids = scene.get("character_ids", [])
            voice = "narrator"
            if ids and ids[0] in characters:
                voice = characters[ids[0]].get("voice", "narrator")
            generate_tts(spoken_text, audio, voice)
            duration = media_duration(audio)
            render_scene(
                motion,
                audio,
                rendered,
                width=self.cfg.width,
                height=self.cfg.height,
            )
            rendered_scenes.append(rendered)
            subtitles.append((spoken_text, duration))
            print(f"rendered {index}/{len(project['scenes'])}: {scene_id}")

        final = self.store.final_dir / "final_story.mp4"
        concat_and_subtitle(rendered_scenes, subtitles, final)
        return final
