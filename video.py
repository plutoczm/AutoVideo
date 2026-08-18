import asyncio
import io
import os
import re
import shutil
from pathlib import Path

import edge_tts
import google.generativeai as genai
import gradio as gr
import requests
from dotenv import load_dotenv
from PIL import Image
from moviepy.editor import (
    AudioFileClip,
    CompositeVideoClip,
    ImageClip,
    TextClip,
    concatenate_videoclips,
)

load_dotenv()

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY", "")
HF_TOKEN = os.getenv("HF_TOKEN", "")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")
EDGE_TTS_VOICE = os.getenv("EDGE_TTS_VOICE", "zh-CN-XiaoxiaoNeural")
SUBTITLE_FONT = os.getenv("SUBTITLE_FONT", "")

SD_API_URL = os.getenv(
    "SD_API_URL",
    "https://api-inference.huggingface.co/models/CompVis/stable-diffusion-v1-4",
)

WIDTH = 720
HEIGHT = 1280
FPS = 24
OUTPUT_DIR = Path("outputs")
IMAGE_DIR = OUTPUT_DIR / "images"
AUDIO_DIR = OUTPUT_DIR / "audio"
FINAL_VIDEO = OUTPUT_DIR / "final_video.mp4"


def check_config():
    missing = []
    if not GOOGLE_API_KEY:
        missing.append("GOOGLE_API_KEY")
    if not HF_TOKEN:
        missing.append("HF_TOKEN")
    if missing:
        raise RuntimeError(
            "Missing environment variables: " + ", ".join(missing) + ". Copy .env.example to .env first."
        )


def reset_outputs():
    if OUTPUT_DIR.exists():
        shutil.rmtree(OUTPUT_DIR)
    IMAGE_DIR.mkdir(parents=True, exist_ok=True)
    AUDIO_DIR.mkdir(parents=True, exist_ok=True)


def generate_scenes(topic: str):
    genai.configure(api_key=GOOGLE_API_KEY)
    model = genai.GenerativeModel(GEMINI_MODEL)

    prompt = f"""
你正在制作一个简单的短视频。根据下面的主题生成 5 个连续分镜。
每个分镜只需要 1-2 句简短中文旁白，并给出一个对应的英文文生图 Prompt。
不要输出标题、Markdown 或额外说明。
严格按下面格式逐行输出：
旁白文本 ||| English image prompt

主题：{topic}
""".strip()

    response = model.generate_content(prompt)
    text = response.text.strip()

    scenes = []
    for raw_line in text.splitlines():
        line = re.sub(r"^\s*\d+[\.、\)）:-]?\s*", "", raw_line).strip()
        if not line:
            continue

        if "|||" in line:
            narration, image_prompt = line.split("|||", 1)
        else:
            narration = line
            image_prompt = line

        narration = narration.strip()
        image_prompt = image_prompt.strip()
        if narration:
            scenes.append({"narration": narration, "image_prompt": image_prompt})

    if not scenes:
        raise RuntimeError("The LLM did not return usable scenes. Please try another topic.")

    return scenes[:5]


def generate_image(prompt: str, output_path: Path):
    headers = {"Authorization": f"Bearer {HF_TOKEN}"}
    response = requests.post(
        SD_API_URL,
        headers=headers,
        json={"inputs": prompt},
        timeout=180,
    )
    response.raise_for_status()

    try:
        image = Image.open(io.BytesIO(response.content)).convert("RGB")
    except Exception as exc:
        raise RuntimeError("Stable Diffusion did not return a valid image.") from exc

    image.save(output_path, quality=95)


async def _save_tts(text: str, output_path: Path):
    communicator = edge_tts.Communicate(text=text, voice=EDGE_TTS_VOICE)
    await communicator.save(str(output_path))


def generate_tts(text: str, output_path: Path):
    asyncio.run(_save_tts(text, output_path))


def fit_vertical(image_path: Path, duration: float):
    clip = ImageClip(str(image_path)).set_duration(duration)
    clip = clip.resize(height=HEIGHT)
    if clip.w < WIDTH:
        clip = clip.resize(width=WIDTH)
    return clip.crop(
        x_center=clip.w / 2,
        y_center=clip.h / 2,
        width=WIDTH,
        height=HEIGHT,
    )


def make_subtitle(text: str, duration: float):
    kwargs = {
        "txt": text,
        "fontsize": 36,
        "color": "white",
        "bg_color": "black",
        "method": "caption",
        "size": (WIDTH - 80, None),
        "align": "center",
    }
    if SUBTITLE_FONT:
        kwargs["font"] = SUBTITLE_FONT

    return (
        TextClip(**kwargs)
        .set_duration(duration)
        .set_position(("center", HEIGHT - 260))
    )


def generate_video(topic: str):
    topic = topic.strip()
    if not topic:
        raise gr.Error("请输入一个主题或几个内容要点。")

    check_config()
    reset_outputs()
    scenes = generate_scenes(topic)

    clips = []
    try:
        for index, scene in enumerate(scenes, start=1):
            image_path = IMAGE_DIR / f"scene_{index}.jpg"
            audio_path = AUDIO_DIR / f"scene_{index}.mp3"

            generate_image(scene["image_prompt"], image_path)
            generate_tts(scene["narration"], audio_path)

            audio_clip = AudioFileClip(str(audio_path))
            image_clip = fit_vertical(image_path, audio_clip.duration)
            subtitle_clip = make_subtitle(scene["narration"], audio_clip.duration)

            scene_clip = CompositeVideoClip(
                [image_clip, subtitle_clip],
                size=(WIDTH, HEIGHT),
            ).set_audio(audio_clip)
            clips.append(scene_clip)

        final_clip = concatenate_videoclips(clips, method="compose")
        final_clip.write_videofile(
            str(FINAL_VIDEO),
            fps=FPS,
            codec="libx264",
            audio_codec="aac",
        )
        final_clip.close()
    finally:
        for clip in clips:
            clip.close()

    scene_preview = "\n\n".join(
        f"分镜 {i}: {scene['narration']}\n图片 Prompt: {scene['image_prompt']}"
        for i, scene in enumerate(scenes, start=1)
    )
    return str(FINAL_VIDEO), scene_preview


demo = gr.Interface(
    fn=generate_video,
    inputs=gr.Textbox(
        label="主题 / 内容要点",
        lines=4,
        placeholder="例如：用 1 分钟介绍为什么天空是蓝色的",
    ),
    outputs=[
        gr.Video(label="生成视频"),
        gr.Textbox(label="分镜预览", lines=12),
    ],
    title="AutoVideo - AIGC 短视频生成工具",
    description="输入主题，自动生成分镜、Stable Diffusion 图片、Edge-TTS 配音和 9:16 短视频。",
)


if __name__ == "__main__":
    demo.launch()
