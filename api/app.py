import os
import json
import re # 正则表达式模块
from flask import Flask, jsonify, send_from_directory, request, g
from werkzeug.utils import secure_filename # 导入原始函数作为参考
from .extensions import db, login_manager
from .models import User
from .auth import auth as auth_blueprint
from flask_cors import CORS
from flask_migrate import Migrate
from flask_login import login_required, current_user
import getpass
from urllib.parse import unquote

# --- Path Definitions ---
APP_ROOT = os.path.dirname(os.path.abspath(__file__))
ON_RENDER = os.environ.get('ON_RENDER')
if ON_RENDER:
    INSTANCE_FOLDER = '/var/data/instance'
else:
    INSTANCE_FOLDER = os.path.join(APP_ROOT, '..', 'instance')
PUBLIC_FOLDER = os.path.join(APP_ROOT, '..', 'public')
GLOBAL_STATIC_FOLDER = os.path.join(PUBLIC_FOLDER, 'static')
USER_DATA_ROOT = os.path.join(INSTANCE_FOLDER, 'user_data')

# --- Helper Functions ---
def get_user_path(subfolder):
    if hasattr(g, 'user') and g.user.is_authenticated:
        path = os.path.join(USER_DATA_ROOT, g.user.username, subfolder)
        os.makedirs(path, exist_ok=True)
        return path
    return None

def get_global_path(subfolder):
    path = os.path.join(GLOBAL_STATIC_FOLDER, subfolder)
    os.makedirs(path, exist_ok=True)
    return path

def secure_filename_custom(filename):
    """
    A custom secure_filename function that supports Unicode characters
    but still prevents directory traversal attacks.
    """
    # 移除所有可能用于路径遍历的字符: / \ ..
    filename = filename.replace('..', '')
    filename = filename.replace('/', '')
    filename = filename.replace('\\', '')
    
    # 将空格替换为下划线
    filename = filename.replace(' ', '_')
    
    # 使用正则表达式移除其他不推荐的字符，但保留字母、数字、下划线、减号、点和中文字符
    # \w 匹配 [a-zA-Z0-9_]
    # \u4e00-\u9fa5 是中文字符的 Unicode 范围
    filename = re.sub(r'[^\w\s.-]', '', filename, flags=re.UNICODE)
    
    # 清理文件名首尾可能多余的字符
    return filename.strip('_.- ')

