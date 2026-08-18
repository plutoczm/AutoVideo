# ComfyUI workflow slots

AutoVideo Studio keeps model-specific graph details in ComfyUI instead of hard-coding node IDs in Python.
Export each graph with **Save (API Format)** and place it here.

## 1. `image_api.json`

Recommended purpose: high-quality consistent story keyframes.

Good workflow families:

- SDXL / FLUX-style illustration workflow;
- StoryDiffusion / IP-Adapter / PuLID / InstantID-style reference-conditioned workflow;
- anime-oriented checkpoints/LoRA when you own or are licensed to use the model assets.

Replace relevant widget values in the exported API JSON with these literal tokens:

- `__PROMPT__` - positive prompt
- `__NEGATIVE_PROMPT__` - negative prompt
- `__REFERENCE_IMAGE__` - uploaded character reference filename
- `__WIDTH__` / `__HEIGHT__`
- `__SEED__`

`__REFERENCE_IMAGE__` is optional. If your graph uses a reference-image node, put the token in its image filename field.

## 2. `video_api.json`

Recommended purpose: image-to-video animation for each keyframe.

For a modern open workflow, use a Wan-family I2V graph (for example Wan2.x through native ComfyUI or a WanVideo wrapper). Export the graph in API format and replace inputs with:

- `__PROMPT__` - motion/camera prompt
- `__NEGATIVE_PROMPT__`
- `__INPUT_IMAGE__` - keyframe uploaded by AutoVideo
- `__WIDTH__` / `__HEIGHT__`
- `__SEED__`

If `video_api.json` is absent, AutoVideo falls back to a simple Ken Burns animation so the rest of the pipeline can still be tested.

## Why workflows are external

This project is an orchestration/AI-application project, not a reimplementation of diffusion/video models. Keeping workflows external makes it possible to upgrade the image/video model without rewriting the story, TTS and editing pipeline.

## Copyright / model-use note

Use original characters and source material you have permission to adapt. A prompt such as "high-energy hand-drawn pirate adventure anime" is safer for a public demo than reproducing named copyrighted characters, franchise logos, exact costumes or copied dialogue.
