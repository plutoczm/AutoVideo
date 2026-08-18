# First publishable episode runbook

This runbook is for producing the first real AutoVideo short, **《潮汐之眼》**, instead of only validating the code path.

## 1. Configure the environment

Copy `.env.example` to `.env`, then configure the LLM/media credentials you intend to use.

For the default cloud path, the required values are:

```text
LLM_API_KEY=...
MEDIA_PROVIDER=gemini
GEMINI_API_KEY=...
GEMINI_IMAGE_MODEL=...
GEMINI_VIDEO_MODEL=...
```

Keep `TTS_PROVIDER=edge` for the first visual production pass. Upgrade voice quality only after the visuals and pacing are acceptable.

## 2. Run production preflight

```bash
python -m autovideo.preflight
```

Do not start paid image/video generation until all required checks are `PASS`.

The preflight verifies:

- `ffmpeg` and `ffprobe` are on `PATH`;
- the output directory is writable;
- LLM configuration exists;
- the selected media provider has the required configuration;
- local ComfyUI connectivity/workflow files when `MEDIA_PROVIDER=comfy`;
- high-quality HTTP TTS configuration when enabled.

## 3. Start the creator review UI

```bash
python review_app.py
```

Click **运行环境检查** once more from the UI, then click **载入《潮汐之眼》精修模板**.

The template comes from:

```text
examples/episode_01_storyboard.json
```

It is hand-authored so the first production run does not depend on LLM storyboard variability.

## 4. Character lock pass

Generate three candidates for `char_lulan` and `char_eve` separately.

Reject a candidate if any of the following are weak:

- face is difficult to reproduce;
- hairstyle silhouette is ambiguous;
- costume colors are not visually distinct;
- brass compass / crescent pendant is missing;
- front/three-quarter views look like different people.

Approve exactly one reference for each character before rendering scene keyframes.

## 5. Keyframe pass

Generate three candidates per scene, one scene at a time.

Prioritize these shots first because they define the visual standard for the episode:

1. `scene_01` — hook / compass / golden light;
2. `scene_03` — lost-city reveal;
3. `scene_06` — suspended-rain realization beat;
4. `scene_08` — mechanical-eye ending.

If these four shots do not look publishable, do not spend video-generation budget on the remaining scenes yet.

Check every keyframe for:

- character identity;
- costume and prop continuity;
- clear 9:16 composition;
- readable focal point on a phone screen;
- shot-size variety across adjacent scenes;
- no text/watermark/deformed limbs.

## 6. I2V pass

Start with one motion candidate for the four priority scenes. Generate a second candidate only where the first has a real motion/identity defect.

Good motion should be restrained. Reject clips with:

- face morphing;
- wardrobe changes;
- duplicated limbs;
- architecture rebuilding itself;
- aggressive camera movement that hides the subject;
- a different scene appearing midway through the shot.

After the four priority scenes pass, render the remaining shots.

## 7. Dialogue and pacing pass

The template uses separate `dialogue_lines`, so Lu Lan and Eve can keep different voices.

Before final render, edit `storyboard.json` in the UI if a line is too long. Short-form pacing should prefer concise spoken lines over literal exposition.

## 8. Final render

Optional: provide an owned/licensed BGM file in the final-render tab. Keep BGM volume low for the first pass.

Render output:

```text
outputs/projects/tide-eye-episode-01/final/final_story.mp4
```

Watch the result on a phone, not only on desktop. The first acceptance criteria are:

- the first 2-3 seconds create immediate curiosity;
- Lu Lan and Eve remain recognizable across scenes;
- no single bad I2V shot breaks immersion;
- dialogue is intelligible above ambience/BGM;
- subtitles are readable without covering faces;
- the final eye reveal gives a clear ending beat.

## 9. Iterate at scene granularity

Do not restart the entire episode because of one weak shot. AutoVideo stores selected references, keyframes and motion candidates in `selections.json`; regenerate only the weak character/scene/shot and render the episode again.

The goal of the first episode is not perfect automation. The goal is a short that is good enough to publish and that gives concrete evidence about which part of the pipeline needs the next engineering improvement.
