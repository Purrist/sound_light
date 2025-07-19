import os
import json
import re
import shutil
from flask import Flask, jsonify, send_from_directory, request, g, abort
from urllib.parse import unquote
from .extensions import db, login_manager
from .models import User, AudioFile
from .auth import auth as auth_blueprint
from flask_cors import CORS
from flask_migrate import Migrate
from flask_login import login_required, current_user
import getpass
from .generator import generate_noise, process_and_save_track

# --- Path Definitions ---
APP_ROOT = os.path.dirname(os.path.abspath(__file__))
INSTANCE_FOLDER = os.path.join(APP_ROOT, '..', 'instance')
PUBLIC_FOLDER = os.path.join(APP_ROOT, '..', 'public')
AUDIO_STORAGE_ROOT = os.path.join(INSTANCE_FOLDER, 'audio')
USER_CONFIG_ROOT = os.path.join(INSTANCE_FOLDER, 'user_data')
# We keep a reference to static for built-in files, but no new data goes here.
BUILT_IN_STATIC_FOLDER = os.path.join(PUBLIC_FOLDER, 'static')

# --- Helper Functions ---
def get_user_config_path(subfolder):
    if hasattr(current_user, 'is_authenticated') and current_user.is_authenticated:
        path = os.path.join(USER_CONFIG_ROOT, current_user.username, subfolder)
        os.makedirs(path, exist_ok=True); return path
    return None

def get_audio_storage_path(subfolder):
    path = os.path.join(AUDIO_STORAGE_ROOT, subfolder)
    os.makedirs(path, exist_ok=True); return path

