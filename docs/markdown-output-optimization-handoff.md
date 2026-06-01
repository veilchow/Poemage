# Markdown 输出优化交接文档

## 背景

游戏前端 A 调用后端 B 的 `https://your-domain.example/api/stream` 时，AI 返回内容在前端表现为换行丢失、段落挤在一起，无法稳定渲染为结构化 Markdown。

排查后确认：原 `/api/stream` 是兼容旧前端的 SSE 风格流式接口，直接透传模型 token，没有额外约束模型输出 Markdown 结构，也没有结构化事件包装。为避免影响旧游戏链路，新增平行接口处理 Markdown 输出。

## 相关接口

### 旧接口

`GET /api/stream`

用途：保留原游戏侧调用方式。

特点：
- 使用 StepFun chat 模型，默认 `STEPFUN_CHAT_MODEL=step-2-mini`。
- `data` 查询参数中传入 JSON，要求包含 `messages` 数组。
- 响应为 `text/event-stream`。
- 直接输出 `data: <delta>`，保持原行为。

### 新接口

`GET /api/stream/markdown`

用途：给需要结构化 Markdown 的前端使用。

特点：
- 与旧接口并行，不影响 `/api/stream`。
- 请求参数仍复用 `data.messages`。
- 后端会在用户消息前追加 system prompt，要求模型保留标题、段落、列表、代码块和换行。
- 响应仍为 `text/event-stream`，但每条 `data:` 是 JSON 字符串。

事件格式：

```json
{"type":"start"}
{"type":"delta","content":"..."}
{"type":"done"}
{"type":"error","message":"..."}
```

## 请求示例

```bash
curl -N "https://your-domain.example/api/stream/markdown?data={\"messages\":[{\"role\":\"user\",\"content\":\"请用 Markdown 介绍洛阳\"}]}"
```

实际调用时应 URL encode `data` 参数。

## 前端接入建议

新前端应按 JSON SSE 处理：

```js
const source = new EventSource(`/api/stream/markdown?data=${encodeURIComponent(JSON.stringify({
  messages: [{ role: 'user', content: prompt }]
}))}`);

let markdown = '';

source.onmessage = (event) => {
  const payload = JSON.parse(event.data);
  if (payload.type === 'delta') {
    markdown += payload.content || '';
    renderMarkdown(markdown);
  }
  if (payload.type === 'done') {
    source.close();
  }
};
```

## 后端位置

主要文件：

- `app/aiapi/main.py`

主要函数：

- `markdown_messages(messages)`
- `stream_response()`
- `stream_markdown_response()`

## 配置项

- `STEPFUN_KEY`
- `STEPFUN_API_BASE`
- `STEPFUN_CHAT_MODEL`

生产环境真实配置在 `app/local_config.py` 或环境变量中，不应提交到 Git。

## 验收点

- 旧 `/api/stream` 可继续返回原始流式文本。
- 新 `/api/stream/markdown` 返回 JSON SSE。
- AI 输出包含 Markdown 标题、段落、列表和换行。
- 前端按 `delta` 拼接后可稳定渲染 Markdown。

## 已知限制

- Markdown 结构质量仍取决于模型输出，后端只通过 system prompt 约束，不做 Markdown AST 修复。
- 新接口仍是 SSE，不是 WebSocket。
- 如果前端使用 EventSource，需要按 `onmessage` 解析 JSON，而不是把 `event.data` 当纯文本直接拼接。
