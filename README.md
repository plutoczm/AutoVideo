# AutoVideo AI Studio

Creator-oriented AIGC story-to-video pipeline for producing vertical short films, AI comics/animation and novel adaptations for platforms such as Douyin, TikTok and YouTube Shorts.

`main` is the continuously upgraded creator version. The original beginner demo is preserved on the `legacy/demo` branch.

## Product goal

The goal is not to make a slideshow from AI images. AutoVideo is designed around the production stages that matter for watchable short-form story content:

```text
Story / novel excerpt / content idea
        ↓
LLM story adaptation
        ↓
Character bible + voice roles
        ↓
Storyboard / shot plan
        ↓
Character reference images
        ↓
Reference-conditioned scene keyframes
        ↓
Image-to-video animation
        ↓
Controlled narration / dialogue
        ↓
Native ambience + voice mixing
        ↓
Subtitles + FFmpeg composition
        ↓
9:16 short film
```

The public demo should use original characters and stories or material that you have permission to adapt.

## Current main pipeline

### 1. Story planning

`autovideo/planner.py` converts an idea or novel excerpt into structured JSON with:

- original character definitions;
- stable appearance/wardrobe descriptions;
- voice roles;
- 6-10 short-form scenes;
- keyframe prompts;
- image-to-video motion/camera prompts;
- narration and dialogue.

### 2. Character and scene images

Two media paths are supported:

- `MEDIA_PROVIDER=gemini` - creator-quality cloud path using a current Gemini image model;
- `MEDIA_PROVIDER=comfy` - local/experimental path through exported ComfyUI workflows.

The Gemini path reuses generated character references when rendering scene keyframes so identity is not based on text alone.

### 3. Image-to-video

The default cloud path animates each keyframe with Veo image-to-video. During fast iteration, use the fast model; for final candidate shots, switch the model through `.env` without changing pipeline code.

The local path stays model-agnostic through ComfyUI. A Wan/LTX/Hunyuan-style I2V graph can be swapped in by exporting an API-format workflow.

### 4. Voice and sound

- Edge-TTS remains the no-cost fallback.
- `TTS_PROVIDER=http` can point to a higher-quality local or remote TTS service such as a CosyVoice/F5-TTS wrapper.
- When a generated video already contains ambience/effects, FFmpeg keeps that native audio at a lower level and mixes controlled narration/dialogue over it.

### 5. Delivery

Final scenes are normalized to vertical output, concatenated, subtitled and exported as H.264/AAC MP4 suitable for short-form publishing workflows.

## Quality strategy

A creator-facing result depends more on continuity and shot design than on using a single large model. AutoVideo therefore treats the following as first-class quality constraints:

1. **Story hook** - the first seconds must establish conflict/question immediately.
2. **Character consistency** - one visual bible and reusable reference assets across shots.
3. **Shot continuity** - each I2V clip begins from an approved keyframe instead of independently generating unrelated scenes.
4. **Camera language** - shot size, angle, motion and lighting are planned before rendering.
5. **Voice identity** - stable voice roles across the story.
6. **Audio hierarchy** - narration/dialogue above ambience, with room for later BGM/SFX layers.
7. **Vertical composition** - scenes are planned for `9:16`, not cropped from landscape as an afterthought.
8. **Human review** - expensive final renders should be selected from storyboard/keyframe candidates rather than blindly accepting first generations.

## Recommended creator workflow

For actual publishing, do not immediately render every scene at the most expensive quality setting.

```text
Draft story
  ↓
Generate storyboard JSON
  ↓
Generate / approve character sheets
  ↓
Generate / approve scene keyframes
  ↓
Fast I2V draft renders
  ↓
Replace weak shots
  ↓
Final-quality I2V renders
  ↓
Voice / ambience / subtitle pass
  ↓
Final MP4
```

This keeps iteration cost under control while preserving quality where viewers actually notice it.

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

Install `ffmpeg` and `ffprobe` separately and make sure both are available on `PATH`.

## Configuration

```bash
cp .env.example .env
```

At minimum for the default cloud creator path configure:

```text
LLM_API_KEY=...
GEMINI_API_KEY=...
MEDIA_PROVIDER=gemini
```

Useful quality controls:

```text
GEMINI_IMAGE_MODEL=gemini-3.1-flash-image-preview
GEMINI_VIDEO_MODEL=veo-3.1-fast-generate-preview
GEMINI_VIDEO_RESOLUTION=720p
GEMINI_VIDEO_DURATION=8
VIDEO_WIDTH=1080
VIDEO_HEIGHT=1920
```

Use the fast video model for iteration. For selected final shots, switch `GEMINI_VIDEO_MODEL` to a higher-quality compatible Veo model available to your account.

## Run

Input can be an idea, a short story, a novel excerpt, or a UTF-8 text file.

```bash
python studio.py "一个原创海上冒险故事：年轻航海士在暴风雨中发现一座会发光的失落岛屿"
```

Or:

```bash
python studio.py examples/story.txt --output outputs/my_episode
```

Generated project assets are organized under the output directory:

```text
outputs/my_episode/
├── storyboard.json
├── references/
├── keyframes/
├── motion/
├── audio/
├── scenes/
├── subtitles.srt
└── final_story.mp4
```

## Project structure

```text
AutoVideo/
├── autovideo/
│   ├── planner.py          # story -> characters + storyboard
│   ├── gemini_media.py     # Gemini image + Veo I2V creator path
│   ├── comfy.py            # model-agnostic ComfyUI adapter
│   ├── tts.py              # Edge-TTS / high-quality HTTP TTS adapter
│   └── composer.py         # FFmpeg render, audio mix and subtitles
├── workflows/              # optional local ComfyUI workflow slots
├── studio.py               # end-to-end CLI
├── requirements.txt
├── .env.example
├── UPSTREAM.md
└── README.md
```

## Model / provider roadmap

The orchestration layer is intentionally provider-oriented. Planned creator providers include:

- image generation/editing with stronger multi-reference character control;
- additional cloud I2V/T2V providers for shot comparison;
- current open video models through ComfyUI for local rendering;
- direct high-quality multi-speaker TTS integration;
- BGM/SFX generation and automatic loudness/ducking;
- storyboard/keyframe review UI before expensive renders;
- episode/project persistence and rerender-from-scene support.

## Legacy demo

The earlier learning version based on a simple `Stable Diffusion -> Edge-TTS -> image/video composition` flow is kept at:

```text
legacy/demo
```

It remains useful for understanding the basic pipeline, while `main` is reserved for the continuously upgraded creator-facing system.

## Open-source provenance

The repository originally started from the MIT-licensed `vasanthgitt/GenAI-Video_Generation` learning project. The current main branch has moved to a substantially different orchestration architecture, but the original attribution is intentionally retained in `UPSTREAM.md` and `LICENSE`.
