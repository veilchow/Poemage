import base64
import json as jsonlib
import os
import re
import uuid
from pathlib import Path
import threading
import time

from flask import Response, current_app, jsonify, redirect, render_template, request, stream_with_context
from flask_login import current_user
from sqlalchemy.exc import OperationalError

from app.classroom import classroom
from app.libs.extensions import db
from app.models.classroom_event import ClassroomEvent

from app.classroom.core import (
    build_deterministic_mindmap,
    build_image_prompt,
    build_revision_prompt,
    build_teaching_prompt,
    teaching_content_needs_revision,
    validate_mermaid_code,
)


POLL_INTERVAL_SECONDS = 0.2
HEARTBEAT_SECONDS = 15
DEFAULT_SESSION_ID = 'default'
GENERATED_IMAGE_DIR = Path(__file__).resolve().parents[1] / 'static' / 'generated'
KNOWLEDGE_BASE_PATH = Path(__file__).resolve().with_name('knowledge_base.md')
CLASSROOM_IMAGE_MODEL = os.getenv('CLASSROOM_IMAGE_MODEL', 'step-image-edit-2')
CLASSROOM_IMAGE_SIZE = os.getenv('CLASSROOM_IMAGE_SIZE', '1024x1024')
CLASSROOM_IMAGE_STEPS = int(os.getenv('CLASSROOM_IMAGE_STEPS', '4'))
CLASSROOM_IMAGE_COUNT = int(os.getenv('CLASSROOM_IMAGE_COUNT', '1'))
CLASSROOM_IMAGE_TIMEOUT = float(os.getenv('CLASSROOM_IMAGE_TIMEOUT', '35'))
KNOWLEDGE_BASE_CACHE = {'mtime': None, 'content': ''}
TYPE_ALIASES = {
    '地点': 'location',
    '诗人': 'person',
    '人物': 'person',
    '事件': 'event',
    '诗词': 'poem',
    '诗作': 'poem',
    '文化': 'culture',
    '历史': 'history',
    '技法': 'technique',
    '主题': 'theme',
    '概念': 'concept',
    'location': 'location',
    'person': 'person',
    'event': 'event',
    'poem': 'poem',
    'poet': 'person',
    'time': 'history',
    'culture': 'culture',
    'history': 'history',
    'technique': 'technique',
    'theme': 'theme',
    'concept': 'concept',
}
TEACHING_PROMPT_BY_TYPE = {
    'person': (
        "面向学生讲清诗人的人生经历、性格气质、代表作品和作品中的情感力量。"
    ),
    'poem': (
        "面向学生讲清诗词画面、关键意象、情感变化和一句值得记住的赏析结论。"
    ),
    'location': (
        "面向学生讲清地点的画面感、历史文化、诗词象征和它为什么会触动诗人。"
    ),
    'event': (
        "面向学生讲清事件背景、人物处境、情绪压力和它如何进入诗词表达。"
    ),
    'culture': (
        "面向学生讲清文化常识如何帮助理解诗词中的礼俗、空间、人物关系和情绪。"
    ),
    'history': (
        "面向学生讲清历史背景如何改变人物处境，并转化为诗词中的家国、漂泊或兴亡之感。"
    ),
    'technique': (
        "面向学生讲清表现技法如何组织画面、推进情绪、形成表达效果。"
    ),
    'theme': (
        "面向学生讲清主题如何从画面、处境和情绪中自然生长出来。"
    ),
}
CONTENT_REJECT_TERMS = (
    '解释它如何',
    '解释它带出',
    '解释它和',
    '角度一',
    '角度二',
    '角度三',
    '关键词',
    '情感投入',
    '仿佛穿越',
    '古色古香',
    '熙熙攘攘',
    '叫卖声',
    '红墙碧瓦',
    '旅游',
    '想象一下',
    '你是否',
    '如果你是',
    '市井喧嚣',
    '宫阙',
    '洛阳刺史',
    '《琵琶行》中以洛阳',
    '《琵琶行》写于洛阳',
    '琵琶行》写于洛阳',
)


