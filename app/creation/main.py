from app.creation import creation
from app.libs.extensions import db
# 引入相关模型
from app.models import User, Creation, Poem
from flask_login import login_required, current_user
from flask import request, jsonify, redirect, session, make_response, Response


@creation.route('/creations/<int:creation_id>', methods=['GET'])
def get_creation(creation_id):
    creation = Creation.query.get_or_404(creation_id)
    result = {
        'id': creation.id,
        'name': creation.name,
        'user_id': creation.user_id,
        'poem_id': creation.poem_id,
        'content': creation.content,
        'created_at': creation.created_at.isoformat(),
        'creation_info': creation.creation_info
    }
    return jsonify({'creation': result}), 200


@creation.route('/creations', methods=['GET'])
def get_all_creations():
    creations = Creation.query.all()

    creation_list = [
        {
            'id': c.id,
            'name': c.name,
            'user_id': c.user_id,
            'poem_id': c.poem_id,
            'content': c.content,
            'created_at': c.created_at.isoformat(),
            'creation_info': c.creation_info
        } for c in creations
    ]

    return jsonify({
        'creations': creation_list
    }), 200


@creation.route('/creations', methods=['POST'])
@login_required
def add_creation():
    data = request.get_json()
    if not data:
        return jsonify({'message': '请求数据必须为JSON格式'}), 400

    # 验证必要字段
    required_fields = ['name', 'poem_id']
    missing_fields = [field for field in required_fields if field not in data]
    if missing_fields:
        return jsonify({'message': f'缺少必要的字段：{", ".join(missing_fields)}'}), 400

    name = data.get('name')
    poem_id = data.get('poem_id')
    content = data.get('content', '')
    creation_info = data.get('creation_info', '')

    # 检查字段类型
    if not isinstance(name, str) or not isinstance(poem_id, int):
        return jsonify({'message': '字段类型不正确'}), 400

    # 检查诗歌是否存在
    poem = Poem.query.get(poem_id)
    if not poem:
        return jsonify({'message': '诗歌不存在'}), 404

    # 创建新的创作
    creation = Creation(
        name=name,
        user_id=current_user.id,
        poem_id=poem_id,
        content=content,
        creation_info=creation_info
    )
    db.session.add(creation)
    db.session.commit()

    # 返回结果
    result = {
        'id': creation.id,
        'name': creation.name,
        'user_id': creation.user_id,
        'poem_id': creation.poem_id,
        'content': creation.content,
        'created_at': creation.created_at.isoformat(),
        'creation_info': creation.creation_info
    }

    return jsonify({'message': '创作添加成功', 'creation': result}), 201


@creation.route('/creations/<int:creation_id>', methods=['PUT'])
@login_required
def update_creation(creation_id):
    creation = Creation.query.get_or_404(creation_id)
    if creation.user_id != current_user.id:
        return jsonify({'message': '无权修改他人的创作'}), 403

    data = request.get_json()
    if not data:
        return jsonify({'message': '请求数据必须为JSON格式'}), 400

    # 更新字段
    if 'name' in data:
        if not isinstance(data['name'], str):
            return jsonify({'message': 'name字段类型不正确'}), 400
        creation.name = data['name']
    if 'content' in data:
        creation.content = data['content']
    if 'creation_info' in data:
        creation.creation_info = data['creation_info']

    db.session.commit()

    result = {
        'id': creation.id,
        'name': creation.name,
        'user_id': creation.user_id,
        'poem_id': creation.poem_id,
        'content': creation.content,
        'created_at': creation.created_at.isoformat(),
        'creation_info': creation.creation_info
    }

    return jsonify({'message': '创作更新成功', 'creation': result}), 200


@creation.route('/creations/<int:creation_id>', methods=['DELETE'])
@login_required
def delete_creation(creation_id):
    creation = Creation.query.get_or_404(creation_id)
    if creation.user_id != current_user.id:
        return jsonify({'message': '无权删除他人的创作'}), 403

    db.session.delete(creation)
    db.session.commit()
    return jsonify({'message': '创作删除成功'}), 200
