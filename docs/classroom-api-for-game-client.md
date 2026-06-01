# A-B-C 课堂联动 API 文档

更新时间：2026-05-28

本文档描述游戏端 A、服务端 B、教师端 C 的课堂联动接口。当前实现基于同一账号绑定：A 创建课堂事件时必须传 `user_id`，B 会把课堂事件写入 `session_id = user:{user_id}`，C 使用同一账号登录后通过 SSE 实时接收。

## 基础信息

本地开发地址：

```text
http://127.0.0.1:5001/api
```

生产地址：

```text
https://your-domain.example/api
```

教师端 C 依赖登录态 Cookie。游戏端 A 创建课堂事件时可以不依赖 Cookie，但必须在请求体中传登录接口返回的 `user_id`。

## 前置依赖

- 用户账号必须已存在。当前不要求教师端另行注册。
- A 游戏端和 C 教师端需要使用同一个账号登录，才能看到同一批课堂事件。
- B 端依赖数据库中的 `classroom_event` 表，服务启动时会按需创建。
- AI 生成依赖 StepFun 文本模型和图片模型相关环境变量。
- 课堂知识库文件位于 `app/classroom/knowledge_base.md`，B 端生成文案时会参考。
- 图片生成结果会保存到 `/static/generated/`，返回给 C 端的是可访问 URL。

## 1. 登录

```http
POST /api/login
Content-Type: application/json
```

请求体：

```json
{
  "username": "teacher_test",
  "password": "teacher_test"
}
```

成功响应 `200`：

```json
{
  "message": "登录成功",
  "user_id": 205
}
```

失败响应：

```json
// 401
{"message": "用户名不存在"}

// 402
{"message": "用户名或密码错误"}
```

教师端 C 后续请求必须携带 Cookie。游戏端 A 需要保存该响应里的 `user_id`，并在创建课堂事件时传给 B。

## 2. A 创建课堂概念事件

A 游戏端点击地点、诗人、事件等元素后，请调用此接口。该接口只创建“课堂概念事件”，默认不直接生成教案。

```http
POST /api/classroom/events
Content-Type: application/json
```

请求体：

```json
{
  "user_id": 205,
  "context": "老师带着学生在诗词世界中探索古都洛阳，学生刚刚点击了地图上的洛阳。当前课堂目标是理解地点怎样承载乡愁、离别与历史兴衰。",
  "type": "地点",
  "description": "洛阳"
}
```

字段说明：

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `user_id` | number/string | 是 | `/api/login` 成功响应中的 `user_id`。B 用它绑定 C 的教师账号 |
| `context` | string | 建议 | A 侧课堂上下文/游戏背景，权重高于知识库 |
| `type` | enum/string | 是 | 概念类型，支持中文或英文别名 |
| `description` | string | 是 | 被点击或关注的具体内容，例如 `洛阳`、`李白`、`安史之乱` |
| `generate_ai` | boolean | 否 | 默认 `false`。一般不建议 A 端传 `true`，生成应由 C 端确认扩展项后触发 |

语义约定：

- `context` 只表示课堂上下文、游戏背景或教师当前教学意图。
- `description` 表示课堂概念的具体内容；B 会用它作为左侧概念标题和教案主题。

支持的类型：

| 中文 | 内部值 |
| --- | --- |
| 地点 | `location` |
| 诗人 / 人物 | `person` |
| 事件 | `event` |
| 诗词 / 诗作 | `poem` |
| 文化 | `culture` |
| 历史 | `history` |
| 技法 | `technique` |
| 主题 | `theme` |
| 概念 | `concept` |

成功响应 `201`：

```json
{
  "event": {
    "id": 1495,
    "session_id": "user:205",
    "event_type": "concept",
    "source": "A",
    "concept_type": "location",
    "name": "洛阳",
    "content": "老师带着学生在诗词世界中探索古都洛阳...",
    "payload": {
      "type": "location",
      "concept_type": "location",
      "context": "老师带着学生在诗词世界中探索古都洛阳...",
      "name": "洛阳",
      "description": "洛阳"
    },
    "created_at": "2026-05-28T12:29:09+08:00"
  }
}
```

失败响应：

