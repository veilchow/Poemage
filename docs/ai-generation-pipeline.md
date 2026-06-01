# B 端 AI 处理与生成管线文档

更新时间：2026-05-28

本文档整理当前 Flask B 端所有直接调用 StepFun/OpenAI-compatible API 的功能，包括入口、请求流转、模型参数、prompt 结构、后续可优化点。当前代码主要分布在：

- `app/aiapi/main.py`：通用 AI 文本流、Markdown 流、图片生成工具接口。
- `app/classroom/main.py`：A-B-C 课堂联动中的教学文案、文案修订、课堂图片、Mindmap 生成。

## 1. 全局 AI 配置

配置来源在 `app/aiapi/main.py`：

```python
STEPFUN_KEY = os.getenv("STEPFUN_KEY", LOCAL_STEPFUN_KEY)
STEPFUN_API_BASE = os.getenv("STEPFUN_API_BASE", "https://api.stepfun.com/v1")
STEPFUN_MODEL = os.getenv("STEPFUN_IMAGE_MODEL", "step-1x-medium")
STEPFUN_CHAT_MODEL = os.getenv("STEPFUN_CHAT_MODEL", "step-2-mini")
```

课堂图片相关默认配置在 `app/classroom/main.py`：

```python
CLASSROOM_IMAGE_MODEL = os.getenv('CLASSROOM_IMAGE_MODEL', 'step-image-edit-2')
CLASSROOM_IMAGE_SIZE = os.getenv('CLASSROOM_IMAGE_SIZE', '1024x1024')
CLASSROOM_IMAGE_STEPS = int(os.getenv('CLASSROOM_IMAGE_STEPS', '4'))
CLASSROOM_IMAGE_COUNT = int(os.getenv('CLASSROOM_IMAGE_COUNT', '1'))
CLASSROOM_IMAGE_TIMEOUT = float(os.getenv('CLASSROOM_IMAGE_TIMEOUT', '35'))
```

当前生产实测 `step-image-edit-2` 支持 `1024x1024`，不支持 `768x768`。

## 2. 通用文本接口

### 2.1 `/api/gpt`

代码位置：`app/aiapi/main.py::direct_response`

调用方式：

```http
GET /api/gpt?data={...}
```

`data` 是 JSON 字符串，要求包含：

```json
{
  "messages": [
    {"role": "user", "content": "用户问题"}
  ]
}
```

处理流程：

1. 解析 query 参数 `data`。
2. 取 `python_obj['messages']`。
3. 调用 StepFun chat completion。
4. 直接返回 `response.choices[0].message.content`。

模型：

```python
model="step-2-mini"
```

prompt 管线：

- 没有额外 system prompt。
- 完全透传调用方传入的 `messages`。

适用性：

- 这是一个轻量直接问答接口。
- 不负责 Markdown 结构优化。
- 不做输出后处理。

### 2.2 `/api/stream`

代码位置：`app/aiapi/main.py::stream_response`

调用方式：

```http
GET /api/stream?data={...}
```

`data.messages` 结构同 `/api/gpt`。

处理流程：

1. `parse_messages_arg()` 从 query 参数解析 `messages`。
2. 调用 StepFun chat completion，`stream=True`。
3. 把模型增量内容按 SSE 格式输出：

```text
data: <delta content>

```

模型：

```python
model=STEPFUN_CHAT_MODEL
```

默认是 `step-2-mini`。

prompt 管线：

- 没有额外 system prompt。
- 透传调用方传入的 `messages`。

注意：

- 这是早期流式接口，SSE data 直接放字符串，不是结构化 JSON。
- 使用全局 `stop_stream`，多用户并发时存在互相影响风险。

### 2.3 `/api/stream/markdown`

代码位置：`app/aiapi/main.py::stream_markdown_response`

调用方式：

```http
GET /api/stream/markdown?data={...}
```

处理流程：

1. `parse_messages_arg()` 解析 `messages`。
2. 使用 `markdown_messages(messages)` 包一层 system prompt。
3. 调用 StepFun chat completion，`stream=True`。
4. 输出结构化 SSE JSON：

```json
{"type": "start"}
{"type": "delta", "content": "..."}
{"type": "done"}
```

模型：

```python
model=STEPFUN_CHAT_MODEL
```

