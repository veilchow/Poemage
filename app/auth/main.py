from app.auth import auth
from app.libs.extensions import db
# 引入 User 模型
from app.models import User
from flask_login import login_user, current_user, logout_user
from flask import request, jsonify, redirect, session, make_response, Response


@auth.route('/login', methods=['POST'])
def login():
    """登录视图"""
    data = request.get_json()
    username = data['username']
    password = data['password']
    # 查询用户信息
    user = User.query.filter_by(username=username).first()
    if not user:
        return jsonify({'message': '用户名不存在'}), 401
    elif not user.check_password(password):
        return jsonify({'message': '用户名或密码错误'}), 402
    # 登录逻辑
    # 配置 session 的 permanent 的值为 True
    # 使 PERMANENT_SESSION_LIFETIME 配置项生效
    session.permanent = True
    # 数据校验通过，执行 login_user 方法
    login_user(user)
    # 保存cookie
    resp = make_response()
    resp.set_cookie('username', username)
    return jsonify({'message': '登录成功', 'user_id': user.id}), 200


@auth.route('/logout')
def logout():
    """登出视图"""
    # 如果是未登录用户访问
    if not current_user.is_authenticated:
        return jsonify({'message': '并未登录'}), 403
    logout_user()
    # 删除cookie
    resp = make_response()
    resp.delete_cookie('username')
    return jsonify({'message': '已登出'}), 201


@auth.route('/register', methods=['POST'])
def register():
    """注册视图"""
    data = request.get_json()
    username = data['username']
    password = data['password']
    # 查询用户信息
    if User.query.filter_by(username=username).first():
        return jsonify({'message': '用户名已存在'}), 404

    user = User(username=username, password=password)
    db.session.add(user)
    db.session.commit()
    return jsonify({'message': '注册成功', 'user_id': user.id}), 202
