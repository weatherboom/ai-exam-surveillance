"""网页界面中文文案。

只服务于 Gradio 页面的展示层：引擎内部的 incident 字典、JSON 报告、
以及烧录进输出视频的叠加文字都保持英文，因为 cv2.putText 只能渲染 ASCII，
画不出中文。
"""

import re

# 违规行为：固定文案
_VIOLATION_ZH = {
    "Prohibited Device (Cell Phone)": "违规使用电子设备（手机）",
    "Peeking & Copying from Student in Front": "偷看并抄袭前排考生",
    "Peeking / Communicating Across Aisle (Right)": "隔排偷看 / 传递信息（右侧）",
    "Peeking / Communicating Across Aisle (Left)": "隔排偷看 / 传递信息（左侧）",
    "Candidate Missing from Desk / Camera View": "考生离开座位 / 离开摄像画面",
    "Looking Away from Exam Paper": "视线离开试卷",
    "No cheating or suspicious behavior detected": "未检测到作弊或可疑行为",
}

# 违规行为：带动态数值，按正则替换
_VIOLATION_PATTERNS = [
    (
        re.compile(r"^Multiple People in Room \((\d+) detected\)$"),
        r"房间内出现多人（检测到 \1 人）",
    ),
]

_SEVERITY_ZH = {
    "CRITICAL": "严重",
    "HIGH": "高",
    "MEDIUM": "中",
    "LOW": "低",
    "CLEAN": "无异常",
}

_STUDENT_ID_ZH = {
    "Candidate": "考生",
    "All Candidates": "全部考生",
}

# 流水线在开头的失败返回
_ENGINE_ERROR_ZH = {
    "No valid video file provided.": "未提供有效的视频文件。",
    "Failed to open video file.": "无法打开该视频文件，请确认格式是否受支持。",
}


def translate_violation(text):
    """英文违规描述 -> 中文；未收录的原文返回。"""
    if not text:
        return text
    if text in _VIOLATION_ZH:
        return _VIOLATION_ZH[text]
    for pattern, repl in _VIOLATION_PATTERNS:
        if pattern.match(text):
            return pattern.sub(repl, text)
    return text


def translate_severity(text):
    return _SEVERITY_ZH.get(text, text)


def translate_student_id(text):
    """'Student #3' -> '学生 #3'。"""
    if not text:
        return text
    match = re.fullmatch(r"Student #(\d+)", text)
    if match:
        return f"学生 #{match.group(1)}"
    return _STUDENT_ID_ZH.get(text, text)


def translate_error(text):
    return _ENGINE_ERROR_ZH.get(text, text)


def build_summary(stats, incidents):
    """按 stats 重新组织中文结论，不做英文原句的逐词替换。"""
    if not stats:
        return "未获得有效的审查结果。"

    flagged_students = len({inc.get("student_id") for inc in incidents})
    return (
        f"智能监考审查完成：共追踪 {stats['total_students']} 名考生，"
        f"处理 {stats['processed_frames']} 帧画面；"
        f"记录到 {stats['flagged_incidents']} 起确认违规，"
        f"涉及 {flagged_students} 名可疑考生，"
        f"{stats['clean_students']} 名考生无异常。"
        f"考场诚信指数：{stats['integrity_score']}。"
    )