def parse_jsonish_value(value):
    if not isinstance(value, str):
        return value
    text = value.strip()
    if not text:
        return ''
    try:
        return jsonlib.loads(text)
    except ValueError:
        return text


def summarize_payload_value(value):
    parsed = parse_jsonish_value(value)
    if isinstance(parsed, str):
        return parsed.strip()
    if isinstance(parsed, list):
        items = [summarize_payload_value(item) for item in parsed]
        return '、'.join(item for item in items if item)[:80]
    if isinstance(parsed, dict):
        for key in ('name', 'title', 'context', 'poem', 'poemString', 'place', 'location', 'intro', 'introduction', 'time'):
            if parsed.get(key):
                summary = summarize_payload_value(parsed.get(key))
                if summary:
                    return summary[:80]
        values = [summarize_payload_value(item) for item in parsed.values()]
        return '、'.join(item for item in values if item)[:80]
    if parsed is None:
        return ''
    return str(parsed).strip()


def normalize_classroom_payload(data):
    concept_type = data.get('type') or data.get('concept_type') or 'concept'
    concept_type = TYPE_ALIASES.get(str(concept_type).strip(), 'concept')
    context_value = data.get('context') or ''
    description = data.get('description') or data.get('content') or data.get('name') or data.get('target_name') or data.get('target_id') or '当前对象'
    content_value = summarize_payload_value(description) or '当前对象'
    normalized = dict(data)
    normalized['type'] = concept_type
    normalized['concept_type'] = concept_type
    normalized['context'] = str(context_value).strip()
    normalized['name'] = str(content_value).strip()
    normalized['description'] = str(content_value).strip()
    return normalized


def load_knowledge_base():
    try:
        stat = KNOWLEDGE_BASE_PATH.stat()
    except OSError:
        return ''

    if KNOWLEDGE_BASE_CACHE['mtime'] != stat.st_mtime:
        KNOWLEDGE_BASE_CACHE['mtime'] = stat.st_mtime
        KNOWLEDGE_BASE_CACHE['content'] = KNOWLEDGE_BASE_PATH.read_text(encoding='utf-8').strip()

    return KNOWLEDGE_BASE_CACHE['content']









def ensure_classroom_table():
    try:
        ClassroomEvent.__table__.create(db.engine, checkfirst=True)
    except OperationalError as exc:
        original = getattr(exc, 'orig', None)
        if not original or getattr(original, 'args', [None])[0] != 1050:
            raise


def current_classroom_session_id():
    if current_user.is_authenticated:
        return f"user:{current_user.id}"
    return None


def classroom_session_id_from_payload(data):
    session_id = current_classroom_session_id()
    if session_id:
        return session_id, None, None

    user_id = data.get('user_id') or data.get('userId')
    if user_id in (None, ''):
        return None, jsonify({'message': '缺少 user_id'}), 400
    try:
        user_id = int(user_id)
    except (TypeError, ValueError):
        return None, jsonify({'message': 'user_id 必须是数字'}), 400
    if user_id <= 0:
        return None, jsonify({'message': 'user_id 必须是正整数'}), 400
    return f"user:{user_id}", None, None


def require_classroom_user():
    session_id = current_classroom_session_id()
    if not session_id:
        return None, jsonify({'message': '请先登录'}), 401
    return session_id, None, None


def save_event(session_id, event_type, source='system', concept_type=None, name=None, content=None, payload=None):
    ensure_classroom_table()
    event = ClassroomEvent(
        session_id=session_id,
        event_type=event_type,
        source=source,
        concept_type=concept_type,
        name=name,
        content=content,
        event_payload=payload or {},
    )
    db.session.add(event)
    try:
        db.session.commit()
    except Exception:
        db.session.rollback()
        raise
    return event


