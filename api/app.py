import os
import json
import re
import shutil
from flask import Flask, jsonify, send_from_directory, request, g, abort
from urllib.parse import unquote
from .extensions import db, login_manager
from .models import User, AudioFile # Import the new model
from .auth import auth as auth_blueprint
from flask_cors import CORS
from flask_migrate import Migrate
from flask_login import login_required, current_user
import getpass
# Import our new generator functions
from .generator import generate_noise, process_and_save_track

# --- Path Definitions ---
APP_ROOT = os.path.dirname(os.path.abspath(__file__))
ON_RENDER = os.environ.get('ON_RENDER')
INSTANCE_FOLDER = '/var/data/instance' if ON_RENDER else os.path.join(APP_ROOT, '..', 'instance')
PUBLIC_FOLDER = os.path.join(APP_ROOT, '..', 'public')
GLOBAL_STATIC_FOLDER = os.path.join(PUBLIC_FOLDER, 'static')
SHARED_USER_DATA_ROOT = os.path.join(INSTANCE_FOLDER, 'user_data', 'shared')
USER_CONFIG_ROOT = os.path.join(INSTANCE_FOLDER, 'user_data')

# --- Helper Functions ---
def get_user_config_path(subfolder):
    if hasattr(current_user, 'is_authenticated') and current_user.is_authenticated:
        path = os.path.join(USER_CONFIG_ROOT, current_user.username, subfolder)
        os.makedirs(path, exist_ok=True)
        return path
    return None

def get_shared_audio_path(subfolder):
    path = os.path.join(SHARED_USER_DATA_ROOT, subfolder)
    os.makedirs(path, exist_ok=True)
    return path

def get_global_path(subfolder):
    path = os.path.join(GLOBAL_STATIC_FOLDER, subfolder)
    os.makedirs(path, exist_ok=True)
    return path

def secure_filename_custom(filename):
    filename = filename.replace('..', '').replace('/', '').replace('\\', '').replace(' ', '_')
    filename = re.sub(r'[^\w\s.-]', '', filename, flags=re.UNICODE)
    return filename.strip('_.- ')

