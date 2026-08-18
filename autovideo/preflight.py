import os
import shutil
import tempfile
from dataclasses import dataclass
from pathlib import Path

import requests


@dataclass
class Check:
    name: str
    ok: bool
    detail: str
    required: bool = True


def _command(name: str) -> Check:
    path = shutil.which(name)
    return Check(name, bool(path), path or f"{name} not found on PATH")


def _env(name: str, *, required: bool = True) -> Check:
    value = os.getenv(name, "").strip()
    return Check(name, bool(value) or not required, "configured" if value else "missing", required)


def _writable_outputs() -> Check:
    root = Path(os.getenv("AUTOVIDEO_OUTPUT_ROOT", "outputs"))
    try:
        root.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(dir=root, prefix=".autovideo-check-", delete=True):
            pass
        return Check("output directory", True, str(root.resolve()))
    except OSError as exc:
        return Check("output directory", False, f"not writable: {exc}")


def _comfy_health() -> Check:
    base = os.getenv("COMFYUI_URL", "http://127.0.0.1:8188").rstrip("/")
    try:
        response = requests.get(f"{base}/system_stats", timeout=3)
        response.raise_for_status()
        return Check("ComfyUI", True, f"reachable at {base}")
    except Exception as exc:
        return Check("ComfyUI", False, f"unreachable at {base}: {exc}")


def run_preflight() -> list[Check]:
    checks = [
        _command("ffmpeg"),
        _command("ffprobe"),
        _writable_outputs(),
    ]

    llm_provider = os.getenv("LLM_PROVIDER", "doubao").strip().lower()
    checks.append(
        Check(
            "LLM_PROVIDER",
            llm_provider in {"gemini", "doubao", "deepseek"},
            llm_provider or "missing",
        )
    )
    if llm_provider == "gemini":
        checks.extend([_env("GEMINI_API_KEY"), _env("GEMINI_LLM_MODEL")])
    elif llm_provider == "doubao":
        checks.extend([_env("ARK_API_KEY"), _env("DOUBAO_LLM_MODEL")])
    elif llm_provider == "deepseek":
        checks.extend([_env("DEEPSEEK_API_KEY"), _env("DEEPSEEK_MODEL")])

    provider = os.getenv("MEDIA_PROVIDER", "doubao").strip().lower()
    checks.append(
        Check("MEDIA_PROVIDER", provider in {"gemini", "doubao", "comfy"}, provider or "missing")
    )

    if provider == "gemini":
        checks.extend(
            [
                _env("GEMINI_API_KEY"),
                _env("GEMINI_IMAGE_MODEL"),
                _env("GEMINI_VIDEO_MODEL"),
                Check(
                    "Gemini video billing",
                    True,
                    "Veo API video generation requires Gemini paid-tier access",
                    required=False,
                ),
            ]
        )
    elif provider == "doubao":
        checks.extend(
            [
                _env("ARK_API_KEY"),
                _env("DOUBAO_IMAGE_MODEL"),
                _env("DOUBAO_VIDEO_MODEL"),
                Check(
                    "Doubao free quota",
                    True,
                    "trial quota depends on Ark account/model activation and remaining allowance",
                    required=False,
                ),
            ]
        )
    elif provider == "comfy":
        image_workflow = Path(os.getenv("COMFY_IMAGE_WORKFLOW", "workflows/image_api.json"))
        video_workflow = Path(os.getenv("COMFY_VIDEO_WORKFLOW", "workflows/video_api.json"))
        checks.extend(
            [
                _comfy_health(),
                Check("image workflow", image_workflow.exists(), str(image_workflow)),
                Check("video workflow", video_workflow.exists(), str(video_workflow), required=False),
            ]
        )

    tts_provider = os.getenv("TTS_PROVIDER", "edge").strip().lower()
    if tts_provider == "http":
        checks.append(_env("TTS_HTTP_URL"))
    else:
        checks.append(Check("TTS_PROVIDER", True, f"{tts_provider or 'edge'} fallback"))

    return checks


def format_report(checks: list[Check]) -> str:
    lines = ["AutoVideo production preflight", ""]
    for check in checks:
        marker = "PASS" if check.ok else ("WARN" if not check.required else "FAIL")
        lines.append(f"[{marker}] {check.name}: {check.detail}")
    required_failures = [c for c in checks if c.required and not c.ok]
    lines.extend(
        [
            "",
            "READY" if not required_failures else f"NOT READY: {len(required_failures)} required check(s) failed",
        ]
    )
    return "\n".join(lines)


def main() -> None:
    checks = run_preflight()
    print(format_report(checks))
    if any(c.required and not c.ok for c in checks):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
