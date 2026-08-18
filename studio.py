import argparse
from pathlib import Path

from dotenv import load_dotenv

from autovideo.creator import CreatorPipeline


load_dotenv()


def read_source(value: str) -> str:
    candidate = Path(value)
    if candidate.exists() and candidate.is_file():
        return candidate.read_text(encoding="utf-8")
    return value


def build_project(source: str, output_dir: Path) -> Path:
    pipeline = CreatorPipeline(output_dir)

    print("[1/5] Planning storyboard...")
    project = pipeline.create_storyboard(source)

    print(f"[2/5] Generating {len(project.get('characters', []))} character references...")
    pipeline.generate_character_candidates(count=1)

    print(f"[3/5] Generating {len(project.get('scenes', []))} scene keyframes...")
    pipeline.generate_keyframe_candidates(count=1)

    print("[4/5] Generating image-to-video shots...")
    pipeline.generate_motion_candidates(count=1)

    print("[5/5] Rendering final vertical video...")
    final_path = pipeline.render_episode()
    print(f"Storyboard: {output_dir / 'storyboard.json'}")
    print(f"Final video: {final_path}")
    return final_path


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "AutoVideo Studio quick path: idea/novel -> storyboard -> references -> keyframes "
            "-> I2V -> multi-speaker TTS -> vertical short film"
        )
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
