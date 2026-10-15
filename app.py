import gradio as gr
import pandas as pd
import json
import os
import tempfile
from src.detector import ObjectDetector
from src.pose_analyzer import PoseAnalyzer
from src.pipeline import SurveillancePipeline
from src import i18n

global_detector = ObjectDetector(model_name="yolov8n.pt", conf_thresh=0.35)
global_pose_analyzer = PoseAnalyzer(model_name="yolov8n-pose.pt")
pipeline = SurveillancePipeline(obj_detector=global_detector, pose_analyzer=global_pose_analyzer)

INCIDENT_COLUMNS = ["时间", "考生编号", "违规行为", "严重程度", "置信度"]


def build_incident_table(incidents):
    """把引擎的英文 incident 字典转成中文表头的展示用 DataFrame。

    DataFrame 的列名会覆盖 gr.DataFrame 的 headers 参数，所以列名必须在这里定成中文。
    """
    if not incidents:
        rows = [{
            "时间": "00:00",
            "考生编号": "全部考生",
            "违规行为": "未检测到作弊或可疑行为",
            "严重程度": "无异常",
            "置信度": "100%",
        }]
    else:
        rows = [{
            "时间": inc.get("timestamp", "-"),
            "考生编号": i18n.translate_student_id(inc.get("student_id", "-")),
            "违规行为": i18n.translate_violation(inc.get("violation", "-")),
            "严重程度": i18n.translate_severity(inc.get("severity", "-")),
            "置信度": inc.get("confidence", "-"),
        } for inc in incidents]

    return pd.DataFrame(rows, columns=INCIDENT_COLUMNS)


def format_kpi_cards(stats=None):
    if not stats:
        stats = {
            "total_students": "-",
            "flagged_incidents": "-",
            "clean_students": "-",
            "integrity_score": "--%"
        }
    return f"""
    <div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 14px; margin: 16px 0 20px 0;">
        <div style="background: #ffffff; border: 1px solid #e2e8f0; border-radius: 10px; padding: 16px 18px; box-shadow: 0 1px 3px rgba(0,0,0,0.04);">
            <div style="font-size: 12px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.05em; color: #64748b;">受监控考生</div>
            <div style="font-size: 28px; font-weight: 700; color: #0f172a; margin-top: 4px;">{stats['total_students']}</div>
        </div>
        <div style="background: #ffffff; border: 1px solid #e2e8f0; border-radius: 10px; padding: 16px 18px; box-shadow: 0 1px 3px rgba(0,0,0,0.04);">
            <div style="font-size: 12px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.05em; color: #ef4444;">标记违规数</div>
            <div style="font-size: 28px; font-weight: 700; color: #dc2626; margin-top: 4px;">{stats['flagged_incidents']}</div>
        </div>
        <div style="background: #ffffff; border: 1px solid #e2e8f0; border-radius: 10px; padding: 16px 18px; box-shadow: 0 1px 3px rgba(0,0,0,0.04);">
            <div style="font-size: 12px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.05em; color: #10b981;">无违规考生</div>
            <div style="font-size: 28px; font-weight: 700; color: #059669; margin-top: 4px;">{stats['clean_students']}</div>
        </div>
        <div style="background: #ffffff; border: 1px solid #e2e8f0; border-radius: 10px; padding: 16px 18px; box-shadow: 0 1px 3px rgba(0,0,0,0.04);">
            <div style="font-size: 12px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.05em; color: #3b82f6;">考场诚信指数</div>
            <div style="font-size: 28px; font-weight: 700; color: #2563eb; margin-top: 4px;">{stats['integrity_score']}</div>
        </div>
    </div>
    """

def run_surveillance(video_file, mode, frame_skip, progress=gr.Progress()):
    if not video_file:
        return (None, build_incident_table([]), None, None, format_kpi_cards(),
                "请先上传考试视频，或通过摄像头录制后再开始分析。")

    progress(0.04, desc="正在初始化检测模型...")

    def on_progress(pct, desc):
        progress(pct, desc=desc)

    output_video, incidents, summary, snapshots, stats = pipeline.process_video(
        video_path=video_file,
        mode=mode,
        frame_skip=int(frame_skip),
        progress_callback=on_progress
    )

    if not stats:
        return (output_video, build_incident_table([]), snapshots, None, format_kpi_cards(),
                f"审查未能完成：{i18n.translate_error(summary)}")

    df = build_incident_table(incidents)

    log_temp = tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False)
    json.dump({
        "summary": summary,
        "mode": mode,
        "stats": stats,
        "incidents": incidents
    }, log_temp, indent=4)
    log_temp.close()

    kpi_html = format_kpi_cards(stats)
    progress(1.0, desc="审查完成。")

    return output_video, df, snapshots, log_temp.name, kpi_html, i18n.build_summary(stats, incidents)

