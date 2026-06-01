from app.texture import texture
from app.libs.extensions import db
# 引入相关模型
# from app.models import User, Creation, Poem, Texture
# from flask_login import login_required, current_user
# from flask import request, jsonify, redirect, session, make_response, Response
#
#
# @texture.route('/creations/<int:creation_id>/textures', methods=['GET'])
# @login_required
# def get_textures(creation_id):
#     # 检查创作是否存在并属于当前用户，确保用户只能查看自己的创作的纹理。
#     creation = Creation.query.get_or_404(creation_id)
#     if creation.user_id != current_user.id:
#         return jsonify({'message': '无权查看他人的创作'}), 403
#
#     textures = Texture.query.filter_by(creation_id=creation_id).all()
#     textures_list = [texture.to_dict() for texture in textures]
#
#     return jsonify({'textures': textures_list}), 200
#
#
# @texture.route('/creations/<int:creation_id>/textures/<int:sub_id>', methods=['GET'])
# @login_required
# def get_texture(creation_id, sub_id):
#     # 检查创作是否存在并属于当前用户
#     creation = Creation.query.get_or_404(creation_id)
#     if creation.user_id != current_user.id:
#         return jsonify({'message': '无权查看他人的创作'}), 403
#
#     texture = Texture.query.get_or_404((creation_id, sub_id))
#     return jsonify({'texture': texture.to_dict()}), 200
#
#
# @texture.route('/creations/<int:creation_id>/textures', methods=['POST'])
# @login_required
# def add_or_update_texture(creation_id):
#     data = request.get_json()
#     if not data:
#         return jsonify({'message': '请求数据必须为JSON格式'}), 400
#
#     # 验证必要字段
#     required_fields = ['sub_id', 'base64_code']
#     missing_fields = [field for field in required_fields if field not in data]
#     if missing_fields:
#         return jsonify({'message': f'缺少必要的字段：{", ".join(missing_fields)}'}), 400
#
#     sub_id = data['sub_id']
#     base64_code = data['base64_code']
#     texture_info = data.get('texture_info', '')
#
#     # 检查字段类型
#     if not isinstance(sub_id, int) or not isinstance(base64_code, str):
#         return jsonify({'message': '字段类型不正确'}), 400
#
#     # 检查创作是否存在并属于当前用户
#     creation = Creation.query.get_or_404(creation_id)
#     if creation.user_id != current_user.id:
#         return jsonify({'message': '无权修改他人的创作'}), 403
#
#     # 检查纹理是否存在
#     texture = Texture.query.get((creation_id, sub_id))
#     if texture:
#         # 更新已有纹理
#         texture.base64_code = base64_code
#         texture.texture_info = texture_info
#         db.session.commit()
#         return jsonify({'message': '纹理已更新', 'texture': texture.to_dict()}), 200
#     else:
#         # 添加新纹理
#         texture = Texture(
#             creation_id=creation_id,
#             sub_id=sub_id,
#             base64_code=base64_code,
#             texture_info=texture_info
#         )
#         db.session.add(texture)
#         db.session.commit()
#         return jsonify({'message': '纹理已添加', 'texture': texture.to_dict()}), 201