def save_generated_image(image_b64):
    GENERATED_IMAGE_DIR.mkdir(parents=True, exist_ok=True)
    filename = f"{uuid.uuid4().hex}.png"
    path = GENERATED_IMAGE_DIR / filename
    path.write_bytes(base64.b64decode(image_b64))
    return f"/static/generated/{filename}"


def sse_event(event_type, data):
    payload = jsonlib.dumps(data, ensure_ascii=False)
    return f"event: {event_type}\ndata: {payload}\n\n"


@classroom.route('/classroom/teacher', methods=['GET'])
def classroom_teacher():
    if not current_user.is_authenticated:
        return redirect('/api/classroom/login')
    username = getattr(current_user, 'username', None) or getattr(current_user, 'email', None) or str(current_user.id)
    return render_template('classroom_teacher.html', username=username)


@classroom.route('/classroom/login', methods=['GET'])
def classroom_login():
    if current_user.is_authenticated:
        return redirect('/api/classroom/teacher')
    return render_template('classroom_login.html')






















def generate_mermaid_code(data, chart_type='mindmap'):
    code = build_deterministic_mindmap(data)
    return code if validate_mermaid_code(code, chart_type) else None


def generate_classroom_image(app, session_id, data, event_context, teaching_content):
    with app.app_context():
        try:
            from app.aiapi.main import generate_image

            image_started_at = time.time()
            save_event(
                session_id=session_id,
                event_type='image_start',
                source='B',
                payload=event_context,
            )
            image_kwargs = {
                'model': data.get('image_model', CLASSROOM_IMAGE_MODEL),
                'size': data.get('image_size', CLASSROOM_IMAGE_SIZE),
                'steps': int(data.get('image_steps', CLASSROOM_IMAGE_STEPS)),
                'cfg_scale': float(data.get('image_cfg_scale', 1.0)),
                'timeout': float(data.get('image_timeout', CLASSROOM_IMAGE_TIMEOUT)),
                'n': max(1, min(int(data.get('image_count', CLASSROOM_IMAGE_COUNT)), 1)),
            }
            try:
                image_data = generate_image(build_image_prompt(data, teaching_content), **image_kwargs)
            except Exception:
                image_data = generate_image(build_safe_symbolic_image_prompt(data, teaching_content), **image_kwargs)
            image_urls = []
            for item in image_data:
                image = getattr(item, 'b64_json', None)
                if not image:
                    continue
                image_urls.append(save_generated_image(image))
            if image_urls:
                save_event(
                    session_id=session_id,
                    event_type='image_done',
                    source='B',
                    content=image_urls[0],
                    payload={
                        **event_context,
                        'format': 'url',
                        'urls': image_urls,
                        'duration_seconds': round(time.time() - image_started_at, 2),
                    },
                )
            else:
                save_event(
                    session_id=session_id,
                    event_type='image_error',
                    source='B',
                    content='图片接口未返回有效图像。',
                    payload=event_context,
                )
        except Exception as image_exc:
            save_event(
                session_id=session_id,
                event_type='image_error',
                source='B',
                content=str(image_exc),
                payload=event_context,
            )


