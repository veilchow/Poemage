from app.mission import mission
from app.libs.extensions import db
# 引入相关模型
from app.models import Mission
from flask_login import login_required, current_user
from flask import request, jsonify, redirect, session, make_response, Response


# 获取所有关卡信息
@mission.route('/missions', methods=['GET'])
def get_all_missions():
    missions = Mission.query.all()
    if not missions:
        return jsonify({'message': '没有关卡数据'}), 404  # 如果没有关卡数据，返回提示信息

    result = [
        {
            'id': mission.id,
            'curMissionIndex': mission.curMissionIndex,
            'isBefore': mission.isBefore,
            'charaPosition': mission.charaPosition,
            'direction': mission.direction,
            'missionPassedTag': mission.missionPassedTag,
            'created_at': mission.created_at.isoformat()
        }
        for mission in missions
    ]
    return jsonify({'missions': result}), 200


# 获取指定curMissionIndex的关卡信息
@mission.route('/missions/<int:curMissionIndex>', methods=['GET'])
def get_mission_by_index(curMissionIndex):
    mission = Mission.query.filter_by(curMissionIndex=curMissionIndex).first()
    if not mission:
        return jsonify({'message': '关卡未找到'}), 404

    result = {
        'id': mission.id,
        'curMissionIndex': mission.curMissionIndex,
        'isBefore': mission.isBefore,
        'charaPosition': mission.charaPosition,
        'direction': mission.direction,
        'missionPassedTag': mission.missionPassedTag,
        'created_at': mission.created_at.isoformat()
    }
    return jsonify({'mission': result}), 200


# 添加关卡
@mission.route('/missions', methods=['POST'])
def add_mission():
    data = request.get_json()
    if not data:
        return jsonify({'message': '请求数据必须为JSON格式'}), 400

    required_fields = ['curMissionIndex', 'isBefore', 'charaPosition', 'direction']
    missing_fields = [field for field in required_fields if field not in data]
    if missing_fields:
        return jsonify({'message': f'缺少必要的字段：{", ".join(missing_fields)}'}), 400

    curMissionIndex = data.get('curMissionIndex')
    if Mission.query.filter_by(curMissionIndex=curMissionIndex).first():
        return jsonify({'message': f'关卡 {curMissionIndex} 已存在'}), 400  # 如果关卡已经存在，返回错误

    isBefore = data.get('isBefore')
    charaPosition = data.get('charaPosition')
    direction = data.get('direction')
    missionPassedTag = data.get('missionPassedTag', False)

    # 创建新的Mission实例
    mission = Mission(
        curMissionIndex=curMissionIndex,
        isBefore=isBefore,
        charaPosition=charaPosition,  # 存储Vec3的字符串格式
        direction=direction,
        missionPassedTag=missionPassedTag
    )

    db.session.add(mission)
    db.session.commit()

    result = {
        'id': mission.id,
        'curMissionIndex': mission.curMissionIndex,
        'isBefore': mission.isBefore,
        'charaPosition': mission.charaPosition,
        'direction': mission.direction,
        'missionPassedTag': mission.missionPassedTag,
        'created_at': mission.created_at.isoformat()
    }

    return jsonify({'message': '关卡添加成功', 'mission': result}), 201


# 更新关卡信息
@mission.route('/missions/<int:curMissionIndex>', methods=['PUT'])
def update_mission(curMissionIndex):
    data = request.get_json()
    mission = Mission.query.filter_by(curMissionIndex=curMissionIndex).first()
    if not mission:
        return jsonify({'message': '关卡未找到'}), 404  # 如果关卡不存在，返回404

    mission.curMissionIndex = data.get('curMissionIndex', mission.curMissionIndex)
    mission.isBefore = data.get('isBefore', mission.isBefore)
    mission.charaPosition = data.get('charaPosition', mission.charaPosition)
    mission.direction = data.get('direction', mission.direction)
    mission.missionPassedTag = data.get('missionPassedTag', mission.missionPassedTag)

    db.session.commit()

    result = {
        'id': mission.id,
        'curMissionIndex': mission.curMissionIndex,
        'isBefore': mission.isBefore,
        'charaPosition': mission.charaPosition,
        'direction': mission.direction,
        'missionPassedTag': mission.missionPassedTag,
        'created_at': mission.created_at.isoformat()
    }

    return jsonify({'message': '关卡更新成功', 'mission': result}), 200


# 删除关卡
@mission.route('/missions/<int:curMissionIndex>', methods=['DELETE'])
def delete_mission(curMissionIndex):
    mission = Mission.query.filter_by(curMissionIndex=curMissionIndex).first()
    if not mission:
        return jsonify({'message': '关卡未找到'}), 404  # 如果关卡不存在，返回404

    db.session.delete(mission)
    db.session.commit()

    return jsonify({'message': '关卡删除成功'}), 200