Markdown system prompt：

```text
请使用结构清晰的 Markdown 输出。保留段落、标题、列表、代码块和换行；不要把所有内容压缩成一行。
```

适用性：

- 用于解决普通 `/stream` 输出被前端拼成一行、Markdown 结构不稳定的问题。
- 后端只约束模型输出，不做 Markdown AST 修复。

## 3. 通用图片接口

### 3.1 `/api/generate-image`

代码位置：`app/aiapi/main.py::api_generate_image`

调用方式：

```http
POST /api/generate-image
Content-Type: application/json
```

请求体：

```json
{
  "prompt": "图片提示词"
}
```

处理流程：

1. 从 JSON 中读取 `prompt`。
2. 调用 `generate_image(prompt)`。
3. 返回 base64 图片数组。

底层函数：

```python
def generate_image(prompt, model=STEPFUN_MODEL, n=1, response_format='b64_json',
                   size='256x256', steps=20, seed=11879934, cfg_scale=7.5, timeout=20.0):
```

实际请求：

```python
client.images.generate(
    model=model,
    prompt=prompt,
    response_format=response_format,
    extra_body={
        "cfg_scale": cfg_scale,
        "seed": seed,
        "steps": steps
    },
    size=size,
    n=n,
)
```

注意：

- `seed` 参数会被函数内部随机值覆盖。
- 这个接口默认仍使用 `STEPFUN_IMAGE_MODEL`，默认值是 `step-1x-medium`。
- 课堂教师端不直接使用 `/api/generate-image`，而是通过课堂管线调用同一个 `generate_image()` 函数。

## 4. A-B-C 课堂 AI 管线

课堂链路由 A 创建课堂概念，C 选择扩展项后触发 B 生成教学组件。

### 4.1 A 创建课堂概念

代码位置：`app/classroom/main.py::create_classroom_event`

入口：

```http
POST /api/classroom/events
```

当前语义：

```json
{
  "user_id": 205,
  "context": "课堂上下文/游戏背景",
  "type": "地点",
  "description": "洛阳"
}
```

归一化函数：`normalize_classroom_payload(data)`

规则：

- `type` 通过 `TYPE_ALIASES` 归一为内部类型。
- `context` 保持为课堂上下文。
- `description` 是具体内容，会被解析为 `name`。
- 如果 `description` 是 JSON 字符串、数组或对象，会用 `summarize_payload_value()` 抽取简短标题。

入库：

```python
event_type='concept'
source='A'
concept_type=data['concept_type']
name=data['name']
content=data['context']
payload=data
```

默认不生成 AI。除非 A 显式传 `generate_ai=true`，否则由 C 端二次确认扩展项后生成。

### 4.2 C 触发教学组件生成

代码位置：`app/classroom/main.py::generate_classroom_lesson`

入口：

```http
POST /api/classroom/events/{event_id}/generate
```

请求体核心字段：

```json
{
  "component_id": "2507-person_intro-...",
  "context": "课堂上下文/背景",
  "type": "person",
  "description": "李白",
  "extension": {
    "id": "person_intro",
    "title": "诗人介绍",
    "description": "这位诗人的基本信息和生平概览。",
    "instruction": "讲清诗人的气质、人生处境、作品风格，不写履历表。"
  },
  "generate_image": true
}
```

处理流程：

1. 查询当前教师账号下的 `concept` 事件。
2. 合并原始 `event_payload` 和 C 端请求覆盖字段。
3. 补齐：
   - `concept_event_id`
   - `component_id`
   - `generate_image`
4. 调用 `normalize_classroom_payload()`。
5. 启动后台线程 `generate_teaching_content(app, session_id, data)`。
6. 立即返回 `202`。

## 5. 课堂教学文案生成

代码位置：

- `build_teaching_prompt(data)`
- `generate_teaching_content(app, session_id, data)`

模型：

```python
model=STEPFUN_CHAT_MODEL
stream=True
messages=markdown_messages([{'role': 'user', 'content': prompt}])
```

也就是说最终消息结构是：

```json
[
  {
    "role": "system",
    "content": "请使用结构清晰的 Markdown 输出。保留段落、标题、列表、代码块和换行；不要把所有内容压缩成一行。"
  },
  {
    "role": "user",
    "content": "<build_teaching_prompt 生成的大 prompt>"
  }
]
```

