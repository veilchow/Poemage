from app.aiapi import aiapi
from openai import OpenAI
from flask import request, json, jsonify, redirect, session, make_response, Response, stream_with_context
import threading
import random
import os

# 测试路由
@aiapi.route('/hello', methods=['POST', 'GET'])
def hello():
    return jsonify({"hello": "123"}), 200


generation_thread = None
generation_event = threading.Event()
should_stop_generation = False

stream_thread = None
stop_stream = False
def generate_gpt_response(data):
    global should_stop_generation

    # client = OpenAI(api_key=os.getenv("DEEPSEEK_API_KEY"), base_url="https://your-domain.example")
    client = OpenAI(api_key=STEPFUN_KEY, base_url=STEPFUN_API_BASE)

    python_obj = json.loads(data)
    print(python_obj['messages'])

    # 在生成前检查是否要求停止
    if should_stop_generation:
        print("Generation was stopped before starting.")
        return "Generation was stopped."

    # 请求生成内容
    response = client.chat.completions.create(
        # model="deepseek-chat",
        model="step-2-16k",

        messages=python_obj['messages'],
    )

    # 生成过程中检查是否被要求停止
    if should_stop_generation:
        print("Generation was interrupted.")
        return "Generation was interrupted."

    return response.choices[0].message.content


@aiapi.route('/gpt', methods=['GET'])
def direct_response():
    data = request.args.get('data')
    print(data)
    python_obj = json.loads(data)
    print(python_obj['messages'])
    client = OpenAI(api_key=STEPFUN_KEY, base_url=STEPFUN_API_BASE)
    response = client.chat.completions.create(
        model="step-2-mini",
        messages=python_obj['messages'],
    )
    return response.choices[0].message.content


# @app.route('/api/gpt', methods=['GET'])
# def direct_response():
#     global generation_thread, should_stop_generation
#
#     data = request.args.get('data')
#     print(data)
#
#     # 设置停止标志
#     should_stop_generation = False
#     generation_event.clear()
#
#     # 创建一个新线程执行生成任务
#     generation_thread = threading.Thread(target=generate_gpt_response, args=(data,))
#     generation_thread.start()
#
#     return "Generation started, you can stop it using /api/gpt/stop"


@aiapi.route('/gpt/stop', methods=['GET'])
def stop_generation():
    global should_stop_generation

    # 设置停止标志，告诉线程停止生成
    should_stop_generation = True

    # 等待生成线程结束
    if generation_thread:
        generation_thread.join()

    return "Generation stopped successfully."


try:
    from app.local_config import STEPFUN_KEY as LOCAL_STEPFUN_KEY
except ImportError:
    LOCAL_STEPFUN_KEY = None

STEPFUN_KEY = os.getenv("STEPFUN_KEY", LOCAL_STEPFUN_KEY)
STEPFUN_API_BASE = os.getenv("STEPFUN_API_BASE", "https://api.stepfun.com/v1")
STEPFUN_MODEL = os.getenv("STEPFUN_IMAGE_MODEL", "step-1x-medium")
STEPFUN_CHAT_MODEL = os.getenv("STEPFUN_CHAT_MODEL", "step-2-mini")


def create_stepfun_client():
    return OpenAI(api_key=STEPFUN_KEY, base_url=STEPFUN_API_BASE)


def parse_messages_arg():
    data = request.args.get('data')
    if not data:
        return None, jsonify({"error": "Missing data parameter"}), 400

    try:
        python_obj = json.loads(data)
    except ValueError:
        return None, jsonify({"error": "Invalid JSON in data parameter"}), 400

    messages = python_obj.get('messages')
    if not isinstance(messages, list):
        return None, jsonify({"error": "data.messages must be a list"}), 400

    return messages, None, None


def markdown_messages(messages):
    return [
        {
            "role": "system",
            "content": (
                "请使用结构清晰的 Markdown 输出。保留段落、标题、列表、代码块和换行；"
                "不要把所有内容压缩成一行。"
            ),
        },
        *messages,
    ]


def sse_json(event):
    return f"data: {json.dumps(event, ensure_ascii=False)}\n\n"


# 图片生成函数
def generate_image(prompt, model=STEPFUN_MODEL, n=1, response_format='b64_json',
                   size='256x256', steps=20, seed=11879934, cfg_scale=7.5, timeout=20.0):
    seed = random.randint(0, 2 ** 31 - 1)  # 生成一个足够大的随机整数
    client = OpenAI(
        api_key=STEPFUN_KEY,
        base_url=STEPFUN_API_BASE,
        timeout=timeout,
    )
    image = client.images.generate(
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
    return image.data

# Flask 路由
@aiapi.route('/generate-image', methods=['POST'])
def api_generate_image():
    try:
        data = request.json
        prompt = data.get('prompt', '')

        if not prompt:
            return jsonify({"error": "Prompt is required"}), 400

        print(prompt)
        result = generate_image(prompt)

        print(result)
        urls = [img.b64_json for img in result if img.b64_json]

        return jsonify({"status": "success", "data": urls})

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500



# @app.route('/api/stream', methods=['GET'])
# def stream_response():
#     data = request.args.get('data')
#     #print(data)
#     python_obj = json.loads(data)
#     #print(python_obj['messages'])
#     client = OpenAI(api_key=os.getenv("DEEPSEEK_API_KEY"), base_url="https://your-domain.example")
#     response = client.chat.completions.create(
#         model="deepseek-chat",
#         messages=python_obj['messages'],
#         stream=True
#     )
#
#     def generate():
#         for chunk in response:
#             yield f"data: {chunk.choices[0].delta.content}\n\n"  # 按需修改输出结构
#      #       print(chunk.choices[0].delta.content)
#
#     return Response(stream_with_context(generate()), content_type='text/event-stream')

def stop_stream_generation():
    global stop_stream
    stop_stream = True


@aiapi.route('/stream', methods=['GET'])
def stream_response():
    global stop_stream
    stop_stream = False
    messages, error_response, status_code = parse_messages_arg()
    if error_response:
        return error_response, status_code

    client = create_stepfun_client()
    response = client.chat.completions.create(
        model=STEPFUN_CHAT_MODEL,
        messages=messages,
        stream=True
    )

    def generate():
        global stop_stream  # 使用 global 来修改全局变量
        for chunk in response:
            print(f"data: {chunk.choices[0].delta.content}\n\n")
            if stop_stream:  # 如果 stop_stream 被设置为 True，则终止流式输出
                print("Stream generation stopped.")
                yield ""
                break
            yield f"data: {chunk.choices[0].delta.content}\n\n"  # 输出数据流

    return Response(stream_with_context(generate()), content_type='text/event-stream')


@aiapi.route('/stream/markdown', methods=['GET'])
def stream_markdown_response():
    global stop_stream
    stop_stream = False
    messages, error_response, status_code = parse_messages_arg()
    if error_response:
        return error_response, status_code

    client = create_stepfun_client()
    response = client.chat.completions.create(
        model=STEPFUN_CHAT_MODEL,
        messages=markdown_messages(messages),
        stream=True
    )

    def generate():
        global stop_stream
        yield sse_json({"type": "start"})

        for chunk in response:
            if stop_stream:
                yield sse_json({"type": "stop"})
                break

            content = chunk.choices[0].delta.content
            if content:
                yield sse_json({"type": "delta", "content": content})
        else:
            yield sse_json({"type": "done"})

    return Response(stream_with_context(generate()), content_type='text/event-stream')


@aiapi.route('/stream/stop', methods=['GET'])
def stop_stream_route():
    stop_stream_generation()  # 设置停止标志
    return "Stream generation stopped successfully."
