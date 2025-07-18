import os
import json
from flask import Flask, jsonify, send_from_directory, request, g
from werkzeug.utils import secure_filename
from .extensions import db, login_manager
from .models import User
from .auth import auth as auth_blueprint
from flask_cors import CORS
from flask_migrate import Migrate
from flask_login import login_required, current_user

# --- Path Definitions ---
APP_ROOT = os.path.dirname(os.path.abspath(__file__))
INSTANCE_FOLDER = os.path.join(APP_ROOT, '..', 'instance')
PUBLIC_FOLDER = os.path.join(APP_ROOT, '..', 'public')
GLOBAL_STATIC_FOLDER = os.path.join(PUBLIC_FOLDER, 'static')
USER_DATA_ROOT = os.path.join(INSTANCE_FOLDER, 'user_data')

# Helper function to get paths for logged-in user
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

# Main Application Factory
def create_app():
    app = Flask(__name__,
                instance_path=INSTANCE_FOLDER,
                static_folder=PUBLIC_FOLDER,
                static_url_path='')

    # --- Configuration ---
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'a_very_secret_key_for_development_12345')
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(INSTANCE_FOLDER, 'database.db')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # Limit upload size to 16MB

    # Ensure instance folder exists
    try:
        os.makedirs(app.instance_path, exist_ok=True)
        os.makedirs(USER_DATA_ROOT, exist_ok=True)
    except OSError:
        pass

    # --- Initialize Extensions ---
    db.init_app(app)
    Migrate(app, db)
    login_manager.init_app(app)
    CORS(app, supports_credentials=True, origins=["http://localhost:5000", "http://127.0.0.1:5000"])

    # --- Register Blueprints ---
    app.register_blueprint(auth_blueprint)

    # --- Helper functions to combine global and user data ---
    def get_combined_json_files(subfolder):
        results = []
        global_path = get_global_path(subfolder)
        if os.path.exists(global_path):
            for f in os.listdir(global_path):
                if f.endswith('.json'):
                    results.append({'name': f.replace('.json', ''), 'is_global': True})
        
        user_path = get_user_path(subfolder)
        user_files = set()
        if user_path and os.path.exists(user_path):
             for f in os.listdir(user_path):
                if f.endswith('.json'):
                    user_files.add(f.replace('.json', ''))
        
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
        user_files = set()
        if user_path and os.path.exists(user_path):
            for f in os.listdir(user_path):
                if f.lower().endswith(audio_ext):
                    user_files.add(f)
        
        global_names = {item['name'] for item in results}
        for name in user_files:
            if name not in global_names:
                results.append({'name': name, 'is_global': False})
        return sorted(results, key=lambda x: x['name'])

    # --- API Routes ---
    @app.route('/api/get-audio-files')
    @login_required
    def get_audio_files_api():
        return jsonify({
            'mainsound': get_combined_audio_files('mainsound'),
            'plussound': get_combined_audio_files('plussound')
        })

    @app.route('/api/soundsets', methods=['GET'])
    @login_required
    def get_soundsets():
        return jsonify(get_combined_json_files('soundset'))

    @app.route('/api/controlsets', methods=['GET'])
    @login_required
    def get_controlsets():
        return jsonify(get_combined_json_files('controlset'))

    @app.route('/api/soundsets/<name>', methods=['GET'])
    @login_required
    def get_soundset_by_name(name):
        user_path = get_user_path('soundset')
        file_path = os.path.join(user_path, f"{name}.json")
        if os.path.exists(file_path):
            return send_from_directory(user_path, f"{name}.json")
        
        global_path = get_global_path('soundset')
        file_path_global = os.path.join(global_path, f"{name}.json")
        if os.path.exists(file_path_global):
            return send_from_directory(global_path, f"{name}.json")
        return jsonify({'error': 'Soundset not found'}), 404
        
    @app.route('/api/soundsets', methods=['POST', 'PUT'])
    @login_required
    def save_or_update_soundset():
        data = request.json
        name = data.get('name')
        if not name: return jsonify({'error': 'Soundset name is required'}), 400
        
        # Prevent users from overwriting global sets
        global_path = get_global_path('soundset')
        if os.path.exists(os.path.join(global_path, f"{name}.json")):
            return jsonify({'error': 'Cannot modify a global soundset.'}), 403

        user_path = get_user_path('soundset')
        file_path = os.path.join(user_path, f"{name}.json")
        
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
        return jsonify({'message': f'Soundset {name} saved successfully'})

    @app.route('/api/soundsets', methods=['DELETE'])
    @login_required
    def delete_soundset():
        name = request.json.get('name')
        if not name: return jsonify({'error': 'Name is required'}), 400

        # Check if it's a global set first
        global_path = get_global_path('soundset')
        if os.path.exists(os.path.join(global_path, f"{name}.json")):
            return jsonify({'error': 'Cannot delete a global soundset'}), 403

        user_path = get_user_path('soundset')
        file_path = os.path.join(user_path, f"{name}.json")
        if os.path.exists(file_path):
            os.remove(file_path)
            return jsonify({'message': f'Soundset {name} deleted successfully'})
        return jsonify({'error': 'Soundset not found'}), 404

    @app.route('/api/controlsets/<name>', methods=['GET'])
    @login_required
    def get_controlset_by_name(name):
        user_path = get_user_path('controlset')
        file_path = os.path.join(user_path, f"{name}.json")
        if os.path.exists(file_path):
            return send_from_directory(user_path, f"{name}.json")

        global_path = get_global_path('controlset')
        file_path_global = os.path.join(global_path, f"{name}.json")
        if os.path.exists(file_path_global):
            return send_from_directory(global_path, f"{name}.json")
        return jsonify({'error': 'Controlset not found'}), 404

    @app.route('/api/controlsets', methods=['POST'])
    @login_required
    def save_controlset():
        data = request.json
        name = data.get('name')
        settings = data.get('settings')
        if not name or not settings: return jsonify({'error': 'Name and settings are required'}), 400
        
        global_path = get_global_path('controlset')
        if os.path.exists(os.path.join(global_path, f"{name}.json")):
            return jsonify({'error': 'Cannot modify a global controlset.'}), 403

        user_path = get_user_path('controlset')
        file_path = os.path.join(user_path, f"{name}.json")
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(settings, f, ensure_ascii=False, indent=4)
        return jsonify({'message': f'Controlset {name} saved successfully'})

    @app.route('/api/controlsets', methods=['DELETE'])
    @login_required
    def delete_controlset():
        name = request.json.get('name')
        if not name: return jsonify({'error': 'Name is required'}), 400

        global_path = get_global_path('controlset')
        if os.path.exists(os.path.join(global_path, f"{name}.json")):
            return jsonify({'error': 'Cannot delete a global controlset'}), 403
            
        user_path = get_user_path('controlset')
        file_path = os.path.join(user_path, f"{name}.json")
        if os.path.exists(file_path):
            os.remove(file_path)
            # Also check if it was the default and clear it
            default_file = os.path.join(user_path, 'default.txt')
            if os.path.exists(default_file):
                with open(default_file, 'r', encoding='utf-8') as f:
                    if f.read() == name:
                        os.remove(default_file)
            return jsonify({'message': f'Controlset {name} deleted successfully'})
        return jsonify({'error': 'Controlset not found'}), 404

    @app.route('/api/controlsets/default', methods=['GET', 'POST'])
    @login_required
    def handle_default_controlset():
        user_path = get_user_path('controlset')
        default_file = os.path.join(user_path, 'default.txt')
        
        if request.method == 'GET':
            if os.path.exists(default_file):
                with open(default_file, 'r', encoding='utf-8') as f:
                    return jsonify({'default': f.read()})
            return jsonify({'default': '默认配置'}) # Global default
            
        if request.method == 'POST':
            name = request.json.get('name')
            with open(default_file, 'w', encoding='utf-8') as f:
                f.write(name)
            return jsonify({'message': f'Set {name} as default successfully'})

    @app.route('/api/upload/<track_type>', methods=['POST'])
    @login_required
    def upload_audio(track_type):
        if track_type not in ['mainsound', 'plussound']:
            return jsonify({'error': '无效的音轨类型'}), 400
        if 'file' not in request.files:
            return jsonify({'error': '没有文件部分'}), 400
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': '没有选择文件'}), 400
        if file:
            filename = secure_filename(file.filename)
            global_file_path = os.path.join(get_global_path(track_type), filename)
            if os.path.exists(global_file_path):
                return jsonify({'error': f'无法上传，全局目录中已存在同名文件'}), 409
            
            upload_path = get_user_path(track_type)
            file.save(os.path.join(upload_path, filename))
            return jsonify({'message': '文件上传成功', 'filename': filename})
        return jsonify({'error': '文件上传失败'}), 500

    @app.route('/api/delete-audio/<track_type>/<filename>', methods=['DELETE'])
    @login_required
    def delete_audio(track_type, filename):
        if track_type not in ['mainsound', 'plussound']:
            return jsonify({'error': '无效的音轨类型'}), 400
        
        safe_filename = secure_filename(filename)
        global_file_path = os.path.join(get_global_path(track_type), safe_filename)
        if os.path.exists(global_file_path):
            return jsonify({'error': '不能删除全局音频文件'}), 403

        user_path = get_user_path(track_type)
        file_to_delete = os.path.join(user_path, safe_filename)
        if os.path.exists(file_to_delete):
            os.remove(file_to_delete)
            return jsonify({'message': '文件删除成功'})
        return jsonify({'error': '文件未找到或您没有权限删除'}), 404

    # --- Serve Frontend Application ---
    @app.route('/', defaults={'path': ''})
    @app.route('/<path:path>')
    def serve(path):
        if path != "" and os.path.exists(os.path.join(app.static_folder, path)):
            return send_from_directory(app.static_folder, path)
        
        if hasattr(g, 'user') and g.user.is_authenticated and path.startswith('static/user/'):
            parts = path.split('/')
            if len(parts) == 4:
                _, _, track_type, filename = parts
                user_audio_path = get_user_path(track_type)
                if os.path.exists(os.path.join(user_audio_path, filename)):
                    return send_from_directory(user_audio_path, filename)
        
        return send_from_directory(app.static_folder, 'index.html')

    return app

# This part is for running locally
if __name__ == '__main__':
    app = create_app()
    app.run(host='0.0.0.0', port=5000, debug=True)