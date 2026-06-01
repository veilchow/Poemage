from app.learndata import learndata
from app.libs.extensions import db
# 引入相关模型
from app.models import LearnData
from flask_login import login_required, current_user
from flask import request, json, jsonify, redirect, session, make_response, Response


# 上传 user_id，返回该 user_id 的所有学习数据信息
@learndata.route('/learndata/<int:user_id>/all', methods=['GET'])
def get_all_learndata(user_id):
    learndata_record = LearnData.query.filter_by(user_id=user_id).first()
    if not learndata_record:
        return jsonify({"message": "学习数据为空"}), 404

    result = {
        "id": learndata_record.id,
        "user_id": learndata_record.user_id,
        "poem_data": learndata_record.poem_data,  # 所有诗歌数据直接返回
        "created_at": learndata_record.created_at.isoformat()
    }

    return jsonify(result), 200



# 根据 user_id 和 poem_id 获取某一诗歌的详细得分数据
@learndata.route('/learndata/<int:user_id>/<int:poem_id>', methods=['GET'])
def get_poem_detail(user_id, poem_id):
    learn_data = LearnData.query.filter_by(user_id=user_id).first()
    if not learn_data or not learn_data.poem_data:
        return jsonify({"message": "未找到学习数据"}), 404
    
    poem_detail = next(
        (item for item in learn_data.poem_data 
         if item.get('poem_id') == poem_id), 
        None
    )
    
    if not poem_detail:
        return jsonify({"message": "未找到该诗歌的学习数据"}), 404
    
    return jsonify({
        "poem_id": poem_detail['poem_id'],
        "grade": poem_detail['grade'],
        "content": poem_detail['content']
    }), 200


@learndata.route('/learndata/<int:user_id>/<int:poem_id>', methods=['POST'])
def update_poem_detail(user_id, poem_id):
    # 1. 获取并验证请求数据
    data = request.get_json()
    if not data:
        return jsonify({"message": "请求数据必须为JSON格式"}), 400

    required_fields = ['grade', 'content']
    if any(field not in data for field in required_fields):
        return jsonify({"message": f"缺少必要字段: grade 或 content"}), 400

    # 2. 查询或创建学习数据记录
    learn_data = LearnData.query.filter_by(user_id=user_id).first()
    if not learn_data:
        learn_data = LearnData(
            user_id=user_id,
            poem_data=[{
                "poem_id": poem_id,
                "grade": data['grade'],
                "content": data['content']
            }]
        )
        db.session.add(learn_data)
    else:
        # 3. 创建全新的列表副本（关键步骤）
        new_poem_data = []
        updated = False
        
        # 复制原数据并检查是否需要更新
        if learn_data.poem_data:
            for item in learn_data.poem_data:
                if item.get('poem_id') == poem_id:
                    # 替换匹配的元素为新数据
                    new_poem_data.append({
                        "poem_id": poem_id,
                        "grade": data['grade'],
                        "content": data['content']
                    })
                    updated = True
                else:
                    # 直接复制其他不相关的元素
                    new_poem_data.append(item)
        
        # 如果未找到匹配项，添加新数据
        if not updated:
            new_poem_data.append({
                "poem_id": poem_id,
                "grade": data['grade'],
                "content": data['content']
            })
        
        # 4. 显式赋值全新的列表（触发SQLAlchemy变更检测）
        learn_data.poem_data = new_poem_data

    # 5. 提交变更
    try:
        db.session.commit()
        db.session.refresh(learn_data)  # 确保获取最新数据
        return jsonify({
            "message": "诗歌元素添加/更新成功",
            "poem_id": poem_id,
            "grade": data['grade'],
            "content": data['content'],
        }), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"message": f"数据库错误: {str(e)}"}), 500


# 批量获取多个诗歌的grade数据
@learndata.route('/learndata/<int:user_id>/poem_ids', methods=['POST'])
def get_multiple_poem_grades(user_id):
    data = request.get_json()
    if not data or not isinstance(data.get('poem_ids'), list):
        return jsonify({"message": "需要提供poem_ids数组"}), 400
    
    learn_data = LearnData.query.filter_by(user_id=user_id).first()
    if not learn_data or not learn_data.poem_data:
        return jsonify({"message": "未找到学习数据"}), 404
    
    poem_ids_set = set(data['poem_ids'])
    result = []
    missing_ids = []
    
    for poem_id in data['poem_ids']:
        item = next(
            (x for x in learn_data.poem_data 
             if x.get('poem_id') == poem_id),
            None
        )
        if item:
            result.append({
                "poem_id": poem_id,
                "grade": item['grade']
            })
        else:
            missing_ids.append(poem_id)
    
    return jsonify({
        "data": result,
        "missing_ids": missing_ids
    }), 200
