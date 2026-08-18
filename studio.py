import argparse
import json
import os
from pathlib import Path

from dotenv import load_dotenv

from autovideo.comfy import ComfyUIRunner
from autovideo.composer import (
    concat_and_subtitle,
    image_to_motion_fallback,
    media_duration,
    render_scene,
)
from autovideo.planner import character_prompt, plan_story, scene_prompt
from autovideo.tts import generate_tts


load_dotenv()


def read_source(value: str) -> str:
    candidate = Path(value)
    if candidate.exists() and candidate.is_file():
        return candidate.read_text(encoding="utf-8")
    return value


def voice_for_scene(project: dict, scene: dict) -> str:
    by_id = {c["id"]: c for c in project.get("characters", [])}
    ids = scene.get("character_ids", [])
    if ids and ids[0] in by_id:
        return by_id[ids[0]].get("voice", "narrator")
    return "narrator"


def build_project(source: str, output_dir: Path) -> Path:
    image_workflow = os.getenv("COMFY_IMAGE_WORKFLOW", "workflows/image_api.json")
    video_workflow = os.getenv("COMFY_VIDEO_WORKFLOW", "workflows/video_api.json")
    width = int(os.getenv("VIDEO_WIDTH", "1080"))
    height = int(os.getenv("VIDEO_HEIGHT", "1920"))
    seed = int(os.getenv("BASE_SEED", "42"))

    if not Path(image_workflow).exists():
        raise RuntimeError(
            f"Missing image workflow: {image_workflow}. Export an API-format ComfyUI workflow first; "
            "see workflows/README.md."
        )

    output_dir.mkdir(parents=True, exist_ok=True)
    refs_dir = output_dir / "references"
    keyframes_dir = output_dir / "keyframes"
    motion_dir = output_dir / "motion"
    audio_dir = output_dir / "audio"
    scenes_dir = output_dir / "scenes"
    for folder in (refs_dir, keyframes_dir, motion_dir, audio_dir, scenes_dir):
        folder.mkdir(parents=True, exist_ok=True)

    project = plan_story(source)
    (output_dir / "storyboard.json").write_text(
        json.dumps(project, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    comfy = ComfyUIRunner()
    reference_images: dict[str, Path] = {}

    print(f"[1/4] Generating {len(project.get('characters', []))} character references...")
    for index, character in enumerate(project.get("characters", []), start=1):
        ref_path = refs_dir / f"{character['id']}.png"
        comfy.run(
            image_workflow,
            ref_path,
            prompt=character_prompt(character, project["style_prompt"]),
            negative_prompt=project.get("negative_prompt", ""),
            width=width,
            height=height,
            seed=seed + index,
        )
        reference_images[character["id"]] = ref_path

    rendered_scenes: list[Path] = []
    subtitles: list[tuple[str, float]] = []
    has_video_workflow = Path(video_workflow).exists()

    print(f"[2/4] Rendering {len(project['scenes'])} story scenes...")
    for index, scene in enumerate(project["scenes"], start=1):
        scene_id = scene.get("id", f"scene_{index:02d}")
        keyframe = keyframes_dir / f"{scene_id}.png"
        motion = motion_dir / f"{scene_id}.mp4"
        audio = audio_dir / f"{scene_id}.mp3"
        rendered = scenes_dir / f"{scene_id}.mp4"

        ids = scene.get("character_ids", [])
        reference = reference_images.get(ids[0]) if ids else None

        comfy.run(
            image_workflow,
            keyframe,
            prompt=scene_prompt(project, scene),
            negative_prompt=project.get("negative_prompt", ""),
            reference_image=reference,
            width=width,
            height=height,
            seed=seed + 100 + index,
        )

        narration = scene.get("narration", "").strip()
        dialogue = scene.get("dialogue", "").strip()
        spoken_text = "\n".join(x for x in (narration, dialogue) if x)
        generate_tts(spoken_text, audio, voice_for_scene(project, scene))
        audio_duration = media_duration(audio)

        if has_video_workflow:
            comfy.run(
                video_workflow,
                motion,
                prompt=scene.get("motion_prompt", "cinematic subtle motion"),
                negative_prompt=project.get("negative_prompt", ""),
                input_image=keyframe,
                width=width,
                height=height,
                seed=seed + 200 + index,
            )
        else:
            image_to_motion_fallback(keyframe, motion, duration=audio_duration, width=width, height=height)

        render_scene(motion, audio, rendered, width=width, height=height)
        rendered_scenes.append(rendered)
        subtitles.append((spoken_text, audio_duration))
        print(f"  - {scene_id}: {audio_duration:.1f}s")

    print("[3/4] Composing final vertical video...")
    final_path = output_dir / "final_story.mp4"
    concat_and_subtitle(rendered_scenes, subtitles, final_path)

    print("[4/4] Done")
    print(f"Storyboard: {output_dir / 'storyboard.json'}")
    print(f"Final video: {final_path}")
    return final_path


def main() -> None:
    parser = argparse.ArgumentParser(
        description="AutoVideo Studio: idea/novel -> storyboard -> consistent keyframes -> I2V -> TTS -> short film"
    )
    parser.add_argument(
        "source",
        help="A topic, story idea, novel excerpt, or a UTF-8 .txt file path",
    )
    parser.add_argument("--output", default="outputs/studio", help="Output project directory")
    args = parser.parse_args()

    build_project(read_source(args.source), Path(args.output))


if __name__ == "__main__":
    main()