### 5.1 输入信息优先级

`build_teaching_prompt()` 中声明：

```text
优先级规则：A.context 和 A.description 是最高优先级，必须优先遵循。下面的知识库是重要参考材料，权重低于 A.context 和 A.description，但高于模型常识；当知识库与当前主题有关时，必须吸收其中的经历、地点、诗体或作品信息来丰富讲解。
```

当前输入来源：

1. A/C 请求字段：
   - `A.context（课堂上下文）`
   - `A.description（具体内容）`
   - `type`
   - `extension.title`
   - `extension.instruction`
2. 内置知识库：
   - `app/classroom/knowledge_base.md`
   - 读取后截取前 `2600` 字。
3. 类型侧重点：
   - `TEACHING_PROMPT_BY_TYPE`
4. 文学锚点：
   - `build_literary_hint(name, classroom_context)`

### 5.2 类型侧重点

代码位置：`TEACHING_PROMPT_BY_TYPE`

当前定义：

```text
person: 面向学生讲清诗人的人生经历、性格气质、代表作品和作品中的情感力量。
poem: 面向学生讲清诗词画面、关键意象、情感变化和一句值得记住的赏析结论。
location: 面向学生讲清地点的画面感、历史文化、诗词象征和它为什么会触动诗人。
event: 面向学生讲清事件背景、人物处境、情绪压力和它如何进入诗词表达。
culture: 面向学生讲清文化常识如何帮助理解诗词中的礼俗、空间、人物关系和情绪。
history: 面向学生讲清历史背景如何改变人物处境，并转化为诗词中的家国、漂泊或兴亡之感。
technique: 面向学生讲清表现技法如何组织画面、推进情绪、形成表达效果。
theme: 面向学生讲清主题如何从画面、处境和情绪中自然生长出来。
```

### 5.3 文学锚点

代码位置：`build_literary_hint(name, context)`

当前硬编码规则：

```text
洛阳/洛城：
可选文学方向：秋风与家书、故人与问候、夜笛与乡愁、东都盛衰。这些只是可选语境，不要强行绑定某一首诗。洛阳不应写成旅游景点或单纯宫殿街景。

大漠/沙漠/边塞/塞外/黄沙/戈壁：
可用文学锚点：王维“大漠孤烟直，长河落日圆”。大漠适合讲开阔、孤烟、落日、边塞行旅、家国与孤独，不要写冒险体验。

李白：
可选文学方向：李白的豪放、远游、月亮、酒、想象力、入世不得志。重点讲他如何把个人情感写得开阔飞扬，不要写履历表。

默认：
没有明确作品时，只讲可靠的诗词语境，不要编造诗句或典故。
```

### 5.4 教学文案主 prompt 结构

生成角色：

```text
你是中学语文课堂的大屏知识素材作者。请基于游戏端学生刚刚关注的元素，生成可直接投屏、可直接用于教师讲解的 Markdown 知识素材。老师需要的是“知识点供给”和“科普素材库”，不是教学方法示范，也不是只教学生怎么思考。
```

变量区：

```text
- 元素类型：{concept_type}
- A.context（课堂上下文）：{classroom_context}
- A.description（具体内容）：{name}
- 教师选择的扩展方向：{extension_title}
- 扩展方向说明：{extension_instruction}
- 命中的知识库片段（优先使用）：{knowledge_excerpt}
- 参考知识库：{knowledge_base[:2600]}
- 学生讲解侧重点：{teaching_focus}
- 文学锚点：{literary_hint}
```

知识库召回规则：

```text
- 先按 A.description / A.context / 扩展标题 / 扩展说明在 `knowledge_base.md` 中查找命中片段。
- 命中片段优先级高于通用知识库截断内容，避免具体诗作被 2600 字截断漏掉。
- 诗词相关请求如果命中原文，必须优先展示原文；如果没有命中完整原文，不允许凭模型记忆补全。
```

知识素材要求：