```json
// 400
{"message": "缺少 user_id"}

// 400
{"message": "user_id 必须是数字"}
```

## 3. C 查询课堂事件列表

教师端 C 可用此接口恢复当前账号下的历史课堂事件。

```http
GET /api/classroom/events?limit=100
Cookie: session=...
```

参数：

| 参数 | 类型 | 默认 | 说明 |
| --- | --- | --- | --- |
| `limit` | number | 100 | 最多 500 |

成功响应 `200`：

```json
{
  "events": [
    {
      "id": 1495,
      "session_id": "user:205",
      "event_type": "concept",
      "source": "A",
      "concept_type": "location",
      "name": "洛阳",
      "content": "老师带着学生在诗词世界中探索古都洛阳...",
      "payload": {
        "type": "location",
        "context": "老师带着学生在诗词世界中探索古都洛阳...",
        "description": "洛阳"
      },
      "created_at": "2026-05-28T12:29:09+08:00"
    }
  ]
}
```

失败响应：

```json
// 401
{"message": "请先登录"}
```

## 4. C 订阅课堂事件流

C 端使用 SSE 接收 B 的实时事件。

```http
GET /api/classroom/events/stream
Accept: text/event-stream
Cookie: session=...
```

可选参数：

| 参数 | 类型 | 说明 |
| --- | --- | --- |
| `replay` | `1` | 设置为 `1` 时从 `last_id` 后开始补放事件 |
| `last_id` | number | `replay=1` 时有效 |

连接成功事件：

```text
event: ready
data: {"session_id":"user:205","last_id":1495}
```

无新事件时心跳：

```text
event: heartbeat
data: {"session_id":"user:205","last_id":1495}
```

常见事件类型：

| event | 来源 | 说明 |
| --- | --- | --- |
| `concept` | A | A 创建的新课堂概念 |
| `lesson_component_start` | B | C 已触发某个扩展项组件生成 |
| `ai_start` | B | 文案生成开始 |
| `markdown_delta` | B | 文案流式增量，C 应立即追加显示 |
| `markdown_done` | B | 文案最终结果 |
| `mermaid_start` | B | Mermaid 图表生成开始 |
| `mermaid_done` | B | Mermaid 思维导图生成完成，`payload.chart_type` 固定为 `mindmap` |
| `mermaid_error` | B | 单个 Mermaid 图表失败，C 应隐藏对应图表区域 |
| `image_start` | B | 图片生成开始 |
| `image_done` | B | 图片生成完成，`payload.urls` 是图片 URL 数组 |
| `image_error` | B | 图片生成失败 |
| `lesson_ready` | B | 当前三合一组件完成 |
| `error` | B | 生成流程异常 |

示例 `markdown_delta`：

```text
event: markdown_delta
data: {
  "id": 1501,
  "event_type": "markdown_delta",
  "source": "B",
  "content": "## 洛阳：地点介绍\n\n### 画面入口\n...",
  "payload": {
    "component_id": "1495-location_intro-1716880000000",
    "concept_event_id": 1495,
    "extension": {
      "id": "location_intro",
      "title": "地点介绍"
    }
  }
}
```

示例 `mermaid_done`：

```text
event: mermaid_done
data: {
  "event_type": "mermaid_done",
  "content": "mindmap\n  root((洛阳))\n    画面\n    处境\n    情绪\n    诗意\n    追问",
  "payload": {
    "component_id": "1495-location_intro-1716880000000",
    "concept_event_id": 1495,
    "chart_type": "mindmap"
  }
}
```

示例 `lesson_ready`：

```text
event: lesson_ready
data: {
  "event_type": "lesson_ready",
  "content": "## 洛阳：地点介绍...",
  "payload": {
    "component_id": "1495-location_intro-1716880000000",
    "concept_event_id": 1495,
    "markdown": "## 洛阳：地点介绍...",
    "mermaid": "mindmap\n  root((洛阳))\n    ...",
    "mermaids": {
      "mindmap": "mindmap\n  root((洛阳))\n    ..."
    },
    "images": ["/static/generated/xxx.png"],
    "duration_seconds": 21.3
  }
}
```

## 5. C 触发教学组件生成

C 点击某个概念的扩展项后，调用此接口。这个接口会异步启动 AI 生成，立即返回 `202`。

