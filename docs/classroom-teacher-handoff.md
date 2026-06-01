# 课堂教师端交接文档

## 背景

现有系统包括：

- A：游戏前端。
- B：Flask 后端，本仓库。
- C：教师端演示页面，基于 B 提供的页面和接口。

新需求是：A 中学生点击诗人、诗词、地点、事件等课堂元素后，A 调用 B；B 生成面向课堂投屏的内容；C 实时接收并展示。C 用于教师上课演示，不是教师备课后台。

## 当前交互模型

当前实现采用 SSE 长连接，不使用 WebSocket。

选择 SSE 的原因：

- C 作为前端页面先向 B 建立长连接，B 可以持续推送事件。
- 当前需求是 B 到 C 单向实时推送，SSE 足够。
- 相比 WebSocket，SSE 接入 Nginx 和 Flask 现有生产结构更简单。

数据流：

1. C 登录。
2. C 建立 `GET /api/classroom/events/stream` 长连接。
3. A 或模拟按钮调用 `POST /api/classroom/events`。
4. B 保存课堂事件，后台生成 Markdown、Mermaid、图片。
5. B 生成完成后推送 `lesson_ready`。
6. C 一次性展示完整内容，不在大屏上显示半成品。

## 页面入口

教师登录页：

`GET /api/classroom/login`

教师端页面：

`GET /api/classroom/teacher`

未登录访问教师端会跳转到登录页。登录复用现有 `/api/login`，不新增注册逻辑。

## 主要接口

### 查询课堂事件

`GET /api/classroom/events`

用途：按当前登录用户查询课堂事件历史。

参数：

- `limit`：最大返回数量，默认 100，最大 500。

### 创建课堂事件

`POST /api/classroom/events`

用途：A 游戏侧触发课堂事件，也用于教师端模拟按钮。

请求示例：

```json
{
  "type": "location",
  "name": "洛阳",
  "context": "学生点击了洛阳地点卡片。",
  "generate_ai": true,
  "generate_image": true
}
```

支持类型：

- `location`：地点。
- `person`：诗人/人物。
- `event`：事件。
- `poem`：诗词。
- `concept`：通用概念。

### 教师端事件流

`GET /api/classroom/events/stream`

响应类型：`text/event-stream`

主要事件：

- `ready`：连接建立。
- `concept`：收到 A 侧课堂事件。
- `ai_start`：AI 开始生成。
- `markdown_done`：Markdown 文案生成完成。
- `mermaid_done`：Mermaid 图生成完成。
- `mermaid_error`：Mermaid 未通过审核或生成失败。
- `image_start`：图片生成开始。
- `image_done`：图片生成完成。
- `image_error`：图片生成失败。
- `lesson_ready`：课堂内容聚合完成，C 应以此为准展示。
- `error`：整体生成失败。
- `heartbeat`：连接保活。

前端最终展示应以 `lesson_ready.payload` 为准：

```json
{
  "markdown": "## 洛阳\n...",
  "mermaid": "flowchart TD\n...",
  "images": ["/static/generated/example.png"],
  "duration_seconds": 12.3
}
```

## 展示策略

### 默认态

右侧只显示：

`等待游戏端课堂事件`

当收到课堂事件后，该提示立即隐藏，不占据展示区域。

### 生成态

右侧显示整块 loading skeleton。

不会提前显示半截 Markdown、半截图表或图片生成中的占位内容。

### 完成态

收到 `lesson_ready` 后一次性展示：

- 左侧：课堂事件列表。
- 中间：面向学生的 Markdown 讲解。
- 右侧：课堂图像和 Mermaid 理解图。
- 底部：模拟按钮、自定义输入、清空。

左侧已生成事件可点击切换回历史 lesson。

### 图片交互

课堂图像支持点击放大。

关闭方式：

- 点击右上角关闭按钮。
- 点击遮罩背景。
- 按 `Esc`。

## AI 文案策略

文案定位：直接给学生看的课堂讲解，不是教师备课稿。

当前结构：

```markdown
## 主题

### 画面入口
- ...

### 诗词里的意味
- ...

### 读懂它的三个角度
1. **画面**：...
2. **处境**：...
3. **情绪**：...

### 课堂追问
- ...

### 收束句
- ...
```