```text
- 信息密度要高，优先给时间、地点、人物、作品、关键词、史实、概念定义、作品关联、命运变化等硬知识点。
- 每个核心知识点都要包含“事实 + 为什么重要”，不能只写感受或空泛判断。
- 事实必须严谨；不确定的内容必须用“可能关联”“常见说法”“需结合教材版本核对”等保守表述，不得当成定论。
- 不得为了凑主题强行关联作品、人物或地点；关系不直接时，必须说明是“间接关联”或“不宜作为本主题核心材料”。
- 如果主题涉及事件，必须尽量给出时间跨度、关键人物、转折点和影响。
- 如果主题涉及人物，必须尽量给出身份、时代、生平节点、代表作品、作品气质和相关事件。
- 如果主题涉及地点，必须尽量给出地理/历史身份、相关诗人、相关作品、常见诗词意象和文化含义。
- 如果主题涉及诗词，必须尽量给出作者、背景、关键意象、名句、情感转折和易错理解。
- 不确定的生卒年、数字或作品归属不要编造；可以改写为“常见关联”“可作为比较材料”。
```

诗词原文强制规则：

```text
- 如果“命中的知识库片段”中包含当前诗词原文，必须在正文中完整展示原诗，不得只写作者、时间和诗体。
- 原诗按标题、作者、诗句分行展示；诗句保持换行，不要压成一段。
- 如果知识库没有命中完整原文，必须明确写“知识库未提供完整原文”，不要凭模型记忆补全诗句。
- 原文之后再写简要赏析和知识点，至少覆盖画面、意象、情感变化和一个易错理解。
```

类型修正：

```text
- 地点类不要写成旅游介绍，要落到相关人物、作品、历史记忆、诗词意象和文化象征。
- 人物类不要写空泛履历，要给出关键经历、代表作品、作品风格和时代处境。
- 事件类不要只写百科定义，要列出卷入人物、关键时间线、事件后果和文学影响。
- 诗词类不要复述常识，要抓住作者背景、意象关系、名句解释和易错点。
```

质量要求：

```text
- 每一句都要能直接投屏给学生看，像知识点速查材料，不像后台说明或备课建议。
- 少写“可以帮助学生理解”“引导学生思考”等教法话术，多给可讲的事实、例子和关联。
- 每个列表项都写完整知识点，不能留下任务说明式文字。
- 如果没有明确作品，不要乱编具体诗句；可以用“常见边塞诗/思乡诗/怀古诗”概括。
- 重点提供老师可直接讲的知识素材，兼顾诗词意味，不要只写情绪感受。
```

扩展方向服从规则：

```text
- 如果扩展方向是“相关诗人”，正文必须点出与该地点或主题真实相关的诗人，并说明他们和这个地点/主题的具体关系、相关作品、处境或作品气质；不要把正文写成地点介绍。
- 如果扩展方向是“地点历史”，正文必须讲历史沿革、文化意义和它如何变成诗词里的情绪背景；不要只写风景。
- 如果扩展方向是“诗人的知名作品”，正文必须围绕代表作品、画面和情绪展开；不要只写生平。
- 如果扩展方向是“诗人当前的境遇”，正文必须讲时代压力、人生处境和作品气质；不要写履历表。
- 如果扩展方向是“创作背景”，正文必须解释作品为何在这样的处境中被写出；不要堆百科。
- 如果扩展方向是“意象关系”，正文必须讲意象之间如何互相牵引并推动情绪。
- 如果扩展方向是自定义内容，必须严格按自定义说明组织全文。
```

相关诗人专项规则：

```text
- 必须优先写与主题有真实、可核查关系的诗人；宁可少写，也不能为了凑数量硬编关联。
- 如果材料允许，扩充到 5-6 位诗人，尽量覆盖盛唐到中晚唐；每位诗人都必须写清“与主题的具体关系”。
- 每位诗人使用“【诗人名】”作为小标题，下面用 2-3 条写：与主题关系、代表作品/名句、课堂可用知识点。
- 不能只写诗人风格，必须说明他为什么和当前地点、事件、作品或主题有关。
```

洛阳相关诗人的专项事实约束：