def generate_teaching_content(app, session_id, data):
    with app.app_context():
        try:
            from app.aiapi.main import STEPFUN_CHAT_MODEL, create_stepfun_client, markdown_messages

            data = normalize_classroom_payload(data)
            component_id = data.get('component_id') or uuid.uuid4().hex
            event_context = {
                'component_id': component_id,
                'concept_event_id': data.get('concept_event_id'),
                'extension': data.get('extension'),
            }
            prompt = build_teaching_prompt(data)
            started_at = time.time()
            save_event(
                session_id=session_id,
                event_type='lesson_component_start',
                source='B',
                payload=event_context,
            )
            save_event(
                session_id=session_id,
                event_type='ai_start',
                source='B',
                payload={**event_context, 'prompt': prompt},
            )

            client = create_stepfun_client()
            response = client.chat.completions.create(
                model=STEPFUN_CHAT_MODEL,
                messages=markdown_messages([{'role': 'user', 'content': prompt}]),
                stream=True,
            )

            full_content = []
            delta_buffer = []
            last_delta_flush = time.time()
            for chunk in response:
                content = chunk.choices[0].delta.content
                if not content:
                    continue

                full_content.append(content)
                delta_buffer.append(content)
                if time.time() - last_delta_flush >= 0.25:
                    save_event(
                        session_id=session_id,
                        event_type='markdown_delta',
                        source='B',
                        content=''.join(delta_buffer),
                        payload=event_context,
                    )
                    delta_buffer = []
                    last_delta_flush = time.time()

            if delta_buffer:
                save_event(
                    session_id=session_id,
                    event_type='markdown_delta',
                    source='B',
                    content=''.join(delta_buffer),
                    payload=event_context,
                )

            save_event(
                session_id=session_id,
                event_type='markdown_done',
                source='B',
                content=''.join(full_content),
                payload=event_context,
            )

            teaching_content = ''.join(full_content)
            if teaching_content_needs_revision(teaching_content, data):
                revision_response = client.chat.completions.create(
                    model=STEPFUN_CHAT_MODEL,
                    messages=markdown_messages([
                        {'role': 'user', 'content': build_revision_prompt(data, teaching_content)},
                    ]),
                )
                revised_content = revision_response.choices[0].message.content
                if revised_content and not teaching_content_needs_revision(revised_content, data):
                    teaching_content = revised_content
                    save_event(
                        session_id=session_id,
                        event_type='markdown_done',
                        source='B',
                        content=teaching_content,
                        payload={**event_context, 'revision': True},
                    )
            image_urls = []
            mermaid_codes = {}
            try:
                save_event(
                    session_id=session_id,
                    event_type='mermaid_start',
                    source='B',
                    payload=event_context,
                )
                mermaid_code = generate_mermaid_code(data, 'mindmap')
                if validate_mermaid_code(mermaid_code, 'mindmap'):
                    mermaid_codes['mindmap'] = mermaid_code
                    save_event(
                        session_id=session_id,
                        event_type='mermaid_done',
                        source='B',
                        content=mermaid_code,
                        payload={**event_context, 'chart_type': 'mindmap', 'deterministic': True},
                    )
                else:
                    save_event(
                        session_id=session_id,
                        event_type='mermaid_error',
                        source='B',
                        content='Mermaid 代码未通过服务端格式审核。',
                        payload={**event_context, 'chart_type': 'mindmap'},
                    )
            except Exception as mermaid_exc:
                save_event(
                    session_id=session_id,
                    event_type='mermaid_error',
                    source='B',
                    content=str(mermaid_exc),
                    payload=event_context,
                )
            save_event(
                session_id=session_id,
                event_type='lesson_ready',
                source='B',
                content=teaching_content,
                payload={
                    **event_context,
                    'markdown': teaching_content,
                    'mermaid': mermaid_codes.get('mindmap'),
                    'mermaids': mermaid_codes,
                    'images': image_urls,
                    'duration_seconds': round(time.time() - started_at, 2),
                },
            )
            if data.get('generate_image'):
                image_thread = threading.Thread(
                    target=generate_classroom_image,
                    args=(app, session_id, dict(data), dict(event_context), teaching_content),
                    daemon=True,
                )
                image_thread.start()
        except Exception as exc:
            save_event(
                session_id=session_id,
                event_type='error',
                source='B',
                content=str(exc),
                payload={'component_id': data.get('component_id'), 'concept_event_id': data.get('concept_event_id')},
            )


@classroom.route('/classroom/events', methods=['GET'])
def list_classroom_events():
    ensure_classroom_table()
    session_id, error_response, status_code = require_classroom_user()
    if error_response:
        return error_response, status_code

    limit = min(int(request.args.get('limit', 100)), 500)

    events = (
        ClassroomEvent.query
        .filter_by(session_id=session_id)
        .order_by(ClassroomEvent.id.desc())
        .limit(limit)
        .all()
    )
    events.reverse()

    return jsonify({'events': [event.to_dict() for event in events]}), 200


