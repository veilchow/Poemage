from __future__ import annotations

import ast
import fnmatch
import os
import re
import shutil
import stat
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT.parent / "dreamiverse-backend"
DEST = ROOT

COPY_ITEMS = (
    "app",
    "docs",
    "run.py",
    "requirements.txt",
    "README.md",
    ".env.example",
    ".gitignore",
)

EXCLUDE_PATTERNS = (
    ".git",
    ".git/*",
    "venv",
    "venv/*",
    ".venv",
    ".venv/*",
    "__pycache__",
    "*/__pycache__/*",
    "*.pyc",
    "*.pyo",
    "*.log",
    "local-server*.log",
    ".env",
    ".env.*",
    "app/local_config.py",
    "app/static/generated",
    "app/static/generated/*",
)

REDACTION_PATTERNS = (
    (re.compile(r"https://[A-Za-z0-9.-]+(?::8080)?(?=(?:/api|/classroom|[`\"'\s)]|$))"), "https://your-domain.example"),
    (re.compile(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]*dreamiverse-backend"), "your-org/poemage"),
)

CORE_FUNCTIONS = {
    "is_poem_related",
    "extract_knowledge_excerpt",
    "build_literary_hint",
    "build_teaching_prompt",
    "teaching_content_needs_revision",
    "build_revision_prompt",
    "infer_visual_scene",
    "build_safe_symbolic_image_prompt",
    "build_image_prompt",
    "sanitize_mermaid_label",
    "deterministic_mindmap_nodes",
    "build_deterministic_mindmap",
    "validate_mermaid_code",
}

CORE_IMPORT = """from app.classroom.core import (
    build_deterministic_mindmap,
    build_image_prompt,
    build_revision_prompt,
    build_teaching_prompt,
    teaching_content_needs_revision,
    validate_mermaid_code,
)
"""


PUBLIC_CORE = '''"""Public classroom engine fallback.

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
        "请生成一份可投屏的中学语文课堂 Markdown 知识素材。\\n\\n"
        f"## {name}：{extension_title}\\n\\n"
        "### 基础信息卡\\n"
        f"- 类型：{concept_type}\\n"
        f"- 课堂背景：{context}\\n"
        f"- 扩展方向：{extension_instruction or extension_title}\\n\\n"
        "### 知识点\\n"
        "- 请列出可靠事实、文本线索、关键意象和课堂可讲的解释。\\n"
        "- 如涉及诗词，请优先展示已知原文，再做简要赏析。\\n\\n"
        "### 易错点与记忆法\\n"
        "- 补充学生容易混淆的知识点。\\n\\n"
        "### 收束句\\n"
        "- 用 2-3 句总结本知识点和文本理解的关系。"
    )


def teaching_content_needs_revision(content, data=None):
    return any(token in content for token in ("解释它如何", "角度一", "想象一下"))


def build_revision_prompt(data, content):
    return (
        "请保持原有 Markdown 栏目，重写为知识密度更高、事实更严谨的课堂素材。\\n\\n"
        f"原稿：\\n{content}"
    )


def build_image_prompt(data, teaching_content):
    return (
        "满幅古典国风场景插画，淡彩水墨、水彩晕染、细腻线稿。"
        "不要书本、卷轴、纸张、碑刻、牌匾、印章、题字区域、标签区域。"
        "NO TEXT, no letters, no Chinese characters, no calligraphy, no watermark."
        "只生成无字的课堂配图。"
    )


def _sanitize_mermaid_label(value, fallback="课堂概念", max_len=10):
    label = re.sub(r"[^\\u4e00-\\u9fffA-Za-z0-9]", "", str(value or ""))
    return (label[:max_len] or fallback)[:max_len]


def build_deterministic_mindmap(data):
    name = data.get("name") or data.get("description") or "课堂概念"
    nodes = ("基础信息", "文本线索", "关键意象", "情感变化", "课堂追问")
    return "\\n".join([
        "mindmap",
        f"  root(({_sanitize_mermaid_label(name)}))",
        *[f"    {_sanitize_mermaid_label(node)}" for node in nodes],
    ])


def validate_mermaid_code(code, chart_type=None):
    if not code or "<script" in code or "</" in code:
        return False
    lines = [line.rstrip() for line in code.splitlines() if line.strip()]
    return bool(lines and lines[0] == "mindmap")
'''


LOCAL_CONFIG_EXAMPLE = '''import os

SECRET_KEY = os.getenv("SECRET_KEY", "change-me")
USERNAME = os.getenv("MYSQL_USER", "root")
PASSWORD = os.getenv("MYSQL_PASSWORD", "")
HOST = os.getenv("MYSQL_HOST", "127.0.0.1")
PORT = os.getenv("MYSQL_PORT", "3306")
DATABASE = os.getenv("MYSQL_DATABASE", "flaskserver")
STEPFUN_KEY = os.getenv("STEPFUN_KEY", "")
'''


OPEN_README = r'''# Poemage

Poemage 是一个面向诗词学习场景的游戏后端与教师端演示项目。它提供 Flask API、用户与学习数据服务、诗词内容接口、AI 文本/图像调用入口，以及一个用于课堂投屏的教师端页面。

这个仓库是 Poemage 的开源发行版，重点展示 B-C 侧能力：后端服务与教师端课堂演示。游戏客户端 A 不包含在本仓库中。

## 功能概览

- 用户登录与会话管理
- 诗词、创作、任务、存档、行为、经济、学习数据等游戏服务接口
- AI 文本流式输出接口
- AI 图片生成接口
- 教师端课堂事件接收与展示
- 教师端动态教学文案、课堂图像、思维导图组件
- A 游戏端到 B 后端，再到 C 教师端的课堂事件链路

## 项目定位

Poemage 适合用于以下场景：

- 诗词游戏或教育游戏的 Flask 后端参考实现
- 课堂大屏教师端原型
- 游戏行为触发教学内容生成的 B-C 架构示例
- 基于 SSE 的课堂事件实时展示
- AI 教学内容生成管线的工程集成参考

> 说明：本开源发行版中的 `app/classroom/core.py` 是公开 fallback 实现，用于保证项目可运行与结构可理解。生产环境中的高级 prompt 管线、知识路由、内容校验策略可以通过替换该模块接入。

## 架构概览

```mermaid
flowchart LR
    A[游戏端 A] -->|HTTP: 课堂事件| B[Flask 后端 B]
    B -->|写入课堂事件| DB[(MySQL)]
    C[教师端 C] -->|SSE 长连接| B
    B -->|实时推送概念与组件状态| C
    B -->|文本/图片生成| AI[AI Provider]
    AI -->|Markdown / Image| B
    B -->|lesson_ready / image_done| C
```

## 教师端流程

```mermaid
sequenceDiagram
    participant A as 游戏端 A
    participant B as Flask 后端 B
    participant DB as 数据库
    participant C as 教师端 C
    participant AI as AI 服务

    C->>B: GET /api/classroom/events/stream
    A->>B: POST /api/classroom/events
    B->>DB: 保存课堂概念事件
    B-->>C: concept
    C->>B: POST /api/classroom/events/{id}/generate
    B-->>C: lesson_component_start
    B->>AI: 生成课堂文案
    AI-->>B: Markdown delta
    B-->>C: markdown_delta / markdown_done
    B-->>C: mermaid_done
    B-->>C: lesson_ready
    B->>AI: 后台生成课堂图像
    AI-->>B: image
    B-->>C: image_done
```

## 模块结构

```mermaid
flowchart TB
    App[app] --> Auth[auth 用户认证]
    App --> Poem[poem 诗词数据]
    App --> Creation[creation 创作数据]
    App --> Mission[mission 任务]
    App --> Save[save 存档]
    App --> Learn[learndata 学习数据]
    App --> AI[aiapi AI 文本/图片接口]
    App --> Classroom[classroom 教师端]
    App --> Models[models 数据模型]

    Classroom --> Teacher[classroom_teacher.html]
    Classroom --> Core[core.py 公开课堂引擎]
    Classroom --> Events[classroom_event 事件流]
```

## 目录结构

```text
Poemage/
├── app/
│   ├── aiapi/              # AI 文本与图片接口
│   ├── auth/               # 登录与认证
│   ├── classroom/          # 教师端课堂事件与展示
│   ├── models/             # SQLAlchemy 数据模型
│   ├── poem/               # 诗词接口
│   ├── templates/          # 教师端页面
│   └── ...
├── docs/                   # API 与交接文档
├── tools/                  # 开源发行导出工具
├── requirements.txt
├── run.py
└── README.md
```

## 快速开始

### 1. 创建虚拟环境

```bash
python -m venv .venv
source .venv/bin/activate
```

Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

### 2. 安装依赖

```bash
pip install -r requirements.txt
```

### 3. 配置环境变量

可以复制示例配置：

```bash
cp app/local_config.example.py app/local_config.py
```

或使用环境变量：

```bash
export SECRET_KEY="change-me"
export MYSQL_HOST="127.0.0.1"
export MYSQL_PORT="3306"
export MYSQL_USER="root"
export MYSQL_PASSWORD="your-password"
export MYSQL_DATABASE="flaskserver"
export STEPFUN_KEY="your-stepfun-key"
export STEPFUN_API_BASE="https://api.stepfun.com/v1"
```

Windows PowerShell:

```powershell
$env:SECRET_KEY="change-me"
$env:MYSQL_HOST="127.0.0.1"
$env:MYSQL_PORT="3306"
$env:MYSQL_USER="root"
$env:MYSQL_PASSWORD="your-password"
$env:MYSQL_DATABASE="flaskserver"
$env:STEPFUN_KEY="your-stepfun-key"
$env:STEPFUN_API_BASE="https://api.stepfun.com/v1"
```

### 4. 初始化数据库

确保 MySQL 已创建数据库，例如：

```sql
CREATE DATABASE flaskserver DEFAULT CHARACTER SET utf8mb4;
```

初始化表：

```bash
flask --app run.py initdb
```

### 5. 启动服务

```bash
python run.py
```

默认访问：

- API: `http://127.0.0.1:5000/api`
- 教师端: `http://127.0.0.1:5000/api/classroom/teacher`

## 教师端课堂事件

游戏端可以向后端发送课堂事件：

```http
POST /api/classroom/events
Content-Type: application/json
```

示例：

```json
{
  "user_id": 1,
  "type": "诗词",
  "description": "拨闷",
  "context": "老师带着学生探索杜甫客居蜀中时期的诗词世界。"
}
```

教师端通过 SSE 监听事件：

```http
GET /api/classroom/events/stream
```

更多协议说明见：

- [游戏端课堂 API](docs/classroom-api-for-game-client.md)
- [教师端交接文档](docs/classroom-teacher-handoff.md)
- [AI 生成管线](docs/ai-generation-pipeline.md)

## AI 能力接入

`app/aiapi` 提供文本与图片接口，默认通过 OpenAI 兼容 SDK 访问 AI Provider。你可以通过环境变量配置：

- `STEPFUN_KEY`
- `STEPFUN_API_BASE`
- `STEPFUN_CHAT_MODEL`
- `STEPFUN_IMAGE_MODEL`

课堂内容生成相关逻辑位于：

```text
app/classroom/core.py
```

开源版提供的是简化 fallback。你可以替换该模块以接入自己的：

- prompt 模板
- 知识库召回
- 文案质量校验
- Mermaid 生成策略
- 图片 prompt 策略

## 配置与安全

请不要提交真实配置：

- `app/local_config.py`
- `.env`
- 数据库密码
- API Key
- 生产域名和服务器地址
- 生成图片与运行日志

本仓库提供的 `tools/export_open_source.py` 可用于从内部仓库导出公开发行版，并自动排除敏感配置与运行产物。

## 开发建议

```bash
python -m compileall app
```

如果你修改教师端页面，建议同时检查：

- 登录流程
- 课堂事件列表
- SSE 事件流
- 教学文案生成
- Mermaid 渲染
- 图片生成失败状态

## 技术栈

- Python 3
- Flask
- Flask-Login
- Flask-Cors
- Flask-SQLAlchemy
- Flask-Migrate
- MySQL / PyMySQL
- OpenAI-compatible SDK
- Server-Sent Events
- Mermaid

## 许可证

请在正式发布前补充许可证文件，例如 MIT、Apache-2.0 或其他适合你项目的开源协议。

## 致谢

Poemage 关注“游戏探索行为如何转化为课堂可讲内容”。如果你正在做诗词教育、互动课堂或教育游戏，希望这个项目能提供一个可运行的工程起点。
'''


def should_exclude(relative_path: str) -> bool:
    normalized = relative_path.replace(os.sep, "/")
    return any(fnmatch.fnmatch(normalized, pattern) for pattern in EXCLUDE_PATTERNS)


def remove_readonly(func, path, _exc_info):
    Path(path).chmod(stat.S_IWRITE)
    func(path)


def clean_destination() -> None:
    for item in COPY_ITEMS:
        target = DEST / item
        if target.is_dir():
            shutil.rmtree(target, onerror=remove_readonly)
        elif target.exists():
            target.chmod(target.stat().st_mode | stat.S_IWRITE)
            target.unlink()


def copy_tree_item(item: str) -> None:
    source = SOURCE / item
    target = DEST / item
    if source.is_file():
        if not should_exclude(item):
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)
        return

    for path in source.rglob("*"):
        relative = path.relative_to(SOURCE)
        relative_text = relative.as_posix()
        if should_exclude(relative_text):
            continue
        destination = DEST / relative
        if path.is_dir():
            destination.mkdir(parents=True, exist_ok=True)
        else:
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, destination)


