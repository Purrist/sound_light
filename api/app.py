import os
import json
from flask import Flask, jsonify, send_from_directory, request
from flask_cors import CORS

# --- Setup ---
# We define the Flask app with a specific static folder
# This tells Flask to look for files like style.css and sea.wav inside the 'public' directory
PUBLIC_FOLDER_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'public')
app = Flask(__name__, static_folder=PUBLIC_FOLDER_PATH, static_url_path='')
CORS(app)

# --- Path Definitions (for backend logic) ---
STATIC_LOGIC_PATH = os.path.join(PUBLIC_FOLDER_PATH, 'static')
CONTROLSET_FOLDER = os.path.join(STATIC_LOGIC_PATH, 'controlset')
SOUNDSET_FOLDER = os.path.join(STATIC_LOGIC_PATH, 'soundset')
DEFAULT_CONFIG_FILE = os.path.join(CONTROLSET_FOLDER, 'default.txt')

def initialize_defaults():
    # ... (This function remains unchanged, no need to copy it again if it's correct)
    os.makedirs(CONTROLSET_FOLDER, exist_ok=True)
    os.makedirs(SOUNDSET_FOLDER, exist_ok=True)
    os.makedirs(os.path.join(STATIC_LOGIC_PATH, 'mainsound'), exist_ok=True)
    os.makedirs(os.path.join(STATIC_LOGIC_PATH, 'plussound'), exist_ok=True)
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
# All your /api/... routes remain here. They will work perfectly.
@app.route('/api/get-audio-files')
def get_audio_files():
    try:
        mainsound_path = os.path.join(STATIC_LOGIC_PATH, 'mainsound')
        plussound_path = os.path.join(STATIC_LOGIC_PATH, 'plussound')
        mainsound_files = [f for f in os.listdir(mainsound_path) if f.lower().endswith(('.wav', '.mp3', '.ogg'))]
        plussound_files = [f for f in os.listdir(plussound_path) if f.lower().endswith(('.wav', '.mp3', '.ogg'))]
        return jsonify({'mainsound': mainsound_files, 'plussound': plussound_files})
    except Exception as e: return jsonify({'error': str(e)}), 500

# ... (Paste ALL your other API routes here) ...


# --- Root Route ---
# This serves the main HTML file for any path that is not an API call or a known static file.
@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def catch_all(path):
    # Let Flask's built-in static file handling do the work.
    # If the path is a file in the 'public' folder, it will be served.
    # Otherwise, we serve index.html.
    if path != "" and os.path.exists(os.path.join(app.static_folder, path)):
        return send_from_directory(app.static_folder, path)
    else:
        return send_from_directory(app.static_folder, 'index.html')


# --- Main Entry Point ---
if __name__ == '__main__':
    initialize_defaults()
    app.run(host='0.0.0.0', debug=True, port=5000)