```text
- 可优先考虑：杜甫、李白、王昌龄、白居易、刘禹锡、李贺；如写韩愈、司马光等，必须说明可靠关系。
- 杜甫：可写青年时期在洛阳活动、与李白在洛阳相遇、自称“洛阳布衣”等关联。
- 李白：可写《春夜洛城闻笛》及洛阳闻笛引发乡思，也可写与杜甫洛阳相遇。
- 王昌龄：可写《芙蓉楼送辛渐》中“洛阳亲友如相问”，注意诗作地点不是洛阳，而是托友人向洛阳亲友传话。
- 白居易：可写晚年居洛阳、太子宾客分司东都、葬于洛阳龙门香山；严禁写“白居易曾任洛阳刺史”。
- 刘禹锡：可写晚年与白居易同居洛阳、唱和频繁；涉及《陋室铭》时要注明地点归属有争议，不要强行说成洛阳作品。
- 李贺：可写出生于洛阳福昌县一带，诗风与中唐兴衰感有关。
- 严禁把《琵琶行》写成洛阳背景；《琵琶行》写于江州，背景是浔阳江头。
- 不要说《秋兴八首》“多次提到洛阳”；可写杜甫晚年组诗主要关联夔州、长安与故国之思。
```

强制 Markdown 结构：

```markdown
## {name}：{extension_title}

### 基础信息卡
- 用 4-6 条列出最关键的硬信息，如时间、地点、人物、身份、作品、关键词、历史地位；没有把握的信息不要编造。

### 诗词原文
- 如果知识库命中原文，先完整列出标题、作者和诗句，保持原诗换行。
- 原文后用 2-3 条写简要赏析：画面、意象、情绪或一句关键知识点。
- 如果知识库没有完整原文，只能说明“知识库未提供完整原文”，不能编造诗句。

### {extension_title}知识点
- 用 6-10 条展开本次扩展方向的核心知识点。每条都必须是“事实 + 解释”，并且必须扣住扩展方向。
- 如果扩展方向是人物、作品、历史、意象或地点关联，必须列出具体对象，而不是只写抽象意义。

### 关联素材速查
- 使用“【标题】\n关键信息：...\n课堂可用：...”的标题+正文格式，至少 4 组；不要使用 Markdown 表格。
- 每组都要写具体人物、作品、事件、意象或概念，并明确它与当前主题的真实关系。

### 易错点与记忆法
- **易错点**：列出 2-3 个学生容易混淆或老师需要提醒的点。
- **记忆法**：写 1 句短口诀或速记句，帮助记住本次知识点。

### 收束句
- 写成 2-3 句完整的课堂收束段，约 80-140 个汉字。
- 必须回扣本次扩展方向，点明这个知识点在诗词理解、历史背景或人物关系中的价值；不要只写一句口号。
```

篇幅要求：

```text
总长度约 980-1450 个汉字。输出后自检：硬知识点数量要足，事实关系要经得起核查，不使用表格，且每一段都必须扣住扩展方向。
```

### 5.5 流式落库与 SSE 输出

`generate_teaching_content()` 不直接向 HTTP 响应写流，而是把事件写入 `classroom_event` 表，由 C 端 SSE 连接读取。

事件顺序：

1. `lesson_component_start`
2. `ai_start`
3. `markdown_delta`，每约 `0.25s` 刷一次
4. `markdown_done`
5. 可选 `markdown_done` revision 版本
6. `mermaid_start`
7. `mermaid_done` / `mermaid_error`
8. `lesson_ready`
9. 后台图片线程：
   - `image_start`
   - `image_done` / `image_error`

## 6. 文案质量二次修订

代码位置：

- `teaching_content_needs_revision(content)`
- `build_revision_prompt(data, content)`

触发条件：

如果原文包含以下模板化或不合适内容之一，则触发修订：

```text
解释它如何
解释它带出
解释它和
角度一 / 角度二 / 角度三
关键词
情感投入
仿佛穿越
古色古香
熙熙攘攘
叫卖声
红墙碧瓦
旅游
想象一下
你是否
如果你是
市井喧嚣
宫阙
```

另外，如果 `### 收束句` 后的文本少于约 `60` 个字符或超过约 `180` 个字符，也会触发修订。目标是 2-3 句、约 80-140 个汉字的完整课堂收束段。

诗词相关内容还会追加结构检查：

- 缺少 `### 诗词原文` 栏目会触发修订。
- 如果知识库命中原诗，但正文没有出现原诗标题或诗句，会触发修订。

修订调用：

