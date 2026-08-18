import json
import re
from pathlib import Path

import gradio as gr
from dotenv import load_dotenv

from autovideo.creator import CreatorPipeline
from autovideo.preflight import format_report, run_preflight
from autovideo.project_store import ProjectStore


load_dotenv()
DEFAULT_PROJECTS_DIR = Path("outputs/projects")
FIRST_EPISODE_STORYBOARD = Path("examples/episode_01_storyboard.json")


def _safe_name(value: str) -> str:
    name = re.sub(r"[^a-zA-Z0-9_-]+", "-", value.strip()).strip("-")
    return name or "episode"


def _pipeline(project_dir: str) -> CreatorPipeline:
    if not project_dir.strip():
        raise gr.Error("请先创建或加载项目。")
    return CreatorPipeline(project_dir.strip())


def _project_updates(project: dict):
    characters = [c["id"] for c in project.get("characters", [])]
    scenes = [s["id"] for s in project.get("scenes", [])]
    return (
        gr.Dropdown(choices=characters, value=characters[0] if characters else None),
        gr.Dropdown(choices=scenes, value=scenes[0] if scenes else None),
        gr.Dropdown(choices=scenes, value=scenes[0] if scenes else None),
    )


def run_environment_check():
    report = format_report(run_preflight())
    return f"```text\n{report}\n```"


def create_project(source: str, project_name: str):
    if not source.strip():
        raise gr.Error("请输入故事、小说片段或内容大纲。")
    project_dir = DEFAULT_PROJECTS_DIR / _safe_name(project_name)
    pipeline = CreatorPipeline(project_dir)
    project = pipeline.create_storyboard(source)
    char_update, scene_update, motion_update = _project_updates(project)
    return (
        str(project_dir),
        json.dumps(project, ensure_ascii=False, indent=2),
        char_update,
        scene_update,
        motion_update,
        "已生成 Storyboard。先审核剧情、角色、台词和镜头 Prompt，再保存并生成素材。",
    )


def bootstrap_first_episode(project_name: str):
    if not FIRST_EPISODE_STORYBOARD.exists():
        raise gr.Error(f"找不到模板：{FIRST_EPISODE_STORYBOARD}")
    project = json.loads(FIRST_EPISODE_STORYBOARD.read_text(encoding="utf-8"))
    name = _safe_name(project_name or "tide-eye-episode-01")
    project_dir = DEFAULT_PROJECTS_DIR / name
    ProjectStore(project_dir).save_storyboard(project)
    char_update, scene_update, motion_update = _project_updates(project)
    return (
        str(project_dir),
        json.dumps(project, ensure_ascii=False, indent=2),
        char_update,
        scene_update,
        motion_update,
        "已载入《潮汐之眼》人工精修 Storyboard。可直接审核并保存，不必先调用 LLM。",
    )


def load_project(project_dir: str):
    store = ProjectStore(project_dir.strip())
    project = store.load_storyboard()
    char_update, scene_update, motion_update = _project_updates(project)
    return (
        json.dumps(project, ensure_ascii=False, indent=2),
        char_update,
        scene_update,
        motion_update,
        "项目已加载。",
    )


def save_storyboard(project_dir: str, storyboard_text: str):
    if not project_dir.strip():
        raise gr.Error("请先创建或加载项目。")
    try:
        payload = json.loads(storyboard_text)
    except json.JSONDecodeError as exc:
        raise gr.Error(f"Storyboard JSON 格式错误：{exc}") from exc
    if not payload.get("scenes"):
        raise gr.Error("Storyboard 必须包含 scenes。")
    ProjectStore(project_dir.strip()).save_storyboard(payload)
    char_update, scene_update, motion_update = _project_updates(payload)
    return char_update, scene_update, motion_update, "Storyboard 修改已保存。"


def generate_characters(project_dir: str, character_id: str, count: int):
    pipeline = _pipeline(project_dir)
    results = pipeline.generate_character_candidates(int(count), character_id or None)
    items = results.get(character_id, []) if character_id else [p for group in results.values() for p in group]
    return [str(p) for p in items], f"已生成 {len(items)} 张角色候选图。选择编号后点击确认角色。"


