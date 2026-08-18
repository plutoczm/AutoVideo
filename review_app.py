import json
import re
from pathlib import Path

import gradio as gr
from dotenv import load_dotenv

from autovideo.creator import CreatorPipeline
from autovideo.project_store import ProjectStore


load_dotenv()
DEFAULT_PROJECTS_DIR = Path("outputs/projects")


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
        "已生成 Storyboard。先审核剧情和角色设定，再生成候选图。",
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


def render_final(project_dir: str):
    path = _pipeline(project_dir).render_episode()
    return str(path), f"成片已输出：{path}"


with gr.Blocks(title="AutoVideo Creator Review") as demo:
    gr.Markdown(
        "# AutoVideo Creator Review\n"
        "按 **Storyboard → 角色定妆 → 关键帧 → I2V 镜头 → 成片** 分阶段审核。"
        "默认候选 1 会作为临时选择，但建议逐镜头人工确认后再最终渲染。"
    )

    project_dir = gr.Textbox(label="项目目录", value="outputs/projects/episode-01")
    status = gr.Markdown()

    with gr.Tab("1. Storyboard"):
        source = gr.Textbox(
            label="故事 / 小说片段 / 内容大纲",
            lines=12,
            placeholder="例如：原创海上冒险短篇，主角在暴风雨后发现一座失落岛屿……",
        )
        project_name = gr.Textbox(label="项目名", value="episode-01")
        with gr.Row():
            create_btn = gr.Button("创建新项目", variant="primary")
            load_btn = gr.Button("加载项目")
        storyboard = gr.Code(label="Storyboard JSON", language="json", lines=28)

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
        gr.Markdown("确认所有角色、关键帧和动态镜头后，再进行 TTS、字幕、音轨混合和最终合成。")
        render_btn = gr.Button("渲染最终成片", variant="primary")
        final_video = gr.Video(label="最终 9:16 成片")

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
    render_btn.click(render_final, inputs=[project_dir], outputs=[final_video, status])


if __name__ == "__main__":
    demo.launch()
