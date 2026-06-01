from app.ljson import ljson
from app.libs.extensions import db
# 引入相关模型
from app.models import Ljson
from flask_login import login_required, current_user
from flask import request, json, jsonify, redirect, session, make_response, Response


# 获取所有json信息
@ljson.route('/ljsons', methods=['GET'])
def get_all_ljsons():
    ljsons = Ljson.query.all()
    if not ljsons:
        return jsonify({"message": "没有找到任何 JSON 文件"}), 404

    result = [
        {
            "id": ljson.id,
            "user_id": ljson.user_id,
            "jsonFile": ljson.jsonFile,  # JSON 数据直接返回
            "created_at": ljson.created_at.isoformat()
        }
        for ljson in ljsons
    ]

    return jsonify({"ljsonInfoList": result}), 200


# 获取指定json信息
@ljson.route('/ljsons/<int:user_id>', methods=['GET'])
def get_ljson(user_id):
    ljson = Ljson.query.filter_by(user_id=user_id).first()
    if not ljson:
        return jsonify({"message": "JSON 文件为空"}), 404

    result = {
        "id": ljson.id,
        "user_id": ljson.user_id,
        "jsonFile": ljson.jsonFile,  # JSON 数据直接返回
        "created_at": ljson.created_at.isoformat()
    }

    return jsonify(result), 200


# 上传/更新json
@ljson.route('/ljsons/<int:user_id>', methods=['POST'])
def create_or_update_ljson(user_id):
    data = request.get_json()
    if not data:
        return jsonify({"message": "请求数据必须为 JSON 格式"}), 400

    required_fields = ['jsonFile']
    missing_fields = [field for field in required_fields if field not in data]
    if missing_fields:
        return jsonify({"message": f"缺少必要的字段：{', '.join(missing_fields)}"}), 400

    ljson = Ljson.query.filter_by(user_id=user_id).first()

    if ljson:
        # 更新 JSON 文件
        ljson.jsonFile = data['jsonFile']
    else:
        # 创建新 JSON 文件
        ljson = Ljson(
            user_id=user_id,
            jsonFile=data['jsonFile']
        )
        db.session.add(ljson)

    db.session.commit()

    # 返回更新后的 JSON 文件数据
    result = {
        "id": ljson.id,
        "user_id": ljson.user_id,
        "jsonFile": ljson.jsonFile,
        "created_at": ljson.created_at.isoformat()
    }

    return jsonify({"message": "JSON 文件保存成功", "ljson": result}), 200


# 删除json
@ljson.route('/ljsons/<int:user_id>', methods=['DELETE'])
def delete_ljson(user_id):
    ljson = Ljson.query.filter_by(user_id=user_id).first()
    if not ljson:
        return jsonify({"message": "JSON 文件未找到"}), 404

    db.session.delete(ljson)
    db.session.commit()

    return jsonify({"message": "JSON 文件删除成功"}), 200