```python
revision_response = client.chat.completions.create(
    model=STEPFUN_CHAT_MODEL,
    messages=markdown_messages([
        {'role': 'user', 'content': build_revision_prompt(data, teaching_content)},
    ]),
)
```

修订 prompt：

```text
请重写下面这份学生大屏知识素材稿，保持同样 Markdown 栏目，但显著提高知识密度和课堂可用性。

重写要求：
1. 面向学生和授课老师，输出可直接使用的知识素材，不要写教学方法建议。
2. 必须增加硬知识点：时间、地点、人物、作品、史实、意象、概念定义或作品关联，按主题选择。
3. 如果原稿偏空泛赏析，要改成知识点速查材料；如果扩展方向要求人物、作品或历史，必须列出具体对象。
4. 必须核实事实关系；不要为了凑主题强行关联人物、作品或地点。不要使用 Markdown 表格，改用“【标题】关键信息/课堂可用”的分条格式。
5. 如出现“洛阳刺史”“《琵琶行》写于洛阳”“《琵琶行》中以洛阳为背景”等错误，必须删除并改正。
6. 收束句必须改成 2-3 句完整课堂收束段，约 80-140 个汉字，回扣扩展方向，不要只写一句口号。
7. 不要新增 Markdown 栏目，但必须补足关联素材、易错点和记忆法。
8. 这是诗词相关内容：必须保留或补齐“### 诗词原文”栏目；如果命中的知识库片段提供了原诗，必须完整展示标题、作者和诗句，保持诗句换行；不能只写基础信息卡。

主题：{name}

文学锚点：{literary_hint}

命中的知识库片段：
{knowledge_excerpt}

原稿：
{content}
```

注意：

- 修订不是流式的。
- 修订成功后会再次写入 `markdown_done`，payload 带 `revision=True`。
- 当前 C 端以最后收到的 `markdown_done` 覆盖内容。

## 7. 课堂图片生成

代码位置：

- `build_image_prompt(data, teaching_content)`
- `build_safe_symbolic_image_prompt(data, teaching_content)`
- `generate_classroom_image(app, session_id, data, event_context, teaching_content)`

执行时机：

- 文案和 Mindmap 完成后先写 `lesson_ready`。
- 如果 `generate_image=true`，再启动独立后台线程生成图片。
- 图片成功后写 `image_done`，C 端再更新图片区域。

模型配置：

```python
model=data.get('image_model', CLASSROOM_IMAGE_MODEL)       # 默认 step-image-edit-2
size=data.get('image_size', CLASSROOM_IMAGE_SIZE)          # 默认 1024x1024
steps=int(data.get('image_steps', CLASSROOM_IMAGE_STEPS))  # 默认 4
cfg_scale=float(data.get('image_cfg_scale', 1.0))
timeout=float(data.get('image_timeout', CLASSROOM_IMAGE_TIMEOUT))  # 默认 35
n=max(1, min(int(data.get('image_count', CLASSROOM_IMAGE_COUNT)), 1))
```

### 7.1 主图片 prompt

非人物类型使用 `build_image_prompt()`：

```text
满幅古典国风场景插画，淡彩水墨、水彩晕染、细腻线稿。
不是书页，不是海报，不要白底，不要空白边距，画面必须饱满。
不要书本、卷轴、纸张、碑刻、牌匾、印章、题字区域、标签区域。
{scene}
No written symbols anywhere.
NO TEXT, no letters, no Chinese characters, no calligraphy, no seal, no signboard, no plaque, no book, no scroll, no watermark.
画面中不得出现任何文字、汉字、字母、书法、印章、牌匾、题款、签名、水印。
主题:{concept_type}-{name}。上下文:{context[:80]}。摘要:{teaching_content[:80]}
```

最终截断到 `500` 字符。

### 7.2 场景推断

代码位置：`infer_visual_scene(name, context)`

当前规则：