def redact_text_files() -> None:
    text_suffixes = {".py", ".md", ".txt", ".example", ".html", ".js", ".css", ".json"}
    for path in DEST.rglob("*"):
        if not path.is_file() or "tools" in path.relative_to(DEST).parts:
            continue
        if path.suffix not in text_suffixes and path.name != ".env.example":
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        for pattern, replacement in REDACTION_PATTERNS:
            text = pattern.sub(replacement, text)
        path.chmod(path.stat().st_mode | stat.S_IWRITE)
        path.write_text(text, encoding="utf-8", newline="\n")


def replace_classroom_core() -> None:
    main_path = DEST / "app" / "classroom" / "main.py"
    source = main_path.read_text(encoding="utf-8")
    tree = ast.parse(source)
    lines = source.splitlines()

    remove_ranges = []
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name in CORE_FUNCTIONS:
            remove_ranges.append((node.lineno, node.end_lineno))

    remove_lines = set()
    for start, end in remove_ranges:
        remove_lines.update(range(start, end + 1))

    output = []
    inserted = False
    for index, line in enumerate(lines, start=1):
        if index in remove_lines:
            continue
        output.append(line)
        if not inserted and line.startswith("from app.models.classroom_event import "):
            output.append("")
            output.extend(CORE_IMPORT.rstrip().splitlines())
            inserted = True

    main_path.write_text("\n".join(output).rstrip() + "\n", encoding="utf-8", newline="\n")

    core_path = DEST / "app" / "classroom" / "core.py"
    core_path.write_text(PUBLIC_CORE, encoding="utf-8", newline="\n")


