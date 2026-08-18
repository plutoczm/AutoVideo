# AutoVideo

A beginner-oriented AIGC short-video generation project.

The current baseline is imported from the MIT-licensed open-source project `vasanthgitt/GenAI-Video_Generation` and kept intentionally simple so it can be used as a learning project and modified step by step.

## Current workflow

```text
Topic / content point
        ↓
LLM content generation
        ↓
BART summarization / scene text split
        ↓
Stable Diffusion image generation
        ↓
gTTS voiceover generation
        ↓
MoviePy image + audio + subtitle composition
        ↓
final_video.mp4
```

## Features

- Generate content from a text topic.
- Summarize the generated content into shorter scene text.
- Generate one image for each scene with Stable Diffusion.
- Convert scene text into speech with TTS.
- Match each generated image to its audio duration.
- Add simple subtitles to each scene.
- Concatenate scenes into a final MP4 video.
- Provide a small Gradio interface for entering the topic and previewing the result.

## Technology stack

- Python
- Google Generative AI (`gemini-pro` in the imported baseline)
- Hugging Face Transformers / BART
- Stable Diffusion v1.4 through Hugging Face Inference API
- gTTS
- MoviePy / FFmpeg
- Gradio

The baseline deliberately uses an older, straightforward generation pipeline rather than a recent text-to-video model. The main learning goal is to understand the complete `content -> image -> TTS -> video` workflow.

## Installation

```bash
pip install -r requirements.txt
```

MoviePy also requires FFmpeg to be available on the system.

## Configuration

The imported baseline currently contains placeholder fields for:

- Google Generative AI API key
- Hugging Face inference token

Before running, replace the empty placeholders in `video.py` with your own credentials. A later refactor should move these values to environment variables instead of keeping them in source code.

## Run

```bash
python video.py
```

Open the Gradio page, enter a topic such as `Explain Photosynthesis`, and the program will generate scene images, narration, subtitles and a final video.

## Project status

This is the initial upstream baseline. Planned personal modifications can include:

- replacing hard-coded credentials with `.env` configuration;
- changing gTTS to Edge-TTS;
- simplifying the content-generation stage;
- improving scene splitting and subtitle timing;
- supporting vertical 9:16 short-video output;
- cleaning temporary output directories and adding basic error handling.

## Open-source provenance

This repository currently contains code derived from:

- `vasanthgitt/GenAI-Video_Generation`
- Original license: MIT
- Original copyright: Copyright (c) 2024 vasanth

See `UPSTREAM.md` and `LICENSE` for attribution and license details.
