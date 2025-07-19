import os
from flask import Blueprint, request, jsonify, g
from flask_login import login_user, logout_user, login_required, current_user
from .models import User
from .extensions import db

auth = Blueprint('auth', __name__, url_prefix='/auth')

@auth.before_app_request
def before_request():
    g.user = current_user

@auth.route('/register', methods=['POST'])
def register():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')

    if not username or not password:
        return jsonify({'error': '用户名和密码不能为空'}), 400

    if User.query.filter_by(username=username).first():
        return jsonify({'error': '该用户名已被注册'}), 409

    new_user = User(username=username)
    new_user.set_password(password)
    db.session.add(new_user)
    db.session.commit()

    from .app import USER_DATA_ROOT
    user_dir = os.path.join(USER_DATA_ROOT, username)
    try:
        os.makedirs(os.path.join(user_dir, 'controlset'), exist_ok=True)
        os.makedirs(os.path.join(user_dir, 'soundset'), exist_ok=True)
        os.makedirs(os.path.join(user_dir, 'mainsound'), exist_ok=True)
        os.makedirs(os.path.join(user_dir, 'plussound'), exist_ok=True)
    except OSError as e:
        return jsonify({'error': '无法创建用户目录', 'details': str(e)}), 500

    return jsonify({'message': '用户创建成功'}), 201

@auth.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')
    user = User.query.filter_by(username=username).first()

    if not user or not user.check_password(password):
        return jsonify({'error': '用户名或密码无效'}), 401

    login_user(user, remember=True)
    # KEY CHANGE: Add 'is_admin' to the login response
    return jsonify({'message': '登录成功', 'username': user.username, 'is_admin': user.is_admin})

@auth.route('/logout', methods=['POST'])
@login_required
def logout():
    logout_user()
    return jsonify({'message': '已成功登出'})

@auth.route('/status')
def status():
    if current_user.is_authenticated:
        # KEY CHANGE: Add 'is_admin' to the status response
        return jsonify({'logged_in': True, 'username': current_user.username, 'is_admin': current_user.is_admin})
    return jsonify({'logged_in': False})