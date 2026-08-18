# Upstream provenance

The initial AutoVideo baseline was imported from the following open-source project:

- Project: `vasanthgitt/GenAI-Video_Generation`
- Repository: https://github.com/vasanthgitt/GenAI-Video_Generation
- License: MIT
- Original copyright: Copyright (c) 2024 vasanth

The upstream project was selected because its workflow closely matches the intended learning project:

1. accept a text topic/prompt;
2. generate and summarize content;
3. generate an image for each scene using Stable Diffusion;
4. generate speech for each scene using TTS;
5. synchronize images, narration and subtitles;
6. concatenate all scenes into a final MP4 video.

The initial imported code is intentionally kept close to the upstream baseline. Future commits in this repository can gradually simplify, refactor and personalize the implementation.

## Other projects screened

`SaarD00/AI-Youtube-Shorts-Generator` was also reviewed. It provides topic/script generation, Edge-TTS and FFmpeg-based short-video composition, but its visual path primarily downloads stock footage from Pexels rather than generating scene images. For that reason it was not selected as the main baseline for AutoVideo.
