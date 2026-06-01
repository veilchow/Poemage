from app.economic import economic
from app.libs.extensions import db
# 引入相关模型
from app.models import Economic
from flask_login import login_required, current_user
from flask import request, json, jsonify, redirect, session, make_response, Response


# 获取所有用户经济信息
@economic.route('/economics', methods=['GET'])
def get_all_economics():
    economics = Economic.query.all()
    if not economics:
        return jsonify({"message": "没有找到任何经济数据"}), 404

    result = [
        {
            "id": economic.id,
            "user_id": economic.user_id,
            "coin_value": economic.coin_value,  # 金币值直接返回
            "created_at": economic.created_at.isoformat()
        }
        for economic in economics
    ]

    return jsonify({"economicInfoList": result}), 200


# 获取指定用户的经济信息
@economic.route('/economics/<int:user_id>', methods=['GET'])
def get_economic(user_id):
    economic = Economic.query.filter_by(user_id=user_id).first()
    if not economic:
        return jsonify({"message": "经济数据为空"}), 404

    result = {
        "id": economic.id,
        "user_id": economic.user_id,
        "coin_value": economic.coin_value,  # 金币值直接返回
        "created_at": economic.created_at.isoformat()
    }

    return jsonify(result), 200


# 更新用户的金币值
@economic.route('/economics/<int:user_id>', methods=['POST'])
def update_economic(user_id):
    data = request.get_json()
    if not data:
        return jsonify({"message": "请求数据必须为 JSON 格式"}), 400

    required_fields = ['coin_value']
    missing_fields = [field for field in required_fields if field not in data]
    if missing_fields:
        return jsonify({"message": f"缺少必要的字段：{', '.join(missing_fields)}"}), 400

    economic = Economic.query.filter_by(user_id=user_id).first()

    if economic:
        # 更新金币值
        economic.coin_value = data['coin_value']
    else:
        economic = Economic(
            user_id=user_id,
            coin_value=data['coin_value']
        )
        db.session.add(economic)

    db.session.commit()

    # 返回更新后的经济数据
    result = {
        "id": economic.id,
        "user_id": economic.user_id,
        "coin_value": economic.coin_value,
        "created_at": economic.created_at.isoformat()
    }

    return jsonify({"message": "金币值更新成功", "economic": result}), 200


# 删除指定用户的经济数据
@economic.route('/economics/<int:user_id>', methods=['DELETE'])
def delete_economic(user_id):
    economic = Economic.query.filter_by(user_id=user_id).first()
    if not economic:
        return jsonify({"message": "经济数据未找到"}), 404

    db.session.delete(economic)
    db.session.commit()

    return jsonify({"message": "经济数据删除成功"}), 200