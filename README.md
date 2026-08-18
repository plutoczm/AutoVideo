# AutoVideo

A beginner-oriented AIGC short-video generation tool for learning the complete `content -> image -> TTS -> video` workflow.

The project is intentionally kept small. It does not use a recent text-to-video model. Instead, it combines mature components that are easy to understand and explain: LLM scene generation, Stable Diffusion image generation, Edge-TTS narration and MoviePy/FFmpeg video composition.

## Workflow

```text
Topic / content points
        ↓
LLM generates 5 short scenes
        ↓
Narration + image prompt for each scene
        ↓
Stable Diffusion generates scene images
        ↓
Edge-TTS generates narration audio
        ↓
Image duration follows audio duration
        ↓
MoviePy / FFmpeg adds subtitles and joins scenes
        ↓
9:16 MP4 short video
```

## Current features

- Enter a topic or several content points in a small Gradio interface.
- Generate five short scenes with narration and image prompts.
- Generate one Stable Diffusion image for each scene.
- Generate Chinese or English voiceover with Edge-TTS.
- Match each image scene to the duration of its narration audio.
- Add simple subtitles.
- Compose a vertical `720 x 1280` short video with MoviePy/FFmpeg.
- Export the final result to `outputs/final_video.mp4`.

## Technology stack

- Python
- Google Generative AI (`gemini-1.5-flash` by default, configurable)
- Stable Diffusion v1.4 through Hugging Face Inference API
- Edge-TTS
- MoviePy / FFmpeg
- Gradio

The goal is not to build a production video platform. This is a compact learning project for understanding how text generation, image generation, TTS and traditional video processing can be connected end to end.

## Installation

```bash
python -m venv .venv

# Windows
.venv\Scripts\activate

# macOS / Linux
source .venv/bin/activate

pip install -r requirements.txt
```

FFmpeg must also be installed and available from the command line.

## Configuration

Copy the example environment file:

```bash
cp .env.example .env
```

On Windows PowerShell:

```powershell
Copy-Item .env.example .env
```

Then configure:

```text
GOOGLE_API_KEY=your_google_api_key
HF_TOKEN=your_huggingface_token
```

Optional settings:

```text
GEMINI_MODEL=gemini-1.5-flash
EDGE_TTS_VOICE=zh-CN-XiaoxiaoNeural
SUBTITLE_FONT=
```

`SUBTITLE_FONT` can be set when the default MoviePy/ImageMagick font cannot correctly render Chinese subtitles.

## Run

```bash
python video.py
```

Example input:

```text
为什么天空是蓝色的？用一分钟做一个简单科普。
```

The application generates five scenes and saves their images/audio under `outputs/`, with the final video at:

```text
outputs/final_video.mp4
```

## Project structure

```text
AutoVideo/
├── video.py            # complete beginner-friendly generation pipeline
├── requirements.txt
├── .env.example
├── .gitignore
├── LICENSE
├── UPSTREAM.md
└── README.md
```

The code deliberately stays in one main Python file so the complete flow is easy to follow before later refactoring.

## Changes from the initial upstream baseline

This repository started from the MIT-licensed `vasanthgitt/GenAI-Video_Generation` project. The current version keeps the original learning idea while making a few lightweight changes:

- changed `gTTS` to `Edge-TTS`;
- moved API credentials from source code to `.env`;
- simplified the original BART summarization stage into direct scene generation;
- generates narration and an image prompt for each scene;
- added configurable Chinese TTS voice;
- added vertical 9:16 short-video output;
- moved generated files into a single `outputs/` directory.

## Open-source provenance

This repository contains code derived from:

- Upstream: `vasanthgitt/GenAI-Video_Generation`
- Original license: MIT
- Original copyright: Copyright (c) 2024 vasanth

See `UPSTREAM.md` and `LICENSE` for attribution and license details.