def approve_character(project_dir: str, character_id: str, candidate_number: int):
    if not character_id:
        raise gr.Error("请选择角色。")
    path = _pipeline(project_dir).approve_character(character_id, int(candidate_number))
    return str(path), f"已锁定 {character_id} 的角色参考图：{path.name}"


def generate_keyframes(project_dir: str, scene_id: str, count: int):
    if not scene_id:
        raise gr.Error("请选择分镜。")
    results = _pipeline(project_dir).generate_keyframe_candidates(int(count), scene_id)
    items = results.get(scene_id, [])
    return [str(p) for p in items], f"已生成 {len(items)} 张关键帧候选。"


def approve_keyframe(project_dir: str, scene_id: str, candidate_number: int):
    if not scene_id:
        raise gr.Error("请选择分镜。")
    path = _pipeline(project_dir).approve_keyframe(scene_id, int(candidate_number))
    return str(path), f"已锁定 {scene_id} 关键帧：{path.name}"


def _motion_choices(items: list[Path]):
    return [(p.stem, str(p)) for p in items]


def generate_motions(project_dir: str, scene_id: str, count: int):
    if not scene_id:
        raise gr.Error("请选择分镜。")
    results = _pipeline(project_dir).generate_motion_candidates(int(count), scene_id)
    items = results.get(scene_id, [])
    choices = _motion_choices(items)
    first = str(items[0]) if items else None
    return (
        gr.Dropdown(choices=choices, value=first),
        first,
        f"已生成 {len(items)} 个 I2V 镜头候选。逐个预览后确认。",
    )


def preview_motion(path: str):
    return path or None


def approve_motion(project_dir: str, scene_id: str, selected_path: str):
    if not scene_id or not selected_path:
        raise gr.Error("请选择一个镜头候选。")
    match = re.search(r"candidate_(\d+)\.mp4$", selected_path)
    if not match:
        raise gr.Error("无法识别候选编号。")
    path = _pipeline(project_dir).approve_motion(scene_id, int(match.group(1)))
    return str(path), f"已锁定 {scene_id} 动态镜头：{path.name}"


def render_final(project_dir: str, bgm_path: str, bgm_volume: float):
    bgm = bgm_path.strip() if bgm_path else None
    if bgm and not Path(bgm).exists():
        raise gr.Error(f"BGM 文件不存在：{bgm}")
    path = _pipeline(project_dir).render_episode(bgm_path=bgm, bgm_volume=float(bgm_volume))
    return str(path), f"成片已输出：{path}"


