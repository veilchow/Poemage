from app.user import user
from app.libs.extensions import db
# 引入相关模型
from app.models import User, Creation, Poem
from flask_login import login_required, current_user
from flask import request, jsonify, redirect, session, make_response, Response


@user.route('/users/<int:user_id>/creations/count', methods=['GET'])
@login_required
def get_creation_count(user_id):
    if user_id != current_user.id:
        return jsonify({'message': '无权查看他人的创作数量'}), 403

    count = current_user.creations.count()
    return jsonify({'user_id': user_id, 'creation_count': count}), 200


@user.route('/users/<int:user_id>/creations', methods=['GET'])
@login_required
def get_user_creations(user_id):
    if user_id != current_user.id:
        return jsonify({'message': '无权查看他人的创作'}), 403

    # 获取查询参数
    start_id = request.args.get('start_id', type=int)
    end_id = request.args.get('end_id', type=int)

    if start_id is None or end_id is None:
        return jsonify({'message': '缺少必要的参数：start_id和end_id'}), 400

    # 查询指定范围内的创作
    creations = Creation.query.filter(
        Creation.user_id == user_id,
        Creation.id >= start_id,
        Creation.id <= end_id
    ).all()

    creation_list = [
        {
            'id': c.id,
            'name': c.name,
            'poem_id': c.poem_id,
            'content': c.content,
            'created_at': c.created_at.isoformat(),
            'creation_info': c.creation_info
        } for c in creations
    ]

    return jsonify({
        'user_id': user_id,
        'creations': creation_list
    }), 200