```text
大漠/沙漠/边塞/塞外/黄沙/戈壁/玉门关/阳关：
满幅边塞大漠场景：金色沙丘铺满前景，戈壁与驼队穿过中景，远处关隘烽燧和落日，画面被沙丘、天空、烽燧填满，绝对不要河流、石桥、江南水乡、白墙黑瓦。

洛阳/长安/汴梁/古都/城：
北方古都场景：厚重城楼、宽阔街道、远山、少量柳树，历史感强，不要江南水乡、白墙黑瓦、小桥流水。

李白/杜甫/诗人：
古代诗人意境场景：月夜山水、酒杯、远行道路、江天云影，可以有远处背影或剪影，不画正面肖像，不画真实人物特写，突出孤高、自由与诗意。

默认：
古典语文场景：山川、城郭、人物剪影与诗意空间，依据主题选择准确景物，不要现代元素。
```

注意：当前 `concept_type == 'person'` 时会直接走安全通用 prompt，不使用人物场景规则。

### 7.3 安全通用图片 prompt

人物类型和主图失败兜底都会使用 `build_safe_symbolic_image_prompt()`：

```text
满幅古典国风山水意境插画，淡彩水墨、水彩晕染、细腻线稿。
月夜、远山、江水、空亭、长路、云影，画面饱满，无人物，无肖像，无酒杯。
不要书本、卷轴、纸张、碑刻、牌匾、印章、题字区域、标签区域。
No people portrait. No written symbols anywhere.
NO TEXT, no letters, no Chinese characters, no calligraphy, no seal, no signboard, no plaque, no book, no scroll, no watermark.
主题:古典诗意山水。
```

最终截断到 `500` 字符。

### 7.4 图片失败处理

当前逻辑：

1. 先用 `build_image_prompt()` 生成。
2. 如果抛异常，再用 `build_safe_symbolic_image_prompt()` 兜底重试。
3. 如果仍失败，写入 `image_error`。

常见失败：

- `size_invalid`：图片尺寸不被模型支持。当前默认已改为 `1024x1024`。
- API 超时或网络错误：会写 `image_error`，C 端显示失败。

## 8. Mindmap 生成

代码位置：

- `build_deterministic_mindmap(data)`
- `validate_mermaid_code(code, chart_type='mindmap')`
- `generate_mermaid_code(data, chart_type='mindmap')`

当前 Mindmap 不调用 AI。它是 B 端确定性模板生成的 Mermaid mindmap。

生成结构：

```text
mindmap
  root(({name}))
    {extension_title}
    {type_node_1}
    {type_node_2}
    ...
```

节点来源：

```text
location: 画面入口、地理位置、历史回声、诗词情绪、课堂追问
person: 人生经历、性格气质、代表作品、情感力量、课堂追问
event: 事件背景、人物处境、情绪压力、诗词表达、课堂追问
poem: 画面意象、关键诗句、情感变化、表达意味、课堂追问
culture: 文化常识、礼俗空间、人物关系、诗词意味、课堂追问
history: 时代背景、人物处境、家国情怀、兴亡之感、课堂追问
technique: 表现技法、画面组织、情绪推进、表达效果、课堂追问
theme: 主题入口、画面支撑、处境冲突、情绪收束、课堂追问
默认: 画面入口、文本线索、人物处境、诗词意味、课堂追问
```

安全处理：

- `sanitize_mermaid_label()` 只保留中文、英文、数字。
- 根节点最多 `10` 字。
- 扩展标题最多 `8` 字。
- 节点最多 `10` 字。
- `validate_mermaid_code()` 禁止：
  - `<script`
  - `</`
  - `%%{`
  - `click`
  - `href`
  - `theme`
  - `shape`
  - `classDef`
  - `class`
  - 过长 label
  - `[]<>":`

说明：

- Mindmap 当前稳定性优先，不走模型生成。
- C 端用 Mermaid 10 渲染，若客户端渲染异常则隐藏，不显示错误 SVG。

## 9. 当前 AI 功能一览

