# AutoVideo AI Studio

Creator-oriented AIGC story-to-video pipeline for producing vertical short films, AI comics/animation and novel adaptations for Douyin, TikTok and YouTube Shorts.

`main` is the continuously upgraded creator version. The original beginner demo is preserved on the `legacy/demo` branch.

## Product workflow

AutoVideo is not an AI slideshow maker. It uses a human-in-the-loop creator workflow so weak generations can be rejected before expensive video rendering.

```text
Story / novel excerpt / content idea
        ↓
Gemini / Doubao / DeepSeek storyboard planning
        ↓
Character bible + stable voice roles
        ↓
3x character candidates → human approval
        ↓
3x reference-conditioned keyframes → human approval
        ↓
2x image-to-video shots → human approval
        ↓
Narration + per-character dialogue TTS
        ↓
Native ambience + optional BGM
        ↓
Line-level subtitles + FFmpeg composition
        ↓
9:16 short film
```

For public demos, use original characters/stories or material you have permission to adapt.

## Provider architecture

LLM and media providers are configured independently. This lets you use one provider end to end or mix providers for cost/quality comparisons.

### LLM providers

`LLM_PROVIDER` supports:

- `doubao` — Volcengine Ark Responses API, default model `doubao-seed-2-1-turbo-260628`;
- `gemini` — Gemini API, default model `gemini-3.6-flash`;
- `deepseek` — DeepSeek API, current default model `deepseek-v4-flash`.

Legacy DeepSeek model names `deepseek-chat` / `deepseek-reasoner` are no longer used by this project.

### Media providers

`MEDIA_PROVIDER` supports:

- `doubao` — Seedream image generation + Seedance image-to-video;
- `gemini` — Gemini image generation + Veo image-to-video;
- `comfy` — local/exported ComfyUI workflows for open-model experiments.

Current defaults:

```text
Doubao image: doubao-seedream-5-0-lite-260128
Doubao video: doubao-seedance-1-5-pro-251215
Gemini image: gemini-3.1-flash-image
Gemini video: veo-3.1-lite-generate-preview
```

Model IDs live in `.env`, so providers can be upgraded without rewriting the orchestration layer.

## Free-first configuration

The repository defaults to the simplest current trial path: **one Volcengine Ark key for LLM + image + video**, plus Edge-TTS for speech.

```text
LLM_PROVIDER=doubao
MEDIA_PROVIDER=doubao

ARK_API_KEY=your_volcengine_ark_key
DOUBAO_LLM_MODEL=doubao-seed-2-1-turbo-260628
DOUBAO_IMAGE_MODEL=doubao-seedream-5-0-lite-260128
DOUBAO_VIDEO_MODEL=doubao-seedance-1-5-pro-251215

TTS_PROVIDER=edge
```

This is the recommended first-run setup because Volcengine currently advertises trial quotas for Doubao Seed 2.1, Seedream and Seedance. The same `ARK_API_KEY` is used by all three adapters. Free quotas/model activation are account-specific and can change, so check the Ark console before batch generation.

### Free Gemini LLM + Doubao media

Gemini is also supported as the storyboard LLM. Gemini 3.6 Flash currently has a Gemini API free tier for text input/output:

```text
LLM_PROVIDER=gemini
GEMINI_API_KEY=your_google_ai_studio_key
GEMINI_LLM_MODEL=gemini-3.6-flash

MEDIA_PROVIDER=doubao
ARK_API_KEY=your_volcengine_ark_key
```

This uses Gemini only for story planning while still using the Doubao trial path for image/video generation.

### Optional DeepSeek fallback

```text
LLM_PROVIDER=deepseek
DEEPSEEK_API_KEY=your_deepseek_key
DEEPSEEK_BASE_URL=https://api.deepseek.com
DEEPSEEK_MODEL=deepseek-v4-flash
```

DeepSeek is kept as a low-cost optional provider, not the free-first default.

### Optional Gemini media path

```text
LLM_PROVIDER=gemini
GEMINI_API_KEY=your_google_ai_studio_key
GEMINI_LLM_MODEL=gemini-3.6-flash

MEDIA_PROVIDER=gemini
GEMINI_IMAGE_MODEL=gemini-3.1-flash-image
GEMINI_VIDEO_MODEL=veo-3.1-lite-generate-preview
GEMINI_VIDEO_RESOLUTION=720p
GEMINI_VIDEO_DURATION=8
```

