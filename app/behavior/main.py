from app.behavior import behavior
from app.libs.extensions import db
# 引入相关模型
from app.models import Behavior
from flask_login import login_required, current_user
from flask import request, json, jsonify, redirect, session, make_response, Response


# 获取所有行为信息
@behavior.route('/behaviors', methods=['GET'])
def get_all_behaviors():
    behaviors = Behavior.query.all()
    if not behaviors:
        return jsonify({"message": "没有找到任何行为数据"}), 404

    result = [
        {
            "id": behavior.id,
            "user_id": behavior.user_id,
            "behaviorFile": behavior.behaviorFile,  # JSON 数据直接返回
            "created_at": behavior.created_at.isoformat()
        }
        for behavior in behaviors
    ]

    return jsonify({"behaviorInfoList": result}), 200


# 获取指定行为信息
@behavior.route('/behaviors/<int:user_id>', methods=['GET'])
def get_behavior(user_id):
    behavior = Behavior.query.filter_by(user_id=user_id).first()
    if not behavior:
        return jsonify({"message": "行为数据为空"}), 404

    result = {
        "id": behavior.id,
        "user_id": behavior.user_id,
        "behaviorFile": behavior.behaviorFile,  # JSON 数据直接返回
        "created_at": behavior.created_at.isoformat()
    }

    return jsonify(result), 200


# 上传/更新行为数据
@behavior.route('/behaviors/<int:user_id>', methods=['POST'])
def create_or_update_behavior(user_id):
    data = request.get_json()
    if not data:
        return jsonify({"message": "请求数据必须为 JSON 格式"}), 400

    required_fields = ['behaviorFile']
    missing_fields = [field for field in required_fields if field not in data]
    if missing_fields:
        return jsonify({"message": f"缺少必要的字段：{', '.join(missing_fields)}"}), 400

    behavior = Behavior.query.filter_by(user_id=user_id).first()

    if behavior:
        # 更新行为数据
        behavior.behaviorFile = data['behaviorFile']
    else:
        # 创建新行为数据
        behavior = Behavior(
            user_id=user_id,
            behaviorFile=data['behaviorFile']
        )
        db.session.add(behavior)

    db.session.commit()

    # 返回更新后的行为数据
    result = {
        "id": behavior.id,
        "user_id": behavior.user_id,
        "behaviorFile": behavior.behaviorFile,
        "created_at": behavior.created_at.isoformat()
    }

    return jsonify({"message": "行为数据保存成功", "behavior": result}), 200


# 删除行为数据
@behavior.route('/behaviors/<int:user_id>', methods=['DELETE'])
def delete_behavior(user_id):
    behavior = Behavior.query.filter_by(user_id=user_id).first()
    if not behavior:
        return jsonify({"message": "行为数据未找到"}), 404

    db.session.delete(behavior)
    db.session.commit()

    return jsonify({"message": "行为数据删除成功"}), 200


# 添加或更新behaviorFile中的元素
@behavior.route('/behaviors/<int:user_id>/elements', methods=['POST'])
def add_or_update_behavior_element(user_id):
    # 获取请求数据
    data = request.get_json()
    if not data:
        return jsonify({"message": "请求数据必须为 JSON 格式"}), 400

    # 验证必要字段
    required_fields = ['behavior_index']
    missing_fields = [field for field in required_fields if field not in data]
    if missing_fields:
        return jsonify({"message": f"缺少必要的字段：{', '.join(missing_fields)}"}), 400

    # 查询用户的行为数据
    behavior = Behavior.query.filter_by(user_id=user_id).first()
    
    if not behavior:
        # 如果用户没有行为数据，创建新的并添加元素
        behavior = Behavior(
            user_id=user_id,
            behaviorFile=[data]  # 直接将新元素作为列表的第一个元素
        )
        db.session.add(behavior)
    else:
        # 确保behaviorFile是列表
        if not isinstance(behavior.behaviorFile, list):
            behavior.behaviorFile = []
        
        # 创建behaviorFile的深拷贝以便修改
        behavior_file = list(behavior.behaviorFile)  # 创建新的列表对象
        
        # 查找是否有相同behavior_index的元素
        found = False
        for i, element in enumerate(behavior_file):
            if str(element.get('behavior_index')) == str(data['behavior_index']):
                # 更新现有元素
                behavior_file[i] = data
                found = True
                break
        
        if not found:
            # 添加新元素
            behavior_file.append(data)
        
        # 更新behavior对象的behaviorFile
        behavior.behaviorFile = behavior_file
    
    try:
        db.session.commit()
        # 重新查询确保返回最新数据
        db.session.refresh(behavior)
        return jsonify({
            "message": "行为元素添加/更新成功"
        }), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"message": f"数据库错误: {str(e)}"}), 500