| 功能 | 入口/触发点 | 是否调用 AI | 模型 | Prompt 来源 |
| --- | --- | --- | --- | --- |
| 普通问答 | `GET /api/gpt` | 是 | `step-2-mini` | 调用方传入 `messages` |
| 原始流式文本 | `GET /api/stream` | 是 | `STEPFUN_CHAT_MODEL` | 调用方传入 `messages` |
| Markdown 流式文本 | `GET /api/stream/markdown` | 是 | `STEPFUN_CHAT_MODEL` | `markdown_messages()` + 调用方 `messages` |
| 通用图片 | `POST /api/generate-image` | 是 | `STEPFUN_IMAGE_MODEL` | 调用方传入 `prompt` |
| 课堂文案 | `POST /api/classroom/events/{id}/generate` | 是 | `STEPFUN_CHAT_MODEL` | `build_teaching_prompt()` + `markdown_messages()` |
| 课堂文案修订 | 自动触发 | 是 | `STEPFUN_CHAT_MODEL` | `build_revision_prompt()` + `markdown_messages()` |
| 课堂图片 | 自动触发 | 是 | `CLASSROOM_IMAGE_MODEL` | `build_image_prompt()` / `build_safe_symbolic_image_prompt()` |
| 课堂 Mindmap | 自动触发 | 否 | 无 | B 端固定模板 |

## 10. 后续 prompt 管线优化建议

### 10.1 把 prompt 从代码中拆出来

当前 prompt 都写在 Python 函数里，后续优化成本高。建议拆成：

```text
app/classroom/prompts/
  teaching/base.md
  teaching/revision.md
  image/base.md
  image/safe_symbolic.md
  literary_hints.yml
  type_focus.yml
```

这样可以不改 Python 逻辑，只改 prompt 文件。

### 10.2 引入结构化 prompt 组装器

建议把当前 `build_teaching_prompt(data)` 拆成几个明确阶段：

1. `normalize_input`
2. `select_type_focus`
3. `retrieve_knowledge`
4. `select_literary_hint`
5. `compose_prompt`
6. `validate_output`
7. `revise_if_needed`

这样更容易调权重，也更容易做 A/B 测试。

### 10.3 知识库从固定截断改为检索

当前：

```python
knowledge_base[:2600]
```

问题：

- 主题不相关时也会塞入 prompt。
- 主题相关内容可能在 2600 字之后。

建议：

- 按标题或段落切块。
- 根据 `description/name/context/type` 做关键词召回。
- 最终只拼接最相关的 3-5 段。

### 10.4 输出质量检查从关键词升级为结构校验

当前 `teaching_content_needs_revision()` 主要靠关键词和收束句长度。后续可以增加：

- 必须包含所有 Markdown 标题。
- 每个栏目非空。
- `画面入口` 至少 2 条。
- `课堂追问` 至少 2 个问题。
- 禁止“想象一下”等模板词。
- 收束句必须是 2-3 句完整课堂收束段。

### 10.5 图片 prompt 需要按类型维护

当前人物类型全部走安全通用图，导致画面稳定但主题相关性弱。建议新增：

```text
person_image_prompt
location_image_prompt
event_image_prompt
poem_image_prompt
culture_image_prompt
```

人物图仍可避免正面肖像，但可以保留更强主题符号，例如：

- 李白：月夜、远山、酒盏、江天、远行背影。
- 杜甫：秋风、草堂、孤舟、战乱远景。

### 10.6 课堂文案避免“课堂后台话术”

当前主 prompt 已要求“直接展示给学生”，但模型仍偶尔会输出备课式表达。建议把禁止项做成显式负例：

```text
不要写：
- “这个概念可以帮助学生理解……”
- “课堂定位是……”
- “教学目标是……”
- “解释它如何……”
```

并在修订 prompt 中继续强化。

### 10.7 事件日志中保留 prompt 版本

当前 `ai_start` 会保存完整 prompt，但没有 prompt 版本。建议新增：

```json
{
  "prompt_version": "teaching-v1.3",
  "knowledge_base_version": "...",
  "image_prompt_version": "image-v1.1"
}
```

后续定位质量问题会更快。

## 11. 关键文件索引

```text
app/aiapi/main.py
  create_stepfun_client()
  markdown_messages()
  generate_image()
  /gpt
  /stream
  /stream/markdown
  /generate-image

app/classroom/main.py
  normalize_classroom_payload()
  load_knowledge_base()
  build_literary_hint()
  build_teaching_prompt()
  teaching_content_needs_revision()
  build_revision_prompt()
  infer_visual_scene()
  build_image_prompt()
  build_safe_symbolic_image_prompt()
  build_deterministic_mindmap()
  generate_classroom_image()
  generate_teaching_content()
  create_classroom_event()
  generate_classroom_lesson()

app/classroom/knowledge_base.md
  课堂内置知识库
```
