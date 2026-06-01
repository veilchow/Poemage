from app.poem import poem
from app.libs.extensions import db
# 引入相关模型
from app.models import User, Creation, Poem
from flask_login import login_required, current_user
from flask import request, jsonify, redirect, session, make_response, Response


@poem.route('/poems', methods=['GET'])
def get_all_poems():
    poems = Poem.query.all()
    result = [
        {
            'id': poem.id,
            'name': poem.name,
            'content': poem.content,
            'created_at': poem.created_at.isoformat(),
            'poem_info': poem.poem_info
        }
        for poem in poems
    ]
    return jsonify({'poems': result}), 200


# 添加诗歌
@poem.route('/poems', methods=['POST'])
@login_required
def add_poem():
    data = request.get_json()
    if not data:
        return jsonify({'message': '请求数据必须为JSON格式'}), 400

    required_fields = ['name', 'content']
    missing_fields = [field for field in required_fields if field not in data]
    if missing_fields:
        return jsonify({'message': f'缺少必要的字段：{", ".join(missing_fields)}'}), 400

    name = data.get('name')
    content = data.get('content')
    poem_info = data.get('poem_info', '')

    if not isinstance(name, str) or not isinstance(content, str):
        return jsonify({'message': '字段类型不正确'}), 400

    poem = Poem(
        name=name,
        content=content,
        poem_info=poem_info
    )
    db.session.add(poem)
    db.session.commit()

    result = {
        'id': poem.id,
        'name': poem.name,
        'content': poem.content,
        'created_at': poem.created_at.isoformat(),
        'poem_info': poem.poem_info
    }

    return jsonify({'message': '诗歌添加成功', 'poem': result}), 201