质量约束：

- 约 450-650 个汉字。
- 不写旅游介绍、百科介绍、模板填空。
- 地点类落到离别、怀古、乡愁、盛衰感。
- 人物类落到性格、命运、作品气质，不写履历表。
- 事件类落到人物处境，不写百科定义。
- 诗词类抓意象关系和情感转折。

后端有质量审核词，命中后会触发二次修订。

## Mermaid 策略

Mermaid 不限制单一类型。

当前策略：

1. 服务端先让模型选择合适图表类型，允许 `mindmap` 或 `flowchart TD`。
2. 服务端审核 Mermaid 语法。
3. 如果不合格，再强制生成简单 `flowchart TD`。
4. 如果仍不合格，使用本地兜底 `flowchart TD`。
5. 前端渲染失败时，再用客户端兜底图重试。
6. 仍失败时隐藏图表区域，不显示源码和错误文本。

重要约束：

- 不展示 Mermaid 源码。
- 不展示 `Mermaid 客户端渲染失败` 给学生。
- 拒绝 `theme: person` 这类不稳定 mindmap 写法。

## 图片生成策略

默认模型：

`step-image-edit-2`

默认参数：

- `size=768x1360`
- `steps=8`
- `cfg_scale=1.0`
- `n=1`

选择原因：

- 比 `step-2x-large` 明显更快。
- 本地测试中图片生成通常约 3 秒左右。

图片 prompt 约束：

- 满幅古典国风场景插画。
- 禁止文字、汉字、字母、书法、印章、牌匾、题款、签名、水印。
- 地点、边塞等会按主题生成场景。
- 人物类型优先使用诗意山水/意境图，避免人物肖像触发 StepFun 审核。

已知限制：

- StepFun 偶尔仍可能生成带文字的图片。
- 人物类直接画人物容易被内容审核拦截，因此当前用象征性意境图兜底。
- 当前接口一次只生成 1 张图；StepFun 对 `n` 有限制，多图需要串行多次请求，会增加等待时间。

## 数据和会话绑定

课堂事件按当前登录用户隔离。

session id 规则：

```text
user:<current_user.id>
```

A 和 C 使用同一个账号登录时，可绑定到同一课堂事件流。

## 数据库

模型：

- `app/models/classroom_event.py`

表：

- `classroom_event`

字段：

- `session_id`
- `event_type`
- `source`
- `concept_type`
- `name`
- `content`
- `event_payload`
- `created_at`

`created_at` 存储仍按 UTC，接口输出时转东八区。

## 关键文件

- `app/classroom/main.py`
- `app/models/classroom_event.py`
- `app/templates/classroom_teacher.html`
- `app/templates/classroom_login.html`
- `app/aiapi/main.py`

## 生产部署

生产目录：

`/projects/flask-server`

服务管理：

```bash
supervisorctl status flask-server
supervisorctl restart flask-server
```

生产访问：

`https://your-domain.example/api/classroom/teacher`

生产由 Nginx 对外暴露 8080，后端 Flask/Gunicorn 监听本地 8000。

## 当前状态

已上线提交：

`75028df Refine classroom teacher lesson display`

已上线能力：

- 教师端登录。
- SSE 课堂事件流。
- 模拟按钮和自定义输入。
- Markdown 教学文案。
- 图片生成与放大查看。
- Mermaid 图表生成、审核与前端兜底。
- 左侧历史事件切换。
- 东八区时间显示。

注意：

- 如果本地工作区有未提交改动，应先确认是否已推送并在 7 号生产窗口 `git pull`。
- 生产配置依赖 `app/local_config.py`，不要提交真实密钥。

## 后续建议

- 为 A 侧正式接入固定事件 payload 协议，避免自定义输入的 `concept` 类型过泛。
- 进一步沉淀不同类型的 prompt，例如地点、诗人、诗词、历史事件分别维护模板。
- 将图片生成失败原因记录到后台日志，但前端只显示可用结果。
- 如果后续需要双向控制课堂节奏，再评估 WebSocket；当前单向推送 SSE 足够。
