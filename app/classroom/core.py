"""Public classroom engine fallback.

The production project can replace this module with a private or obfuscated
implementation. This file keeps the open distribution runnable without
publishing the production prompt pipeline.
"""

import re


def build_teaching_prompt(data):
    concept_type = data.get("concept_type") or data.get("type") or "concept"
    name = data.get("name") or data.get("description") or "当前对象"
    context = data.get("context") or ""
    extension = data.get("extension") or {}
    extension_title = extension.get("title") or data.get("extension_title") or "基础讲解"
    extension_instruction = extension.get("instruction") or data.get("extension_instruction") or ""
    return (
        "请生成一份可投屏的中学语文课堂 Markdown 知识素材。\n\n"
        f"## {name}：{extension_title}\n\n"
        "### 基础信息卡\n"
        f"- 类型：{concept_type}\n"
        f"- 课堂背景：{context}\n"
        f"- 扩展方向：{extension_instruction or extension_title}\n\n"
        "### 知识点\n"
        "- 请列出可靠事实、文本线索、关键意象和课堂可讲的解释。\n"
        "- 如涉及诗词，请优先展示已知原文，再做简要赏析。\n\n"
        "### 易错点与记忆法\n"
        "- 补充学生容易混淆的知识点。\n\n"
        "### 收束句\n"
        "- 用 2-3 句总结本知识点和文本理解的关系。"
    )


def teaching_content_needs_revision(content, data=None):
    return any(token in content for token in ("解释它如何", "角度一", "想象一下"))


def build_revision_prompt(data, content):
    return (
        "请保持原有 Markdown 栏目，重写为知识密度更高、事实更严谨的课堂素材。\n\n"
        f"原稿：\n{content}"
    )


def build_image_prompt(data, teaching_content):
    return (
        "满幅古典国风场景插画，淡彩水墨、水彩晕染、细腻线稿。"
        "不要书本、卷轴、纸张、碑刻、牌匾、印章、题字区域、标签区域。"
        "NO TEXT, no letters, no Chinese characters, no calligraphy, no watermark."
        "只生成无字的课堂配图。"
    )


def _sanitize_mermaid_label(value, fallback="课堂概念", max_len=10):
    label = re.sub(r"[^\u4e00-\u9fffA-Za-z0-9]", "", str(value or ""))
    return (label[:max_len] or fallback)[:max_len]


def build_deterministic_mindmap(data):
    name = data.get("name") or data.get("description") or "课堂概念"
    nodes = ("基础信息", "文本线索", "关键意象", "情感变化", "课堂追问")
    return "\n".join([
        "mindmap",
        f"  root(({_sanitize_mermaid_label(name)}))",
        *[f"    {_sanitize_mermaid_label(node)}" for node in nodes],
    ])


def validate_mermaid_code(code, chart_type=None):
    if not code or "<script" in code or "</" in code:
        return False
    lines = [line.rstrip() for line in code.splitlines() if line.strip()]
    return bool(lines and lines[0] == "mindmap")