@classroom.route('/classroom/events', methods=['POST'])
def create_classroom_event():
    data = normalize_classroom_payload(request.get_json(silent=True) or {})
    session_id, error_response, status_code = classroom_session_id_from_payload(data)
    if error_response:
        return error_response, status_code

    concept_type = data.get('concept_type') or data.get('type')
    name = data.get('name')
    generate_ai = bool(data.get('generate_ai', False))

    event = save_event(
        session_id=session_id,
        event_type='concept',
        source='A',
        concept_type=concept_type,
        name=name,
        content=data.get('context'),
        payload=data,
    )

    if generate_ai:
        app = current_app._get_current_object()
        thread = threading.Thread(
            target=generate_teaching_content,
            args=(app, session_id, data),
            daemon=True,
        )
        thread.start()

    return jsonify({'event': event.to_dict()}), 201


@classroom.route('/classroom/events/<int:event_id>/generate', methods=['POST'])
def generate_classroom_lesson(event_id):
    session_id, error_response, status_code = require_classroom_user()
    if error_response:
        return error_response, status_code

    ensure_classroom_table()
    concept_event = ClassroomEvent.query.filter_by(
        id=event_id,
        session_id=session_id,
        event_type='concept',
    ).first()
    if not concept_event:
        return jsonify({'message': '课堂概念不存在'}), 404

    request_data = request.get_json(silent=True) or {}
    base_payload = dict(concept_event.event_payload or {})
    base_payload.update({
        key: value
        for key, value in request_data.items()
        if key in (
            'context', 'type', 'description', 'extension', 'generate_image',
            'image_model', 'image_size', 'image_steps', 'image_cfg_scale',
        )
    })
    base_payload['context'] = base_payload.get('context') or concept_event.content or ''
    base_payload['type'] = base_payload.get('type') or concept_event.concept_type
    base_payload['description'] = base_payload.get('description') or concept_event.name or ''
    base_payload['concept_event_id'] = concept_event.id
    base_payload['component_id'] = request_data.get('component_id') or uuid.uuid4().hex
    base_payload['generate_image'] = request_data.get('generate_image', True)

    data = normalize_classroom_payload(base_payload)
    app = current_app._get_current_object()
    thread = threading.Thread(
        target=generate_teaching_content,
        args=(app, session_id, data),
        daemon=True,
    )
    thread.start()

    return jsonify({
        'component_id': data['component_id'],
        'concept_event_id': concept_event.id,
        'extension': data.get('extension'),
    }), 202


@classroom.route('/classroom/events/stream', methods=['GET'])
def stream_classroom_events():
    ensure_classroom_table()
    session_id, error_response, status_code = require_classroom_user()
    if error_response:
        return error_response, status_code

    replay = request.args.get('replay') == '1'

    if replay:
        last_id = int(request.args.get('last_id', 0))
    else:
        latest_event = (
            ClassroomEvent.query
            .filter_by(session_id=session_id)
            .order_by(ClassroomEvent.id.desc())
            .first()
        )
        last_id = latest_event.id if latest_event else 0

    def generate():
        nonlocal last_id
        last_heartbeat = time.time()
        yield sse_event('ready', {'session_id': session_id, 'last_id': last_id})

        while True:
            db.session.remove()
            events = (
                ClassroomEvent.query
                .filter(
                    ClassroomEvent.session_id == session_id,
                    ClassroomEvent.id > last_id,
                )
                .order_by(ClassroomEvent.id.asc())
                .limit(100)
                .all()
            )

            if events:
                for event in events:
                    last_id = event.id
                    yield sse_event(event.event_type, event.to_dict())
                last_heartbeat = time.time()
            elif time.time() - last_heartbeat >= HEARTBEAT_SECONDS:
                yield sse_event('heartbeat', {'session_id': session_id, 'last_id': last_id})
                last_heartbeat = time.time()

            time.sleep(POLL_INTERVAL_SECONDS)

    return Response(stream_with_context(generate()), content_type='text/event-stream')