# --- Application Factory ---
def create_app():
    app = Flask(__name__, instance_path=INSTANCE_FOLDER, static_folder=PUBLIC_FOLDER, static_url_path='')
    
    app.config.from_mapping(
        SECRET_KEY=os.environ.get('SECRET_KEY', 'a_very_secret_key_for_development_12345'),
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
        MAX_CONTENT_LENGTH=16 * 1024 * 1024
    )
    if ON_RENDER:
        database_url = os.environ.get('DATABASE_URL', '').replace("postgres://", "postgresql://")
        app.config['SQLALCHEMY_DATABASE_URI'] = database_url
    else:
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(INSTANCE_FOLDER, 'database.db')
    
    try:
        os.makedirs(app.instance_path, exist_ok=True)
        os.makedirs(SHARED_USER_DATA_ROOT, exist_ok=True)
    except OSError:
        pass

    db.init_app(app)
    Migrate(app, db)
    login_manager.init_app(app)
    CORS(app, supports_credentials=True, origins=["http://localhost:5000", "http://127.0.0.1:5000", "null"])
    app.register_blueprint(auth_blueprint)

    # --- API Routes ---

    def get_combined_json_files(subfolder):
        results = []
        global_path = get_global_path(subfolder)
        if os.path.exists(global_path):
            for f in os.listdir(global_path):
                if f.endswith('.json'):
                    results.append({'name': f.replace('.json', ''), 'is_global': True})
        user_path = get_user_config_path(subfolder)
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
        # 1. Add all global (protected) files
        global_path = get_global_path(subfolder)
        if os.path.exists(global_path):
            for f in os.listdir(global_path):
                if f.lower().endswith(audio_ext):
                    results.append({'name': f, 'is_global': True})
        
        # 2. Add all shared (community) files
        shared_path = get_shared_audio_path(subfolder)
        if os.path.exists(shared_path):
            for f in os.listdir(shared_path):
                if f.lower().endswith(audio_ext):
                    if not any(r['name'] == f for r in results):
                        results.append({'name': f, 'is_global': False})
        
        return sorted(results, key=lambda x: x['name'])

    @app.route('/api/get-audio-files')
    @login_required
    def get_audio_files_api():
        return jsonify({'mainsound': get_combined_audio_files('mainsound'), 'plussound': get_combined_audio_files('plussound')})

    # --- KEY CHANGE: RESTORING ALL CONFIGURATION ROUTES ---
    @app.route('/api/soundsets', methods=['GET'])
    @login_required
    def get_soundsets(): return jsonify(get_combined_json_files('soundset'))

    @app.route('/api/controlsets', methods=['GET'])
    @login_required
    def get_controlsets(): return jsonify(get_combined_json_files('controlset'))
    
    @app.route('/api/soundsets/<name>', methods=['GET'])
    @login_required
    def get_soundset_by_name(name):
        user_path = get_user_config_path('soundset'); file_path = os.path.join(user_path, f"{name}.json")
        if os.path.exists(file_path): return send_from_directory(user_path, f"{name}.json")
        global_path = get_global_path('soundset'); file_path_global = os.path.join(global_path, f"{name}.json")
        if os.path.exists(file_path_global): return send_from_directory(global_path, f"{name}.json")
        return jsonify({'error': 'Soundset not found'}), 404

    @app.route('/api/controlsets/<name>', methods=['GET'])
    @login_required
    def get_controlset_by_name(name):
        user_path = get_user_config_path('controlset'); file_path = os.path.join(user_path, f"{name}.json")
        if os.path.exists(file_path): return send_from_directory(user_path, f"{name}.json")
        global_path = get_global_path('controlset'); file_path_global = os.path.join(global_path, f"{name}.json")
        if os.path.exists(file_path_global): return send_from_directory(global_path, f"{name}.json")
        return jsonify({'error': 'Controlset not found'}), 404

    @app.route('/api/soundsets', methods=['POST', 'PUT'])
    @login_required
    def save_or_update_soundset():
        data = request.json; name = data.get('name')
        if not name: return jsonify({'error': 'Soundset name is required'}), 400
        write_path = get_global_path('soundset') if current_user.is_admin else get_user_config_path('soundset')
        file_path = os.path.join(write_path, f"{name}.json")
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
        return jsonify({'message': f'Soundset {name} saved successfully'})

    @app.route('/api/soundsets', methods=['DELETE'])
    @login_required
    def delete_soundset():
        name = request.json.get('name')
        if not name: return jsonify({'error': 'Name is required'}), 400
        user_path = get_user_config_path('soundset'); user_file_path = os.path.join(user_path, f"{name}.json")
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
        write_path = get_global_path('controlset') if current_user.is_admin else get_user_config_path('controlset')
        file_path = os.path.join(write_path, f"{name}.json")
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(settings, f, ensure_ascii=False, indent=4)
        return jsonify({'message': f'Controlset {name} saved successfully'})

    @app.route('/api/controlsets', methods=['DELETE'])
    @login_required
    def delete_controlset():
        name = request.json.get('name')
        if not name: return jsonify({'error': 'Name is required'}), 400
        user_path = get_user_config_path('controlset'); user_file_path = os.path.join(user_path, f"{name}.json")
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
        user_path = get_user_config_path('controlset')
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

    # --- Audio File Routes (Community Model) ---
    @app.route('/api/upload/<track_type>', methods=['POST'])
    @login_required
    def upload_audio(track_type):
        if track_type not in ['mainsound', 'plussound']: return jsonify({'error': '无效的音轨类型'}), 400
        if 'file' not in request.files: return jsonify({'error': '没有文件部分'}), 400
        file = request.files['file']
        if file.filename == '': return jsonify({'error': '没有选择文件'}), 400
        if file:
            clean_filename = secure_filename_custom(file.filename)
            if os.path.exists(os.path.join(get_global_path(track_type), clean_filename)):
                return jsonify({'error': '无法上传，已存在同名的受保护文件'}), 409
            upload_path = get_shared_audio_path(track_type)
            file.save(os.path.join(upload_path, clean_filename))
            return jsonify({'message': '文件上传成功', 'filename': clean_filename})
        return jsonify({'error': '文件上传失败'}), 500

    @app.route('/api/delete-audio/<track_type>/<filename>', methods=['DELETE'])
    @login_required
    def delete_audio(track_type, filename):
        safe_filename = secure_filename_custom(filename)
        global_file_path = os.path.join(get_global_path(track_type), safe_filename)
        if os.path.exists(global_file_path):
            if current_user.is_admin:
                os.remove(global_file_path)
                return jsonify({'message': f'受保护的文件 {safe_filename} 已被管理员删除'})
            else:
                return jsonify({'error': '无权删除受保护的文件'}), 403
        shared_file_path = os.path.join(get_shared_audio_path(track_type), safe_filename)
        if os.path.exists(shared_file_path):
            os.remove(shared_file_path)
            return jsonify({'message': f'共享文件 {safe_filename} 已被删除'})
        return jsonify({'error': '文件未找到'}), 404

    @app.route('/api/audio/protect/<track_type>/<filename>', methods=['POST'])
    @login_required
    def protect_audio(track_type, filename):
        if not current_user.is_admin: abort(403)
        safe_filename = secure_filename_custom(filename)
        source_path = os.path.join(get_shared_audio_path(track_type), safe_filename)
        destination_path = os.path.join(get_global_path(track_type), safe_filename)
        if os.path.exists(source_path):
            shutil.move(source_path, destination_path)
            return jsonify({'message': f'文件 {safe_filename} 已被保护。'})
        return jsonify({'error': '共享文件未找到'}), 404

    @app.route('/api/audio/unprotect/<track_type>/<filename>', methods=['POST'])
    @login_required
    def unprotect_audio(track_type, filename):
        if not current_user.is_admin: abort(403)
        safe_filename = secure_filename_custom(filename)
        source_path = os.path.join(get_global_path(track_type), safe_filename)
        destination_path = os.path.join(get_shared_audio_path(track_type), safe_filename)
        if os.path.exists(source_path):
            shutil.move(source_path, destination_path)
            return jsonify({'message': f'文件 {safe_filename} 已取消保护并移回共享库。'})
        return jsonify({'error': '受保护的文件未找到'}), 404

    @app.route('/static-media/<track_type>/<path:filename>')
    def serve_global_file(track_type, filename):
        """
        Serves the protected/global static files from the /public/static directory.
        """
        if track_type not in ['mainsound', 'plussound']:
            abort(404)
        
        global_path = get_global_path(track_type)
        return send_from_directory(global_path, filename)

    @app.route('/api/generate/main-noise', methods=['POST'])
    @login_required
    def generate_main_noise_route():
        try:
            params = request.get_json() or {}
            
            noise_segment = generate_noise(
                duration_s=params.get('duration_s', 30),
                color=params.get('color', 'pink'),
                channels=2,
                tone_cutoff_hz=params.get('tone_cutoff_hz', 8000),
                stereo_width=params.get('stereo_width', 0.8)
            )
            
            temp_filename = process_and_save_track(
                noise_segment, 'mainsound', get_shared_audio_path, params
            )
            
            return jsonify({
                "success": True,
                "filename": temp_filename,
                "message": "主轨噪音已成功生成"
            })
        except Exception as e:
            app.logger.error(f"Error in generate_main_noise_route: {e}", exc_info=True)
            return jsonify({"success": False, "error": "生成音频时发生内部错误"}), 500

    # NEW: API to save the temporary generated track
    @app.route('/api/audio/save-temp', methods=['POST'])
    @login_required
    def save_temp_audio():
        data = request.get_json()
        temp_filename = data.get('temp_filename')
        final_filename = secure_filename_custom(data.get('final_filename'))
        track_type = data.get('track_type')

        if not all([temp_filename, final_filename, track_type]):
            return jsonify({"error": "缺少必要参数"}), 400
        
        # Check for name collision
        if AudioFile.query.filter_by(filename=final_filename, track_type=track_type).first():
            return jsonify({'error': '已存在同名音频文件'}), 409

        temp_path = os.path.join(get_shared_audio_path(track_type), temp_filename)
        final_path = os.path.join(get_shared_audio_path(track_type), final_filename)

        if os.path.exists(temp_path):
            os.rename(temp_path, final_path)
            
            new_audio = AudioFile(
                filename=final_filename,
                track_type=track_type,
                is_global=False,
                user_id=current_user.id
            )
            db.session.add(new_audio)
            db.session.commit()
            return jsonify({"success": True, "message": "音频已成功保存到音乐库"})
        
        return jsonify({"error": "临时文件未找到"}), 404
    
    # --- File Serving Routes ---
    @app.route('/media/shared/<track_type>/<path:filename>')
    def serve_shared_file(track_type, filename):
        if track_type not in ['mainsound', 'plussound']: abort(404)
        shared_path = get_shared_audio_path(track_type)
        return send_from_directory(shared_path, filename)

    @app.route('/', defaults={'path': ''})
    @app.route('/<path:path>')
    def serve(path):
        if path != "" and os.path.exists(os.path.join(app.static_folder, path)):
            return send_from_directory(app.static_folder, path)
        return send_from_directory(app.static_folder, 'index.html')
            
    # --- CLI Command ---
    @app.cli.command("set-admin")
    def set_admin_command():
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