import os
import time
from pathlib import Path

from google import genai
from google.genai import types
from PIL import Image


class GeminiMediaProvider:
    """High-quality cloud media provider for creator-facing output.

    Image generation uses a Gemini image model and can condition on one or more
    local character reference images. Video generation uses Veo image-to-video
    so the generated keyframe becomes the first frame of each shot.
    """

    def __init__(self) -> None:
        api_key = os.getenv("GEMINI_API_KEY", "").strip()
        if not api_key:
            raise RuntimeError("GEMINI_API_KEY is required for MEDIA_PROVIDER=gemini")
        self.client = genai.Client(api_key=api_key)
        self.image_model = os.getenv(
            "GEMINI_IMAGE_MODEL", "gemini-3.1-flash-image"
        )
        self.video_model = os.getenv(
            "GEMINI_VIDEO_MODEL", "veo-3.1-lite-generate-preview"
        )
        self.video_resolution = os.getenv("GEMINI_VIDEO_RESOLUTION", "720p")
        self.video_duration = int(os.getenv("GEMINI_VIDEO_DURATION", "8"))
        self.poll_seconds = int(os.getenv("GEMINI_POLL_SECONDS", "10"))

    def generate_image(
        self,
        prompt: str,
        output_path: str | Path,
        *,
        reference_images: list[str | Path] | None = None,
    ) -> Path:
        contents: list[object] = []
        for path in reference_images or []:
            contents.append(Image.open(path).convert("RGB"))
        contents.append(prompt)

        response = self.client.models.generate_content(
            model=self.image_model,
            contents=contents,
            config=types.GenerateContentConfig(response_modalities=["IMAGE"]),
        )

        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        for part in response.parts or []:
            if getattr(part, "inline_data", None) is not None:
                part.as_image().save(output_path)
                return output_path
        raise RuntimeError("Gemini image generation returned no image")

    def generate_video(
        self,
        prompt: str,
        input_image: str | Path,
        output_path: str | Path,
    ) -> Path:
        image = types.Image.from_file(location=str(input_image))
        operation = self.client.models.generate_videos(
            model=self.video_model,
            prompt=prompt,
            image=image,
            config=types.GenerateVideosConfig(
                number_of_videos=1,
                duration_seconds=self.video_duration,
                aspect_ratio="9:16",
                resolution=self.video_resolution,
                enhance_prompt=True,
            ),
        )

        while not operation.done:
            time.sleep(self.poll_seconds)
            operation = self.client.operations.get(operation)

        if not operation.response or not operation.response.generated_videos:
            raise RuntimeError("Veo generation completed without a video")

        generated = operation.response.generated_videos[0]
        self.client.files.download(file=generated.video)
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        generated.video.save(str(output_path))
        return output_path
