import json
from pathlib import Path
from typing import Any


class ProjectStore:
    """Filesystem-backed project state for iterative creator review.

    Each project keeps the storyboard, generated candidates, approvals and render state
    under one directory so a weak character/keyframe/shot can be regenerated without
    rerunning the entire episode.
    """

    def __init__(self, root: str | Path):
        self.root = Path(root)
        self.storyboard_path = self.root / "storyboard.json"
        self.selections_path = self.root / "selections.json"
        self.references_dir = self.root / "references"
        self.keyframes_dir = self.root / "keyframes"
        self.motion_dir = self.root / "motion"
        self.audio_dir = self.root / "audio"
        self.scenes_dir = self.root / "scenes"
        self.final_dir = self.root / "final"

    def ensure(self) -> None:
        self.root.mkdir(parents=True, exist_ok=True)
        for folder in (
            self.references_dir,
            self.keyframes_dir,
            self.motion_dir,
            self.audio_dir,
            self.scenes_dir,
            self.final_dir,
        ):
            folder.mkdir(parents=True, exist_ok=True)
        if not self.selections_path.exists():
            self.save_selections({"characters": {}, "scenes": {}, "motions": {}})

    def save_storyboard(self, project: dict[str, Any]) -> None:
        self.ensure()
        self.storyboard_path.write_text(
            json.dumps(project, ensure_ascii=False, indent=2), encoding="utf-8"
        )

    def load_storyboard(self) -> dict[str, Any]:
        if not self.storyboard_path.exists():
            raise FileNotFoundError(f"Missing storyboard: {self.storyboard_path}")
        return json.loads(self.storyboard_path.read_text(encoding="utf-8"))

    def load_selections(self) -> dict[str, Any]:
        self.ensure()
        payload = json.loads(self.selections_path.read_text(encoding="utf-8"))
        payload.setdefault("characters", {})
        payload.setdefault("scenes", {})
        payload.setdefault("motions", {})
        return payload

    def save_selections(self, payload: dict[str, Any]) -> None:
        self.root.mkdir(parents=True, exist_ok=True)
        payload.setdefault("characters", {})
        payload.setdefault("scenes", {})
        payload.setdefault("motions", {})
        self.selections_path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
        )

    def _select(self, group: str, item_id: str, candidate_path: str | Path) -> None:
        payload = self.load_selections()
        payload[group][item_id] = str(Path(candidate_path))
        self.save_selections(payload)

    def _selected(self, group: str, item_id: str) -> Path | None:
        value = self.load_selections().get(group, {}).get(item_id)
        return Path(value) if value else None

    def select_character(self, character_id: str, candidate_path: str | Path) -> None:
        self._select("characters", character_id, candidate_path)

    def select_scene(self, scene_id: str, candidate_path: str | Path) -> None:
        self._select("scenes", scene_id, candidate_path)

    def select_motion(self, scene_id: str, candidate_path: str | Path) -> None:
        self._select("motions", scene_id, candidate_path)

    def selected_character(self, character_id: str) -> Path | None:
        return self._selected("characters", character_id)

    def selected_scene(self, scene_id: str) -> Path | None:
        return self._selected("scenes", scene_id)

    def selected_motion(self, scene_id: str) -> Path | None:
        return self._selected("motions", scene_id)

    def character_candidate(self, character_id: str, index: int) -> Path:
        return self.references_dir / character_id / f"candidate_{index:02d}.png"

    def scene_candidate(self, scene_id: str, index: int) -> Path:
        return self.keyframes_dir / scene_id / f"candidate_{index:02d}.png"

    def motion_candidate(self, scene_id: str, index: int) -> Path:
        return self.motion_dir / scene_id / f"candidate_{index:02d}.mp4"

    def character_candidates(self, character_id: str) -> list[Path]:
        folder = self.references_dir / character_id
        return sorted(folder.glob("candidate_*.png")) if folder.exists() else []

    def scene_candidates(self, scene_id: str) -> list[Path]:
        folder = self.keyframes_dir / scene_id
        return sorted(folder.glob("candidate_*.png")) if folder.exists() else []

    def motion_candidates(self, scene_id: str) -> list[Path]:
        folder = self.motion_dir / scene_id
        return sorted(folder.glob("candidate_*.mp4")) if folder.exists() else []