The Gemini image/video path remains supported for quality comparison, but Veo API video generation currently requires a paid Gemini API tier; it is therefore not the default free-first media path.

### Local no-API media path

If you already have a suitable GPU and model weights:

```text
MEDIA_PROVIDER=comfy
COMFYUI_URL=http://127.0.0.1:8188
COMFY_IMAGE_WORKFLOW=workflows/image_api.json
COMFY_VIDEO_WORKFLOW=workflows/video_api.json
```

API cost is zero, but local GPU time/VRAM and model downloads are your responsibility.

## Creator project state

Each episode is persisted so one weak scene can be regenerated without restarting the whole project.

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
├── scenes/
└── final/
    └── final_story.mp4
```

`selections.json` records approved character references, keyframes and motion candidates.

When `MEDIA_PROVIDER=doubao`, Seedream-generated keyframes also keep a small `.source_url` sidecar used as the first-frame URL for Seedance I2V. If that provider-hosted URL expires before motion generation, regenerate the selected keyframe and then request the I2V candidate again.

## Character consistency

Character consistency is treated as a pipeline constraint rather than a prompt-only feature:

1. the LLM creates one stable `visual_bible` per character;
2. multiple character candidates are generated;
3. the creator locks one identity reference;
4. scene keyframes reuse approved character references;
5. prompts preserve face, hair, wardrobe and palette while varying staging;
6. I2V starts from an approved keyframe and asks for restrained motion rather than a new scene.

The exact identity-control mechanism depends on the provider. Gemini and Seedream accept reference images; ComfyUI can host IP-Adapter / PuLID / InstantID / StoryDiffusion-style workflows.

## Creator Review UI

For publishable work, use the staged Gradio UI:

```bash
python review_app.py
```

Stages:

1. **Storyboard** — create/load/edit structured story JSON;
2. **Character Bible** — generate and approve character reference candidates;
3. **Storyboard Keyframes** — generate and approve scene compositions;
4. **I2V Shot Review** — generate and preview motion candidates;
5. **Final Render** — per-character TTS, ambience/BGM, subtitles and 9:16 MP4.

The automatic CLI remains available for quick smoke tests:

```bash
python studio.py "一个原创海上冒险故事：年轻航海士在暴风雨中发现一座发光的失落岛屿"
```

## First episode

The repository includes the original 45–60 second test episode **《潮汐之眼》**:

```text
examples/episode_01_story.txt
examples/episode_01_storyboard.json
```

See `docs/FIRST_EPISODE.md` for the production runbook and acceptance criteria.

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

Install `ffmpeg` and `ffprobe` separately and ensure both are on `PATH`.

Then:

```bash
cp .env.example .env
# Add ARK_API_KEY for the default free-first path.
python -m autovideo.preflight
python review_app.py
```

Do not commit `.env` or API keys to GitHub.

## Project structure

```text
AutoVideo/
├── autovideo/
│   ├── llm.py              # Doubao / Gemini / DeepSeek storyboard providers
│   ├── planner.py          # story -> characters + storyboard + dialogue
│   ├── project_store.py    # project assets + approvals
│   ├── creator.py          # staged candidate/review/render pipeline
│   ├── gemini_media.py     # Gemini image + Veo I2V
│   ├── doubao_media.py     # Seedream image + Seedance I2V
│   ├── comfy.py            # model-agnostic local workflow adapter
│   ├── tts.py              # Edge-TTS / HTTP high-quality TTS adapter
│   ├── composer.py         # FFmpeg audio, subtitles, BGM and final composition
│   └── preflight.py        # local/provider readiness checks
├── examples/
├── docs/
├── workflows/
├── review_app.py
├── studio.py
├── requirements.txt
├── .env.example
└── README.md
```

## Next creator-quality milestones

The next changes should be driven by real episode output rather than adding unrelated infrastructure:

- direct high-quality multi-speaker CosyVoice integration;
- SFX generation/library and loudness/ducking controls;
- better continuity memory for props, damage, weather and time-of-day;
- automatic visual QA before expensive I2V;
- provider comparison for the same approved keyframe;
- reusable cast/style assets across episodes.

## Legacy demo

The original learning version based on `Stable Diffusion -> Edge-TTS -> image/video composition` is preserved on:

```text
legacy/demo
```

## Open-source provenance

The repository originally started from the MIT-licensed `vasanthgitt/GenAI-Video_Generation` learning project. The current creator architecture is substantially different, while the original attribution remains in `UPSTREAM.md` and `LICENSE`.