def get_built_in_static_path(subfolder):
    path = os.path.join(BUILT_IN_STATIC_FOLDER, subfolder)
    os.makedirs(path, exist_ok=True); return path

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
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(INSTANCE_FOLDER, 'database.db')
    try:
        os.makedirs(app.instance_path, exist_ok=True)
        os.makedirs(AUDIO_STORAGE_ROOT, exist_ok=True)
    except OSError: pass

    db.init_app(app); Migrate(app, db); login_manager.init_app(app);
    CORS(app, supports_credentials=True, origins=["http://localhost:5000", "http://127.0.0.1:5000", "null"])
    app.register_blueprint(auth_blueprint)

    # --- API Routes ---

    def get_combined_audio_files(subfolder):
        results = []
        all_audio = AudioFile.query.filter_by(track_type=subfolder).all()
        for audio in all_audio:
            results.append({
                'name': audio.filename,
                'is_global': audio.is_global,
                'uploader': audio.uploader.username
            })
        return sorted(results, key=lambda x: x['name'])

    @app.route('/api/get-audio-files')
    @login_required
    def get_audio_files_api():
        return jsonify({
            'mainsound': get_combined_audio_files('mainsound'),
            'plussound': get_combined_audio_files('plussound'),
            'mix_elements': get_combined_audio_files('mix_elements')
        })

    @app.route('/api/upload/<track_type>', methods=['POST'])
    @login_required
    def upload_audio(track_type):
        if track_type not in ['mainsound', 'plussound', 'mix_elements']: return jsonify({'error': '无效的音轨类型'}), 400
        if 'file' not in request.files: return jsonify({'error': '没有文件部分'}), 400
        file = request.files['file']
        if file.filename == '': return jsonify({'error': '没有选择文件'}), 400
        clean_filename = secure_filename_custom(file.filename)
        if AudioFile.query.filter_by(filename=clean_filename, track_type=track_type).first():
            return jsonify({'error': '已存在同名音频文件'}), 409
        
        upload_path = get_audio_storage_path(track_type)
        file.save(os.path.join(upload_path, clean_filename))
        new_audio = AudioFile(filename=clean_filename, track_type=track_type, is_global=current_user.is_admin, user_id=current_user.id)
        db.session.add(new_audio)
        db.session.commit()
        return jsonify({'message': '文件上传成功', 'filename': clean_filename})

    @app.route('/api/delete-audio/<track_type>/<filename>', methods=['DELETE'])
    @login_required
    def delete_audio(track_type, filename):
        safe_filename = secure_filename_custom(filename)
        audio_file = AudioFile.query.filter_by(filename=safe_filename, track_type=track_type).first()
        if not audio_file: return jsonify({'error': '文件元数据未找到'}), 404
        if audio_file.is_global and not current_user.is_admin: return jsonify({'error': '无权删除受保护的文件'}), 403
        
        file_path = os.path.join(get_audio_storage_path(track_type), safe_filename)
        if os.path.exists(file_path): os.remove(file_path)
        db.session.delete(audio_file)
        db.session.commit()
        return jsonify({'message': f'文件 {safe_filename} 已被删除'})

    @app.route('/api/audio/protect/<track_type>/<filename>', methods=['POST'])
    @login_required
    def protect_audio(track_type, filename):
        if not current_user.is_admin: abort(403)
        safe_filename = secure_filename_custom(filename)
        audio_file = AudioFile.query.filter_by(filename=safe_filename, track_type=track_type).first()
        if audio_file:
            audio_file.is_global = True
            db.session.commit()
            return jsonify({'message': f'文件 {safe_filename} 已被保护。'})
        return jsonify({'error': '文件元数据未找到'}), 404
        
    @app.route('/api/audio/unprotect/<track_type>/<filename>', methods=['POST'])
    @login_required
    def unprotect_audio(track_type, filename):
        if not current_user.is_admin: abort(403)
        safe_filename = secure_filename_custom(filename)
        audio_file = AudioFile.query.filter_by(filename=safe_filename, track_type=track_type).first()
        if audio_file:
            audio_file.is_global = False
            db.session.commit()
            return jsonify({'message': f'文件 {safe_filename} 已取消保护。'})
        return jsonify({'error': '文件元数据未找到'}), 404
        
    @app.route('/api/generate/main-noise', methods=['POST'])
    @login_required
    def generate_main_noise_route():
        try:
            params = request.get_json() or {}
            noise_segment = generate_noise(
                duration_s=params.get('duration_s', 30),
                color=params.get('color', 'pink'),
                tone_cutoff_hz=params.get('tone_cutoff_hz', 8000),
                stereo_width=params.get('stereo_width', 0.8)
            )
            temp_filename = process_and_save_track(noise_segment, 'mainsound', get_shared_audio_path, params)
            return jsonify({"success": True, "filename": temp_filename})
        except Exception as e:
            app.logger.error(f"Error generating noise: {e}", exc_info=True)
            return jsonify({"success": False, "error": "生成音频时发生内部错误"}), 500

    @app.route('/api/audio/save-temp', methods=['POST'])
    @login_required
    def save_temp_audio():
        data = request.get_json()
        temp_filename = data.get('temp_filename')
        final_filename = secure_filename_custom(data.get('final_filename'))
        track_type = data.get('track_type')
        if not all([temp_filename, final_filename, track_type]): return jsonify({"error": "缺少必要参数"}), 400
        if AudioFile.query.filter_by(filename=final_filename, track_type=track_type).first(): return jsonify({'error': '已存在同名音频文件'}), 409
        
        temp_path = os.path.join(get_shared_audio_path(track_type), temp_filename)
        final_path = os.path.join(get_shared_audio_path(track_type), final_filename)
        if os.path.exists(temp_path):
            os.rename(temp_path, final_path)
            new_audio = AudioFile(filename=final_filename, track_type=track_type, is_global=False, user_id=current_user.id)
            db.session.add(new_audio)
            db.session.commit()
            return jsonify({"success": True, "message": "音频已成功保存到音乐库"})
        return jsonify({"error": "临时文件未找到"}), 404

    @app.route('/media/<track_type>/<path:filename>')
    def serve_audio_file(track_type, filename):
        if track_type not in ['mainsound', 'plussound', 'mix_elements']:
            abort(404)
        audio_path = get_audio_storage_path(track_type)
        return send_from_directory(audio_path, filename)

    @app.route('/', defaults={'path': ''})
    @app.route('/<path:path>')
    def serve(path):
        # This now ONLY serves core frontend files.
        if path != "" and os.path.exists(os.path.join(app.static_folder, path)):
            return send_from_directory(app.static_folder, path)
        return send_from_directory(app.static_folder, 'index.html')
            
    @app.cli.command("set-admin")
    def set_admin_command():
        username = input("Enter username to make admin: ")
        password = getpass.getpass("Enter a new password for this admin (leave blank to not change): ")
        user = User.query.filter_by(username=username).first()
        if user:
            print(f"User '{username}' found. Promoting to admin...")
            user.is_admin = True
            if password: user.set_password(password); print("Password has been updated.")
            db.session.commit()
            print(f"User '{username}' is now an admin.")
        else:
            print(f"User '{username}' not found. Creating a new admin user...")
            if not password: print("Error: A password is required for a new user."); return
            admin_user = User(username=username, is_admin=True)
            admin_user.set_password(password)
            db.session.add(admin_user)
            db.session.commit()
            print(f"Admin user '{username}' created successfully.")

    return app

if __name__ == '__main__':
    app = create_app()
    app.run(host='0.0.0.0', port=5000, debug=True)