custom_css = """
body, .gradio-container {
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif !important;
    background-color: #f8fafc !important;
}
.header-wrapper {
    background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%);
    border-radius: 12px;
    padding: 24px 30px;
    margin-bottom: 20px;
    color: #ffffff;
    box-shadow: 0 4px 12px rgba(15, 23, 42, 0.15);
}
.app-title {
    font-size: 24px;
    font-weight: 800;
    letter-spacing: -0.02em;
    color: #ffffff;
    margin: 0;
}
.app-subtitle {
    font-size: 14px;
    color: #94a3b8;
    margin-top: 4px;
}
.badge-online {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    background: rgba(16, 185, 129, 0.15);
    color: #34d399;
    border: 1px solid rgba(16, 185, 129, 0.3);
    padding: 3px 10px;
    border-radius: 20px;
    font-size: 12px;
    font-weight: 600;
}
.section-title {
    font-size: 15px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.04em;
    color: #334155;
    margin-bottom: 10px;
}
"""

with gr.Blocks(title="AEGIS 智能监考系统") as demo:
    gr.HTML("""
    <div class="header-wrapper">
        <div style="display: flex; justify-content: space-between; align-items: center;">
            <div>
                <h1 class="app-title">AEGIS // 智能监考系统</h1>
                <div class="app-subtitle">自动化的考场诚信核验与异常行为检测</div>
            </div>
            <div class="badge-online">
                <span style="font-size: 10px;">●</span> 系统就绪
            </div>
        </div>
    </div>
    """)

    kpi_display = gr.HTML(format_kpi_cards())

    with gr.Row():
        with gr.Column(scale=5):
            gr.Markdown("<div class='section-title'>1. 监考视频输入</div>")
            video_input = gr.Video(
                label="源视频流",
                sources=["upload", "webcam"],
                interactive=True
            )

            with gr.Accordion("参数设置", open=True):
                mode_select = gr.Radio(
                    choices=[
                        ("教室 / 考场监控（CCTV）", "Classroom / Exam Hall (CCTV)"),
                        ("远程在线考试（摄像头）", "Remote Online Exam (Webcam)")
                    ],
                    value="Classroom / Exam Hall (CCTV)",
                    label="考场环境"
                )
                frame_skip_slider = gr.Slider(
                    minimum=1,
                    maximum=6,
                    value=3,
                    step=1,
                    label="抽帧间隔（加速）",
                    info="数值越大处理越快，但检测精度会下降"
                )

            analyze_btn = gr.Button("开始分析", variant="primary", size="lg")

            gr.Examples(
                examples=[
                    ["sample_videos/155164-809618953.mp4", "Classroom / Exam Hall (CCTV)", 3],
                    ["sample_videos/7092083-hd_1920_1080_30fps.mp4", "Classroom / Exam Hall (CCTV)", 3]
                ],
                example_labels=["教室监控示例一", "教室监控示例二"],
                inputs=[video_input, mode_select, frame_skip_slider],
                label="快速示例视频（点击加载）"
            )

        with gr.Column(scale=6):
            gr.Markdown("<div class='section-title'>2. 标注后的输出画面</div>")
            status_banner = gr.Markdown("等待载入考试视频流。")
            video_output = gr.Video(
                label="监考输出画面",
                interactive=False
            )

    with gr.Row():
        with gr.Column():
            gr.Markdown("<div class='section-title'>3. 违规证据截图</div>")
            evidence_gallery = gr.Gallery(
                label="违规截图",
                show_label=False,
                columns=4,
                rows=1,
                height="auto",
                object_fit="contain"
            )

    with gr.Row():
        with gr.Column():
            gr.Markdown("<div class='section-title'>4. 违规事件记录</div>")
            incident_table = gr.DataFrame(
                headers=INCIDENT_COLUMNS,
                datatype=["str", "str", "str", "str", "str"],
                label="违规记录明细",
                interactive=False
            )
            with gr.Row():
                download_json_btn = gr.File(label="下载审查报告（JSON）")

    analyze_btn.click(
        fn=run_surveillance,
        inputs=[video_input, mode_select, frame_skip_slider],
        outputs=[video_output, incident_table, evidence_gallery, download_json_btn, kpi_display, status_banner]
    )

if __name__ == "__main__":
    demo.launch(server_name="0.0.0.0", server_port=7860, share=True)