with gr.Blocks(title="AutoVideo Creator Review") as demo:
    gr.Markdown(
        "# AutoVideo Creator Review\n"
        "按 **环境检查 → Storyboard → 角色定妆 → 关键帧 → I2V 镜头 → 配音/后期 → 成片** 分阶段审核。"
        "默认候选 1 会作为临时选择，但建议逐镜头人工确认后再最终渲染。"
    )

    with gr.Row():
        preflight_btn = gr.Button("运行环境检查")
        project_dir = gr.Textbox(label="项目目录", value="outputs/projects/tide-eye-episode-01")
    preflight_output = gr.Markdown()
    status = gr.Markdown()

    with gr.Tab("1. Storyboard"):
        source = gr.Textbox(
            label="故事 / 小说片段 / 内容大纲",
            lines=12,
            placeholder="例如：原创海上冒险短篇，主角在暴风雨后发现一座失落岛屿……",
        )
        project_name = gr.Textbox(label="项目名", value="tide-eye-episode-01")
        with gr.Row():
            bootstrap_btn = gr.Button("载入《潮汐之眼》精修模板", variant="primary")
            create_btn = gr.Button("让 LLM 创建新 Storyboard")
            load_btn = gr.Button("加载已有项目")
            save_storyboard_btn = gr.Button("保存 Storyboard 修改")
        storyboard = gr.Code(
            label="Storyboard JSON（可直接修改台词、角色、画面 Prompt、运镜 Prompt）",
            language="json",
            lines=28,
        )

    with gr.Tab("2. Character Bible"):
        character_id = gr.Dropdown(label="角色")
        character_count = gr.Slider(1, 6, value=3, step=1, label="候选数量")
        generate_character_btn = gr.Button("生成角色候选")
        character_gallery = gr.Gallery(label="角色候选", columns=3, height="auto")
        character_candidate_number = gr.Number(value=1, precision=0, label="确认候选编号（从 1 开始）")
        approve_character_btn = gr.Button("确认角色参考图", variant="primary")
        approved_character = gr.Image(label="当前确认角色图", type="filepath")

    with gr.Tab("3. Storyboard Keyframes"):
        scene_id = gr.Dropdown(label="分镜")
        keyframe_count = gr.Slider(1, 6, value=3, step=1, label="关键帧候选数量")
        generate_keyframe_btn = gr.Button("生成关键帧候选")
        keyframe_gallery = gr.Gallery(label="关键帧候选", columns=3, height="auto")
        keyframe_candidate_number = gr.Number(value=1, precision=0, label="确认候选编号（从 1 开始）")
        approve_keyframe_btn = gr.Button("确认关键帧", variant="primary")
        approved_keyframe = gr.Image(label="当前确认关键帧", type="filepath")

    with gr.Tab("4. I2V Shot Review"):
        motion_scene_id = gr.Dropdown(label="分镜")
        motion_count = gr.Slider(1, 4, value=2, step=1, label="动态镜头候选数量")
        generate_motion_btn = gr.Button("生成 I2V 候选")
        motion_choice = gr.Dropdown(label="镜头候选")
        motion_preview = gr.Video(label="镜头预览")
        approve_motion_btn = gr.Button("确认动态镜头", variant="primary")
        approved_motion = gr.Video(label="当前确认镜头")

    with gr.Tab("5. Final Render"):
        gr.Markdown(
            "最终阶段会按 Storyboard 中的 narration + dialogue_lines 分角色生成 TTS，"
            "生成更细粒度字幕，并把可选 BGM 混到人声和原生环境声下方。"
        )
        bgm_path = gr.Textbox(label="BGM 文件路径（可留空）", placeholder="assets/bgm/adventure.mp3")
        bgm_volume = gr.Slider(0.0, 0.5, value=0.12, step=0.01, label="BGM 音量")
        render_btn = gr.Button("渲染最终成片", variant="primary")
        final_video = gr.Video(label="最终 9:16 成片")

    preflight_btn.click(run_environment_check, outputs=[preflight_output])
    bootstrap_btn.click(
        bootstrap_first_episode,
        inputs=[project_name],
        outputs=[project_dir, storyboard, character_id, scene_id, motion_scene_id, status],
    )
    create_btn.click(
        create_project,
        inputs=[source, project_name],
        outputs=[project_dir, storyboard, character_id, scene_id, motion_scene_id, status],
    )
    load_btn.click(
        load_project,
        inputs=[project_dir],
        outputs=[storyboard, character_id, scene_id, motion_scene_id, status],
    )
    save_storyboard_btn.click(
        save_storyboard,
        inputs=[project_dir, storyboard],
        outputs=[character_id, scene_id, motion_scene_id, status],
    )
    generate_character_btn.click(
        generate_characters,
        inputs=[project_dir, character_id, character_count],
        outputs=[character_gallery, status],
    )
    approve_character_btn.click(
        approve_character,
        inputs=[project_dir, character_id, character_candidate_number],
        outputs=[approved_character, status],
    )
    generate_keyframe_btn.click(
        generate_keyframes,
        inputs=[project_dir, scene_id, keyframe_count],
        outputs=[keyframe_gallery, status],
    )
    approve_keyframe_btn.click(
        approve_keyframe,
        inputs=[project_dir, scene_id, keyframe_candidate_number],
        outputs=[approved_keyframe, status],
    )
    generate_motion_btn.click(
        generate_motions,
        inputs=[project_dir, motion_scene_id, motion_count],
        outputs=[motion_choice, motion_preview, status],
    )
    motion_choice.change(preview_motion, inputs=[motion_choice], outputs=[motion_preview])
    approve_motion_btn.click(
        approve_motion,
        inputs=[project_dir, motion_scene_id, motion_choice],
        outputs=[approved_motion, status],
    )
    render_btn.click(
        render_final,
        inputs=[project_dir, bgm_path, bgm_volume],
        outputs=[final_video, status],
    )


if __name__ == "__main__":
    demo.launch()