```http
POST /api/classroom/events/{event_id}/generate
Content-Type: application/json
Cookie: session=...
```

请求体：

```json
{
  "component_id": "1495-location_intro-1716880000000",
  "context": "老师补充：本节课聚焦乡愁和历史兴衰。",
  "type": "location",
  "description": "洛阳",
  "extension": {
    "id": "location_intro",
    "title": "地点介绍",
    "description": "地点的基本信息、地理位置和诗词画面入口。",
    "instruction": "讲清地点的方位、历史气质、画面感，以及它为什么容易进入诗词。"
  },
  "generate_image": true
}
```

字段说明：

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `component_id` | string | 否 | C 端生成的组件 ID；不传则 B 自动生成 |
| `context` | string | 否 | 覆盖课堂上下文/背景 |
| `type` | string | 否 | 覆盖原类型 |
| `description` | string | 否 | 覆盖具体内容 |
| `extension` | object | 建议 | 教师选择的扩展项 |
| `generate_image` | boolean | 否 | 默认 `true` |
| `image_model` | string | 否 | 覆盖图片模型，默认 `step-image-edit-2` |
| `image_size` | string | 否 | 覆盖图片尺寸，默认 `1024x1024` |
| `image_steps` | number | 否 | 覆盖图片步数，默认 `4` |
| `image_cfg_scale` | number | 否 | 覆盖图片 CFG，默认 `1.0` |
| `image_timeout` | number | 否 | 覆盖图片接口超时时间，默认 `35` 秒 |

说明：

- B 会先发送 Markdown 流式内容。
- Mindmap 由 B 使用固定模板生成，不再调用 AI 生成 Mermaid 语法，因此不会因为模型输出格式导致渲染失败。
- 图片生成仍依赖 StepFun 图片接口。B 会先返回 `lesson_ready`，图片在独立后台任务完成后再发送 `image_done`，默认使用当前图片模型支持的 `1024x1024` 尺寸，避免为了速度牺牲课堂展示质量。

成功响应 `202`：

```json
{
  "component_id": "1495-location_intro-1716880000000",
  "concept_event_id": 1495,
  "extension": {
    "id": "location_intro",
    "title": "地点介绍",
    "instruction": "讲清地点的方位、历史气质、画面感..."
  }
}
```

失败响应：

```json
// 401
{"message": "请先登录"}

// 404
{"message": "课堂概念不存在"}
```

## A 端推荐调用方式

A 端只需要在课堂元素被点击时调用：

```js
await fetch("/api/classroom/events", {
  method: "POST",
  credentials: "same-origin",
  headers: {"Content-Type": "application/json"},
  body: JSON.stringify({
    user_id: 205,
    type: "地点",
    context: "老师带着学生在诗词世界中探索古都洛阳，学生刚刚点击了地图上的洛阳。",
    description: "洛阳"
  })
});
```

不要由 A 端直接传 `generate_ai: true`，否则会绕过 C 端的二次确认和扩展项选择。

## C 端推荐处理方式

- 建立 `/api/classroom/events/stream` 的 SSE 连接。
- 收到 `concept` 后在左侧列表新增概念。
- 用户选择扩展项后调用 `/api/classroom/events/{event_id}/generate`。
- 收到 `markdown_delta` 时立即追加显示文本。
- 收到 `image_done` 后展示图片。
- 收到 `mermaid_done` 后按 `payload.chart_type` 渲染：
  - `mindmap`：思维导图
- 收到 `mermaid_error` 时隐藏对应图表，不显示 Mermaid 原始报错。

## 注意事项

- `created_at` 返回东八区 ISO 时间。
- 当前去重逻辑主要在 C 前端完成，B 接口不会拒绝重复概念。
- 生成是异步线程，`generate` 接口返回 `202` 只表示任务已启动。
- 图片可能失败，C 端应允许单项缺失，不影响文案展示。
- Mindmap 由服务端固定模板生成，C 端使用 Mermaid 渲染；如果客户端渲染异常，C 端必须隐藏错误图表，不显示 Mermaid 原始报错。
- `lesson_ready` 是组件完成信号，但文本应以 `markdown_delta` 优先实时展示。