def write_examples() -> None:
    (DEST / "app" / "local_config.example.py").write_text(
        LOCAL_CONFIG_EXAMPLE,
        encoding="utf-8",
        newline="\n",
    )
    (DEST / "README.md").write_text(OPEN_README, encoding="utf-8", newline="\n")


def scan_sensitive_tokens() -> list[str]:
    patterns = (
        re.compile(r"BEGIN (RSA |EC |OPENSSH |)PRIVATE KEY"),
        re.compile(r"PASSWORD\s*=\s*[\"'][^\"']{6,}[\"']"),
        re.compile(r"STEPFUN_KEY\s*=\s*[\"'][A-Za-z0-9_-]{20,}[\"']"),
        re.compile(r"(api[_-]?key|token|secret)\s*[:=]\s*[\"'][A-Za-z0-9_-]{20,}[\"']", re.I),
        re.compile(r"HOST\s*=\s*[\"'](?:\d{1,3}\.){3}\d{1,3}[\"']"),
        re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}"),
    )
    findings = []
    allowed_example_values = {
        "127.0.0.1",
        "localhost",
        "your-password",
        "change-me",
        "your-stepfun-key",
    }
    for path in DEST.rglob("*"):
        if not path.is_file() or "tools" in path.relative_to(DEST).parts:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        for pattern in patterns:
            for match in pattern.finditer(text):
                if any(value in match.group(0) for value in allowed_example_values):
                    continue
                findings.append(f"{path.relative_to(DEST)}: matches {pattern.pattern}")
    return findings


def main() -> None:
    if not SOURCE.exists():
        raise SystemExit(f"Source repository not found: {SOURCE}")

    clean_destination()
    for item in COPY_ITEMS:
        copy_tree_item(item)

    redact_text_files()
    replace_classroom_core()
    write_examples()

    findings = scan_sensitive_tokens()
    if findings:
        print("Sensitive scan failed:")
        for finding in findings:
            print(f"  - {finding}")
        raise SystemExit(1)

    print(f"Open distribution exported to {DEST}")


if __name__ == "__main__":
    main()
