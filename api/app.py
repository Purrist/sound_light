import os
import json
from flask import Flask, jsonify, send_from_directory, request
from flask_cors import CORS

app = Flask(__name__, static_folder='../public')
CORS(app)

# --- Path Definitions ---
# This structure works because this file is in /api, and public is in /public.
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PUBLIC_FOLDER = os.path.join(ROOT_DIR, 'public')
STATIC_FOLDER = os.path.join(PUBLIC_FOLDER, 'static')
CONTROLSET_FOLDER = os.path.join(STATIC_FOLDER, 'controlset')
SOUNDSET_FOLDER = os.path.join(STATIC_FOLDER, 'soundset')
DEFAULT_CONFIG_FILE = os.path.join(CONTROLSET_FOLDER, 'default.txt')

def initialize_defaults():
    # ... (This function remains unchanged) ...
    os.makedirs(CONTROLSET_FOLDER, exist_ok=True)
    os.makedirs(SOUNDSET_FOLDER, exist_ok=True)
    os.makedirs(os.path.join(STATIC_FOLDER, 'mainsound'), exist_ok=True)
    os.makedirs(os.path.join(STATIC_FOLDER, 'plussound'), exist_ok=True)
    default_soundset_path = os.path.join(SOUNDSET_FOLDER, '海洋.json')
    if not os.path.exists(default_soundset_path):
        default_soundset_data = {"name": "海洋", "main": "sea.wav", "aux": "sea.wav"}
        with open(default_soundset_path, 'w', encoding='utf-8') as f: json.dump(default_soundset_data, f, ensure_ascii=False, indent=4)
    default_controlset_path = os.path.join(CONTROLSET_FOLDER, '默认配置.json')
    if not os.path.exists(default_controlset_path):
        default_controlset_data = { "breathsPerMin": "6", "masterKelvinStart": "2000", "masterHexStart": "#f57e0f", "masterKelvinEnd": "8000", "masterHexEnd": "#8cb1ff", "kelvinSliderDefault": "5000", "kelvinSliderMin": "3000", "kelvinSliderMax": "7000", "defaultColor": "#c19887", "warmColor": "#e48737", "coolColor": "#9ea9d7", "soundscapeSelect": "海洋", "panningEnable": False, "panningPeriod": "10", "mainVolDefault": "30", "mainVolMin": "0", "mainVolMax": "80", "auxEnable": False, "auxVolume": "50", "lightDelay": "5", "lightDuration": "10", "soundDelay": "10", "soundDuration": "10" }
        with open(default_controlset_path, 'w', encoding='utf-8') as f: json.dump(default_controlset_data, f, ensure_ascii=False, indent=4)
    if not os.path.exists(DEFAULT_CONFIG_FILE):
        with open(DEFAULT_CONFIG_FILE, 'w', encoding='utf-8') as f: f.write('默认配置')


# --- API Routes ---
# (Paste ALL your API routes here, exactly as they are in your working version)
@app.route('/api/get-audio-files')
def get_audio_files():
    try:
        mainsound_path = os.path.join(STATIC_FOLDER, 'mainsound')
        plussound_path = os.path.join(STATIC_FOLDER, 'plussound')
        mainsound_files = [f for f in os.listdir(mainsound_path) if f.lower().endswith(('.wav', '.mp3', '.ogg'))]
        plussound_files = [f for f in os.listdir(plussound_path) if f.lower().endswith(('.wav', '.mp3', '.ogg'))]
        return jsonify({'mainsound': mainsound_files, 'plussound': plussound_files})
    except Exception as e: return jsonify({'error': str(e)}), 500
# ... etc ...

# --- Root Route for Frontend ---
# This handles the initial page load and allows client-side routing.
@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def serve(path):
    if path != "" and os.path.exists(os.path.join(app.static_folder, path)):
        return send_from_directory(app.static_folder, path)
    else:
        return send_from_directory(app.static_folder, 'index.html')


if __name__ == '__main__':
    initialize_defaults()
    app.run(host='0.0.0.0', debug=True, port=5000)