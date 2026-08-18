import asyncio
import os
from pathlib import Path

import edge_tts
import requests


VOICE_MAP = {
    "narrator": "zh-CN-YunxiNeural",
    "young_female": "zh-CN-XiaoxiaoNeural",
    "young_male": "zh-CN-YunjianNeural",
    "mature_female": "zh-CN-XiaoyiNeural",
    "mature_male": "zh-CN-YunyangNeural",
}


async def _edge_save(text: str, voice: str, output_path: Path) -> None:
    communicator = edge_tts.Communicate(text=text, voice=voice)
    await communicator.save(str(output_path))


def edge_tts_generate(text: str, output_path: str | Path, voice_role: str = "narrator") -> Path:
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    voice = os.getenv("EDGE_TTS_VOICE", "") or VOICE_MAP.get(voice_role, VOICE_MAP["narrator"])
    asyncio.run(_edge_save(text, voice, output_path))
    return output_path


def http_tts_generate(text: str, output_path: str | Path, voice_role: str = "narrator") -> Path:
    """Call a user-supplied high-quality TTS service.

    The service is intentionally generic so a local CosyVoice/F5-TTS wrapper can be used
    without coupling this small project to one server implementation. It should accept
    JSON {text, voice} and return audio bytes.
    """
    url = os.getenv("TTS_HTTP_URL", "")
    if not url:
        raise RuntimeError("TTS_HTTP_URL is required for TTS_PROVIDER=http")
    response = requests.post(
        url,
        json={"text": text, "voice": voice_role},
        timeout=300,
    )
    response.raise_for_status()
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(response.content)
    return output_path


def generate_tts(text: str, output_path: str | Path, voice_role: str = "narrator") -> Path:
    provider = os.getenv("TTS_PROVIDER", "edge").lower()
    if provider == "http":
        return http_tts_generate(text, output_path, voice_role)
    return edge_tts_generate(text, output_path, voice_role)