# --- Application Factory ---
def create_app():
    app = Flask(__name__,
                instance_path=INSTANCE_FOLDER,
                static_folder=PUBLIC_FOLDER,
                static_url_path='')

    # --- Configuration ---
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'a_very_secret_key_for_development_12345')
    if ON_RENDER:
        database_url = os.environ.get('DATABASE_URL')
        if database_url:
            database_url = database_url.replace("postgres://", "postgresql://")
        app.config['SQLALCHEMY_DATABASE_URI'] = database_url
    else:
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(INSTANCE_FOLDER, 'database.db')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024

    try:
        os.makedirs(app.instance_path, exist_ok=True)
        os.makedirs(USER_DATA_ROOT, exist_ok=True)
    except OSError:
        pass

    db.init_app(app)
    Migrate(app, db)
    login_manager.init_app(app)
    CORS(app, supports_credentials=True, origins=["http://localhost:5000", "http://127.0.0.1:5000", "null"])
    app.register_blueprint(auth_blueprint)

    # --- Combined Data Reading (GET requests) ---
    def get_combined_json_files(subfolder):
        results = []
        global_path = get_global_path(subfolder)
        if os.path.exists(global_path):
            for f in os.listdir(global_path):
                if f.endswith('.json'):
                    results.append({'name': f.replace('.json', ''), 'is_global': True})
        user_path = get_user_path(subfolder)
        if user_path and os.path.exists(user_path):
            user_files = {f.replace('.json', '') for f in os.listdir(user_path) if f.endswith('.json')}
            global_names = {item['name'] for item in results}
            for name in user_files:
                if name not in global_names:
                    results.append({'name': name, 'is_global': False})
        return sorted(results, key=lambda x: x['name'])

    def get_combined_audio_files(subfolder):
        audio_ext = ('.wav', '.mp3', '.ogg')
        results = []
        global_path = get_global_path(subfolder)
        if os.path.exists(global_path):
            for f in os.listdir(global_path):
                if f.lower().endswith(audio_ext):
                    results.append({'name': f, 'is_global': True})
        user_path = get_user_path(subfolder)
        if user_path and os.path.exists(user_path):
            user_files = {f for f in os.listdir(user_path) if f.lower().endswith(audio_ext)}
            global_names = {item['name'] for item in results}
            for name in user_files:
                if name not in global_names:
                    results.append({'name': name, 'is_global': False})
        return sorted(results, key=lambda x: x['name'])
    
    # --- Read-Only API Routes ---
    @app.route('/api/get-audio-files')
    @login_required
    def get_audio_files_api(): return jsonify({'mainsound': get_combined_audio_files('mainsound'), 'plussound': get_combined_audio_files('plussound')})

    @app.route('/api/soundsets', methods=['GET'])
    @login_required
    def get_soundsets(): return jsonify(get_combined_json_files('soundset'))

    @app.route('/api/controlsets', methods=['GET'])
    @login_required
    def get_controlsets(): return jsonify(get_combined_json_files('controlset'))
    
    @app.route('/api/soundsets/<name>', methods=['GET'])
    @login_required
    def get_soundset_by_name(name):
        user_path = get_user_path('soundset'); file_path = os.path.join(user_path, f"{name}.json")
        if os.path.exists(file_path): return send_from_directory(user_path, f"{name}.json")
        global_path = get_global_path('soundset'); file_path_global = os.path.join(global_path, f"{name}.json")
        if os.path.exists(file_path_global): return send_from_directory(global_path, f"{name}.json")
        return jsonify({'error': 'Soundset not found'}), 404

    @app.route('/api/controlsets/<name>', methods=['GET'])
    @login_required
    def get_controlset_by_name(name):
        user_path = get_user_path('controlset'); file_path = os.path.join(user_path, f"{name}.json")
        if os.path.exists(file_path): return send_from_directory(user_path, f"{name}.json")
        global_path = get_global_path('controlset'); file_path_global = os.path.join(global_path, f"{name}.json")
        if os.path.exists(file_path_global): return send_from_directory(global_path, f"{name}.json")
        return jsonify({'error': 'Controlset not found'}), 404

    # --- Write API Routes ---
    @app.route('/api/soundsets', methods=['POST', 'PUT'])
    @login_required
    def save_or_update_soundset():
        data = request.json; name = data.get('name')
        if not name: return jsonify({'error': 'Soundset name is required'}), 400
        if current_user.is_admin:
            write_path = get_global_path('soundset')
        else:
            write_path = get_user_path('soundset')
        file_path = os.path.join(write_path, f"{name}.json")
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
        return jsonify({'message': f'Soundset {name} saved successfully'})

    @app.route('/api/soundsets', methods=['DELETE'])
    @login_required
    def delete_soundset():
        name = request.json.get('name')
        if not name: return jsonify({'error': 'Name is required'}), 400
        user_path = get_user_path('soundset'); user_file_path = os.path.join(user_path, f"{name}.json")
        if os.path.exists(user_file_path):
            os.remove(user_file_path)
            return jsonify({'message': f'User soundset {name} deleted successfully'})
        if current_user.is_admin:
            global_path = get_global_path('soundset'); global_file_path = os.path.join(global_path, f"{name}.json")
            if os.path.exists(global_file_path):
                os.remove(global_file_path)
                return jsonify({'message': f'Global soundset {name} deleted successfully'})
        return jsonify({'error': 'Soundset not found or permission denied'}), 404
    
    @app.route('/api/controlsets', methods=['POST'])
    @login_required
    def save_controlset():
        data = request.json; name = data.get('name'); settings = data.get('settings')
        if not name or not settings: return jsonify({'error': 'Name and settings are required'}), 400
        if current_user.is_admin:
            write_path = get_global_path('controlset')
        else:
            write_path = get_user_path('controlset')
        file_path = os.path.join(write_path, f"{name}.json")
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(settings, f, ensure_ascii=False, indent=4)
        return jsonify({'message': f'Controlset {name} saved successfully'})

    @app.route('/api/controlsets', methods=['DELETE'])
    @login_required
    def delete_controlset():
        name = request.json.get('name')
        if not name: return jsonify({'error': 'Name is required'}), 400
        user_path = get_user_path('controlset'); user_file_path = os.path.join(user_path, f"{name}.json")
        if os.path.exists(user_file_path):
            os.remove(user_file_path)
            return jsonify({'message': f'User controlset {name} deleted successfully'})
        if current_user.is_admin:
            global_path = get_global_path('controlset'); global_file_path = os.path.join(global_path, f"{name}.json")
            if os.path.exists(global_file_path):
                os.remove(global_file_path)
                return jsonify({'message': f'Global controlset {name} deleted successfully'})
        return jsonify({'error': 'Controlset not found or permission denied'}), 404

    @app.route('/api/controlsets/default', methods=['GET', 'POST'])
    @login_required
    def handle_default_controlset():
        user_path = get_user_path('controlset')
        if not user_path: return jsonify({'error': 'User context not found'}), 500
        default_file = os.path.join(user_path, 'default.txt')
        if request.method == 'GET':
            if os.path.exists(default_file):
                with open(default_file, 'r', encoding='utf-8') as f:
                    return jsonify({'default': f.read().strip()})
            else:
                return jsonify({'default': '默认配置'})
        if request.method == 'POST':
            name = request.json.get('name')
            if not name: return jsonify({'error': 'Name is required to set default'}), 400
            with open(default_file, 'w', encoding='utf-8') as f:
                f.write(name)
            return jsonify({'message': f'Set {name} as default successfully'})
        
    @app.route('/api/upload/<track_type>', methods=['POST'])
    @login_required
    def upload_audio(track_type):
        if track_type not in ['mainsound', 'plussound']: return jsonify({'error': '无效的音轨类型'}), 400
        if 'file' not in request.files: return jsonify({'error': '没有文件部分'}), 400
        file = request.files['file']
        if file.filename == '': return jsonify({'error': '没有选择文件'}), 400
        if file:
            filename = secure_filename_custom(file.filename)
            if current_user.is_admin:
                upload_path = get_global_path(track_type)
            else:
                upload_path = get_user_path(track_type)
                global_file_path = os.path.join(get_global_path(track_type), filename)
                if os.path.exists(global_file_path):
                    return jsonify({'error': f'无法上传，全局目录中已存在同名文件'}), 409
            file.save(os.path.join(upload_path, filename))
            return jsonify({'message': '文件上传成功', 'filename': filename})
        return jsonify({'error': '文件上传失败'}), 500

    @app.route('/api/delete-audio/<track_type>/<filename>', methods=['DELETE'])
    @login_required
    def delete_audio(track_type, filename):
        if track_type not in ['mainsound', 'plussound']: return jsonify({'error': '无效的音轨类型'}), 400
        safe_filename = secure_filename_custom(filename)
        user_path = get_user_path(track_type); user_file_path = os.path.join(user_path, safe_filename)
        if os.path.exists(user_file_path):
            os.remove(user_file_path)
            return jsonify({'message': f'User audio file {safe_filename} deleted successfully'})
        if current_user.is_admin:
            global_path = get_global_path(track_type); global_file_path = os.path.join(global_path, safe_filename)
            if os.path.exists(global_file_path):
                os.remove(global_file_path)
                return jsonify({'message': f'Global audio file {safe_filename} deleted successfully'})
        return jsonify({'error': 'File not found or permission denied'}), 404

    # --- Serve Frontend and CLI ---
    @app.route('/', defaults={'path': ''})
    @app.route('/<path:path>')
    def serve(path):
        # 优先服务 /public 目录下的静态文件，如 style.css, script.js
        if path != "" and os.path.exists(os.path.join(app.static_folder, path)):
            return send_from_directory(app.static_folder, path)

        if hasattr(g, 'user') and g.user.is_authenticated and path.startswith('static/user/'):
            parts = path.split('/')
            if len(parts) == 4:
                _, _, track_type, raw_filename = parts
                
                # KEY CHANGE: Decode the filename from URL encoding back to Unicode
                filename = unquote(raw_filename)
                
                user_folder_path = get_user_path(track_type)
                
                if user_folder_path and os.path.exists(os.path.join(user_folder_path, filename)):
                    return send_from_directory(user_folder_path, filename)
        
        return send_from_directory(app.static_folder, 'index.html')
            
    @app.cli.command("set-admin")
    def set_admin_command():
        """Creates a new admin user or promotes an existing user and sets their password."""
        username = input("Enter username to make admin: ")
        password = getpass.getpass("Enter a new password for this admin (leave blank to not change): ")
        user = User.query.filter_by(username=username).first()
        if user:
            print(f"User '{username}' found. Promoting to admin...")
            user.is_admin = True
            if password:
                user.set_password(password)
                print("Password has been updated.")
            db.session.commit()
            print(f"User '{username}' is now an admin.")
        else:
            print(f"User '{username}' not found. Creating a new admin user...")
            if not password:
                print("Error: A password is required for a new user.")
                return
            admin_user = User(username=username, is_admin=True)
            admin_user.set_password(password)
            db.session.add(admin_user)
            db.session.commit()
            print(f"Admin user '{username}' created successfully.")

    return app

if __name__ == '__main__':
    app = create_app()
    app.run(host='0.0.0.0', port=5000, debug=True)