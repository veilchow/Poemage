from app.save import save
from app.libs.extensions import db
# 引入相关模型
from app.models import Save
from flask_login import login_required, current_user
from flask import request, json, jsonify, redirect, session, make_response, Response


# 获取所有存档信息
@save.route('/saves', methods=['GET'])
def get_all_saves():
    saves = Save.query.all()
    if not saves:
        return jsonify({"message": "没有找到任何存档"}), 404

    result = [
        {
            "id": save.id,
            "user_id": save.user_id,
            "curMissionIndex": save.curMissionIndex,
            "isBefore": save.isBefore,
            "charaPosition": save.charaPosition,  # JSON 数据直接返回
            "direction": save.direction,
            "poemFinishStatus": save.poemFinishStatus,  # JSON 数据直接返回
            "curPoetId": save.curPoetId,
            "poetFinishStatus": save.poetFinishStatus,
            "created_at": save.created_at.isoformat()
        }
        for save in saves
    ]

    return jsonify({"saveInfoList": result}), 200


# 获取指定存档信息
@save.route('/saves/<int:user_id>', methods=['GET'])
# @login_required
def get_save(user_id):
    # 检查是否登录，并且是否是当前用户
    # if current_user.id != user_id:
    #     return jsonify({"message": "无权限访问该存档"}), 403

    save = Save.query.filter_by(user_id=user_id).first()
    if not save:
        return jsonify({"message": "存档为空"}), 404

    result = {
        "id": save.id,
        "user_id": save.user_id,
        "curMissionIndex": save.curMissionIndex,
        "isBefore": save.isBefore,
        "charaPosition": save.charaPosition,  # JSON 数据直接返回
        "direction": save.direction,
        "poemFinishStatus": save.poemFinishStatus,  # JSON 数据直接返回
        "curPoetId": save.curPoetId,
        "poetFinishStatus": save.poetFinishStatus,
        "created_at": save.created_at.isoformat()
    }

    return jsonify(result), 200


# 上传/更新存档
@save.route('/saves/<int:user_id>', methods=['POST'])
# @login_required
def create_or_update_save(user_id):
    # 检查是否登录，并且是否是当前用户
    # if current_user.id != user_id:
    #     return jsonify({"message": "无权限访问该存档"}), 403

    data = request.get_json()
    if not data:
        return jsonify({"message": "请求数据必须为JSON格式"}), 400

    required_fields = [
        'curMissionIndex',
        'isBefore',
        'charaPosition',
        'direction',
        'poemFinishStatus',
        'curPoetId',
        'poetFinishStatus'
    ]
    missing_fields = [field for field in required_fields if field not in data]
    if missing_fields:
        return jsonify({"message": f"缺少必要的字段：{', '.join(missing_fields)}"}), 400

    save = Save.query.filter_by(user_id=user_id).first()

    if save:
        # 更新存档
        save.curMissionIndex = data['curMissionIndex']
        save.isBefore = data['isBefore']
        save.charaPosition = data['charaPosition']  # 直接保存为 JSON 格式
        save.direction = data['direction']
        save.poemFinishStatus = data['poemFinishStatus']  # 保存为 JSON 数组
        save.curPoetId = data['curPoetId']  # <--- 新增
        save.poetFinishStatus = data['poetFinishStatus']  # <--- 新增
    else:
        # 创建新存档
        save = Save(
            user_id=user_id,
            curMissionIndex=data['curMissionIndex'],
            isBefore=data['isBefore'],
            charaPosition=data['charaPosition'],  # 直接保存为 JSON 格式
            direction=data['direction'],
            poemFinishStatus=data['poemFinishStatus'],  # 保存为 JSON 数组
            curPoetId=data['curPoetId'],
            poetFinishStatus=data['poetFinishStatus']
        )
        db.session.add(save)

    db.session.commit()

    # 返回更新后的存档数据
    result = {
        "id": save.id,
        "user_id": save.user_id,
        "curMissionIndex": save.curMissionIndex,
        "isBefore": save.isBefore,
        "charaPosition": save.charaPosition,
        "direction": save.direction,
        "poemFinishStatus": save.poemFinishStatus,
        "curPoetId": save.curPoetId,
        "poetFinishStatus": save.poetFinishStatus,
        "created_at": save.created_at.isoformat()
    }

    return jsonify({"message": "存档保存成功", "save": result}), 200


# 删除存档
@save.route('/saves/<int:user_id>', methods=['DELETE'])
# @login_required
def delete_save(user_id):
    # 检查是否登录，并且是否是当前用户
    # if current_user.id != user_id:
    #     return jsonify({"message": "无权限访问该存档"}), 403

    save = Save.query.filter_by(user_id=user_id).first()
    if not save:
        return jsonify({"message": "存档未找到"}), 404

    db.session.delete(save)
    db.session.commit()

    return jsonify({"message": "存档删除成功"}), 200
