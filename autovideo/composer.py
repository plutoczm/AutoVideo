import json
import subprocess
from pathlib import Path


def _run(args: list[str]) -> None:
    subprocess.run(args, check=True)


def media_duration(path: str | Path) -> float:
    result = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "json",
            str(path),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    return float(json.loads(result.stdout)["format"]["duration"])


def render_scene(
    visual_path: str | Path,
    audio_path: str | Path,
    output_path: str | Path,
    *,
    width: int = 1080,
    height: int = 1920,
) -> Path:
    """Attach narration to a generated clip and normalize it for vertical delivery.

    If the I2V clip is shorter than narration, FFmpeg loops it. This keeps the orchestration
    deterministic while video-model shot length remains configurable in ComfyUI.
    """
    duration = media_duration(audio_path)
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    vf = (
        f"scale={width}:{height}:force_original_aspect_ratio=increase,"
        f"crop={width}:{height},fps=24,format=yuv420p"
    )
    _run(
        [
            "ffmpeg",
            "-y",
            "-stream_loop",
            "-1",
            "-i",
            str(visual_path),
            "-i",
            str(audio_path),
            "-t",
            f"{duration:.3f}",
            "-vf",
            vf,
            "-map",
            "0:v:0",
            "-map",
            "1:a:0",
            "-c:v",
            "libx264",
            "-preset",
            "medium",
            "-crf",
            "18",
            "-c:a",
            "aac",
            "-b:a",
            "192k",
            "-shortest",
            str(output_path),
        ]
    )
    return output_path


def image_to_motion_fallback(
    image_path: str | Path,
    output_path: str | Path,
    duration: float = 5.0,
    *,
    width: int = 1080,
    height: int = 1920,
) -> Path:
    """Fallback when no I2V workflow is configured: subtle Ken Burns motion."""
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    frames = max(1, int(duration * 24))
    vf = (
        f"scale={width * 2}:{height * 2}:force_original_aspect_ratio=increase,"
        f"crop={width * 2}:{height * 2},"
        f"zoompan=z='min(zoom+0.0008,1.08)':d={frames}:s={width}x{height}:fps=24,format=yuv420p"
    )
    _run(
        [
            "ffmpeg",
            "-y",
            "-loop",
            "1",
            "-i",
            str(image_path),
            "-t",
            str(duration),
            "-vf",
            vf,
            "-an",
            "-c:v",
            "libx264",
            "-crf",
            "18",
            str(output_path),
        ]
    )
    return output_path


def _srt_time(seconds: float) -> str:
    ms = int(round(seconds * 1000))
    hours, ms = divmod(ms, 3_600_000)
    minutes, ms = divmod(ms, 60_000)
    secs, ms = divmod(ms, 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{ms:03d}"


def write_srt(lines: list[tuple[str, float]], output_path: str | Path) -> Path:
    cursor = 0.0
    chunks: list[str] = []
    for index, (text, duration) in enumerate(lines, start=1):
        start = cursor
        end = cursor + duration
        chunks.append(f"{index}\n{_srt_time(start)} --> {_srt_time(end)}\n{text.strip()}\n")
        cursor = end
    output_path = Path(output_path)
    output_path.write_text("\n".join(chunks), encoding="utf-8")
    return output_path


def concat_and_subtitle(
    scene_paths: list[str | Path],
    subtitles: list[tuple[str, float]],
    output_path: str | Path,
) -> Path:
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    concat_file = output_path.parent / "concat.txt"
    srt_file = output_path.parent / "subtitles.srt"
    concat_file.write_text(
        "\n".join(f"file '{Path(p).resolve().as_posix()}'" for p in scene_paths),
        encoding="utf-8",
    )
    write_srt(subtitles, srt_file)

    temp = output_path.parent / "joined_no_subs.mp4"
    _run(
        [
            "ffmpeg",
            "-y",
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            str(concat_file),
            "-c",
            "copy",
            str(temp),
        ]
    )
    subtitle_path = srt_file.resolve().as_posix().replace(":", "\\:").replace("'", "\\'")
    _run(
        [
            "ffmpeg",
            "-y",
            "-i",
            str(temp),
            "-vf",
            f"subtitles='{subtitle_path}':force_style='FontSize=16,Outline=2,Alignment=2,MarginV=90'",
            "-c:v",
            "libx264",
            "-crf",
            "18",
            "-c:a",
            "copy",
            "-movflags",
            "+faststart",
            str(output_path),
        ]
    )
    return output_path
