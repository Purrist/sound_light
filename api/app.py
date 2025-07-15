import os
import json
from flask import Flask, jsonify, send_from_directory, request
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

# --- Path Finding (Works for both local and Vercel/Netlify) ---
# This intelligently finds the project root directory.
IS_VERCEL = os.environ.get('VERCEL') == '1'
if IS_VERCEL:
    # On Vercel, the structure is /var/task/api/app.py, so we go up two levels
    ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
else:
    # For local development, the structure is .../sound_light/api/app.py
    ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
    # To match the Vercel structure, we assume we are inside an 'api' folder
    if os.path.basename(ROOT_DIR) == 'api':
        ROOT_DIR = os.path.dirname(ROOT_DIR)

PUBLIC_FOLDER = os.path.join(ROOT_DIR, 'public')
STATIC_FOLDER = os.path.join(PUBLIC_FOLDER, 'static')
CONTROLSET_FOLDER = os.path.join(STATIC_FOLDER, 'controlset')
SOUNDSET_FOLDER = os.path.join(STATIC_FOLDER, 'soundset')


def initialize_defaults():
    os.makedirs(CONTROLSET_FOLDER, exist_ok=True)
    os.makedirs(SOUNDSET_FOLDER, exist_ok=True)
    os.makedirs(os.path.join(STATIC_FOLDER, 'mainsound'), exist_ok=True)
    os.makedirs(os.path.join(STATIC_FOLDER, 'plussound'), exist_ok=True)
    # ... (the rest of initialize_defaults is the same)
    default_soundset_path = os.path.join(SOUNDSET_FOLDER, '海洋.json')
    if not os.path.exists(default_soundset_path):
        default_soundset_data = {"name": "海洋", "main": "sea.wav", "aux": "sea.wav"}
        with open(default_soundset_path, 'w', encoding='utf-8') as f: json.dump(default_soundset_data, f, ensure_ascii=False, indent=4)
    default_controlset_path = os.path.join(CONTROLSET_FOLDER, '默认配置.json')
    if not os.path.exists(default_controlset_path):
        default_controlset_data = { "breathsPerMin": "6", "masterKelvinStart": "2000", "masterHexStart": "#f57e0f", "masterKelvinEnd": "8000", "masterHexEnd": "#8cb1ff", "kelvinSliderDefault": "5000", "kelvinSliderMin": "3000", "kelvinSliderMax": "7000", "defaultColor": "#c19887", "warmColor": "#e48737", "coolColor": "#9ea9d7", "soundscapeSelect": "海洋", "panningEnable": False, "panningPeriod": "10", "mainVolDefault": "30", "mainVolMin": "0", "mainVolMax": "80", "auxEnable": False, "auxVolume": "50", "lightDelay": "5", "lightDuration": "10", "soundDelay": "10", "soundDuration": "10" }
        with open(default_controlset_path, 'w', encoding='utf-8') as f: json.dump(default_controlset_data, f, ensure_ascii=False, indent=4)
        default_config_file = os.path.join(CONTROLSET_FOLDER, 'default.txt')
        if not os.path.exists(default_config_file):
            with open(default_config_file, 'w', encoding='utf-8') as f: f.write('默认配置')


# --- API Routes ---
# All your /api/... routes go here, they will work on Vercel/Netlify
@app.route('/api/get-audio-files')
def get_audio_files():
    # ... (same as before)
    try:
        mainsound_path = os.path.join(STATIC_FOLDER, 'mainsound')
        plussound_path = os.path.join(STATIC_FOLDER, 'plussound')
        if not os.listdir(mainsound_path):
            with open(os.path.join(mainsound_path, 'sea.wav'), 'w') as f: f.write('')
        if not os.listdir(plussound_path):
            with open(os.path.join(plussound_path, 'sea.wav'), 'w') as f: f.write('')
        mainsound_files = [f for f in os.listdir(mainsound_path) if f.lower().endswith(('.wav', '.mp3', '.ogg'))]
        plussound_files = [f for f in os.listdir(plussound_path) if f.lower().endswith(('.wav', '.mp3', '.ogg'))]
        return jsonify({'mainsound': mainsound_files, 'plussound': plussound_files})
    except Exception as e: return jsonify({'error': str(e)}), 500
# ... (Add all your other /api/... routes here)


# --- Static File and Root Route for Local Development ---
# This part will be IGNORED by Vercel/Netlify but is ESSENTIAL for local testing.
if not IS_VERCEL:
    @app.route('/')
    def index():
        return send_from_directory(PUBLIC_FOLDER, 'index.html')

    @app.route('/<path:path>')
    def serve_static_files(path):
        return send_from_directory(PUBLIC_FOLDER, path)

# --- Main Entry Point for Local Development ---
if __name__ == '__main__':
    initialize_defaults()
    # The debug=True is important for local development
    app.run(debug=True, port=5000)