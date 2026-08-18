import copy
import json
import os
import time
import uuid
from pathlib import Path
from typing import Any
from urllib.parse import urlencode

import requests


TOKENS = {
    "__PROMPT__": "prompt",
    "__NEGATIVE_PROMPT__": "negative_prompt",
    "__INPUT_IMAGE__": "input_image",
    "__REFERENCE_IMAGE__": "reference_image",
    "__WIDTH__": "width",
    "__HEIGHT__": "height",
    "__SEED__": "seed",
}


def _replace_tokens(value: Any, values: dict[str, Any]) -> Any:
    if isinstance(value, dict):
        return {k: _replace_tokens(v, values) for k, v in value.items()}
    if isinstance(value, list):
        return [_replace_tokens(v, values) for v in value]
    if isinstance(value, str):
        if value in TOKENS:
            return values.get(TOKENS[value], value)
        result = value
        for token, key in TOKENS.items():
            if token in result and key in values:
                result = result.replace(token, str(values[key]))
        return result
    return value


class ComfyUIRunner:
    """Small ComfyUI API client for exported API-format workflows.

    Workflows stay outside Python. Replace configurable inputs with tokens such as
    __PROMPT__, __INPUT_IMAGE__, __REFERENCE_IMAGE__, __WIDTH__, __HEIGHT__ and __SEED__.
    This allows AutoVideo to use SDXL/FLUX/StoryDiffusion-style image workflows or
    Wan-family image-to-video workflows without hard-coding model-specific node IDs.
    """

    def __init__(self, base_url: str | None = None):
        self.base_url = (base_url or os.getenv("COMFYUI_URL", "http://127.0.0.1:8188")).rstrip("/")
        self.client_id = str(uuid.uuid4())

    def load_workflow(self, path: str | Path) -> dict[str, Any]:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)

    def upload_image(self, path: str | Path) -> str:
        path = Path(path)
        with open(path, "rb") as f:
            response = requests.post(
                f"{self.base_url}/upload/image",
                files={"image": (path.name, f, "application/octet-stream")},
                data={"overwrite": "true", "type": "input"},
                timeout=120,
            )
        response.raise_for_status()
        payload = response.json()
        return payload.get("name", path.name)

    def queue(self, workflow: dict[str, Any]) -> str:
        response = requests.post(
            f"{self.base_url}/prompt",
            json={"prompt": workflow, "client_id": self.client_id},
            timeout=60,
        )
        response.raise_for_status()
        return response.json()["prompt_id"]

    def wait(self, prompt_id: str, timeout: int = 900) -> dict[str, Any]:
        deadline = time.time() + timeout
        while time.time() < deadline:
            response = requests.get(f"{self.base_url}/history/{prompt_id}", timeout=30)
            response.raise_for_status()
            history = response.json()
            if prompt_id in history:
                return history[prompt_id]
            time.sleep(2)
        raise TimeoutError(f"ComfyUI job timed out: {prompt_id}")

    def download_first_output(self, history: dict[str, Any], output_path: str | Path) -> Path:
        candidates: list[dict[str, str]] = []
        for node in history.get("outputs", {}).values():
            for key in ("images", "gifs", "videos"):
                for item in node.get(key, []) or []:
                    if isinstance(item, dict) and item.get("filename"):
                        candidates.append(item)
        if not candidates:
            raise RuntimeError("ComfyUI workflow returned no downloadable output")

        item = candidates[-1]
        params = {
            "filename": item["filename"],
            "subfolder": item.get("subfolder", ""),
            "type": item.get("type", "output"),
        }
        response = requests.get(f"{self.base_url}/view?{urlencode(params)}", timeout=180)
        response.raise_for_status()
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(response.content)
        return output_path

    def run(
        self,
        workflow_path: str | Path,
        output_path: str | Path,
        *,
        prompt: str,
        negative_prompt: str = "",
        input_image: str | Path | None = None,
        reference_image: str | Path | None = None,
        width: int = 720,
        height: int = 1280,
        seed: int = 42,
    ) -> Path:
        values: dict[str, Any] = {
            "prompt": prompt,
            "negative_prompt": negative_prompt,
            "width": width,
            "height": height,
            "seed": seed,
        }
        if input_image:
            values["input_image"] = self.upload_image(input_image)
        if reference_image:
            values["reference_image"] = self.upload_image(reference_image)

        raw = self.load_workflow(workflow_path)
        workflow = _replace_tokens(copy.deepcopy(raw), values)
        prompt_id = self.queue(workflow)
        history = self.wait(prompt_id)
        return self.download_first_output(history, output_path)
