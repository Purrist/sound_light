import os
import json
from flask import Flask, jsonify, send_from_directory, request
from flask_cors import CORS

# --- Setup ---
# This setup correctly defines the static folder relative to this script's location.
# It tells Flask: "All static files are in the '../public' directory".
# static_url_path='' means a request for '/style.css' will look for 'style.css' inside the static_folder.
APP_ROOT = os.path.dirname(os.path.abspath(__file__))
PUBLIC_FOLDER = os.path.join(APP_ROOT, '..', 'public')

app = Flask(__name__, static_folder=PUBLIC_FOLDER, static_url_path='')
CORS(app)

# --- Path Definitions for backend logic ---
# These paths are now correctly based on the PUBLIC_FOLDER
STATIC_FOLDER = os.path.join(PUBLIC_FOLDER, 'static')
CONTROLSET_FOLDER = os.path.join(STATIC_FOLDER, 'controlset')
SOUNDSET_FOLDER = os.path.join(STATIC_FOLDER, 'soundset')
DEFAULT_CONFIG_FILE = os.path.join(CONTROLSET_FOLDER, 'default.txt')


def initialize_defaults():
    # This function is for local development to ensure files exist.
    os.makedirs(CONTROLSET_FOLDER, exist_ok=True)
    os.makedirs(SOUNDSET_FOLDER, exist_ok=True)
    os.makedirs(os.path.join(STATIC_FOLDER, 'mainsound'), exist_ok=True)
    os.makedirs(os.path.join(STATIC_FOLDER, 'plussound'), exist_ok=True)

    default_soundset_path = os.path.join(SOUNDSET_FOLDER, '海洋.json')
    if not os.path.exists(default_soundset_path):
        default_soundset_data = {"name": "海洋", "main": "sea.wav", "aux": "sea.wav"}
        with open(default_soundset_path, 'w', encoding='utf-8') as f: json.dump(default_soundset_data, f,
                                                                                ensure_ascii=False, indent=4)

    default_controlset_path = os.path.join(CONTROLSET_FOLDER, '默认配置.json')
    if not os.path.exists(default_controlset_path):
        default_controlset_data = {"breathsPerMin": "6", "masterKelvinStart": "2000", "masterHexStart": "#f57e0f",
                                   "masterKelvinEnd": "8000", "masterHexEnd": "#8cb1ff", "kelvinSliderDefault": "5000",
                                   "kelvinSliderMin": "3000", "kelvinSliderMax": "7000", "defaultColor": "#c19887",
                                   "warmColor": "#e48737", "coolColor": "#9ea9d7", "soundscapeSelect": "海洋",
                                   "panningEnable": False, "panningPeriod": "10", "mainVolDefault": "30",
                                   "mainVolMin": "0", "mainVolMax": "80", "auxEnable": False, "auxVolume": "50",
                                   "lightDelay": "5", "lightDuration": "10", "soundDelay": "10", "soundDuration": "10"}
        with open(default_controlset_path, 'w', encoding='utf-8') as f: json.dump(default_controlset_data, f,
                                                                                  ensure_ascii=False, indent=4)

    if not os.path.exists(DEFAULT_CONFIG_FILE):
        with open(DEFAULT_CONFIG_FILE, 'w', encoding='utf-8') as f: f.write('默认配置')


# --- API Routes ---
# All your API routes start here. They will work correctly.
@app.route('/api/get-audio-files')
def get_audio_files():
    try:
        mainsound_path = os.path.join(STATIC_FOLDER, 'mainsound')
        plussound_path = os.path.join(STATIC_FOLDER, 'plussound')
        if not os.path.exists(mainsound_path): os.makedirs(mainsound_path)
        if not os.path.exists(plussound_path): os.makedirs(plussound_path)
        mainsound_files = [f for f in os.listdir(mainsound_path) if f.lower().endswith(('.wav', '.mp3', '.ogg'))]
        plussound_files = [f for f in os.listdir(plussound_path) if f.lower().endswith(('.wav', '.mp3', '.ogg'))]
        return jsonify({'mainsound': mainsound_files, 'plussound': plussound_files})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/soundsets', methods=['GET'])
def get_soundsets():
    try:
        sets = [f.replace('.json', '') for f in os.listdir(SOUNDSET_FOLDER) if f.endswith('.json')]
        return jsonify(sets)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/soundsets/<name>', methods=['GET'])
def get_soundset_by_name(name):
    return send_from_directory(SOUNDSET_FOLDER, f"{name}.json")


@app.route('/api/soundsets', methods=['POST'])
def save_soundset():
    data = request.json
    name = data.get('name')
    if not name: return jsonify({'error': 'Soundset name is required'}), 400
    file_path = os.path.join(SOUNDSET_FOLDER, f"{name}.json")
    if os.path.exists(file_path): return jsonify({'error': 'Soundset with this name already exists'}), 409
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)
    return jsonify({'message': f'Soundset {name} saved successfully'})


@app.route('/api/soundsets/<name>', methods=['PUT'])
def update_soundset(name):
    data = request.json
    file_path = os.path.join(SOUNDSET_FOLDER, f"{name}.json")
    if not os.path.exists(file_path): return jsonify({'error': 'Soundset not found'}), 404
    with open(file_path, 'w', encoding='utf-8') as f: json.dump(data, f, ensure_ascii=False, indent=4)
    return jsonify({'message': f'Soundset {name} updated successfully'})


@app.route('/api/soundsets', methods=['DELETE'])
def delete_soundset():
    data = request.json
    name = data.get('name')
    if not name: return jsonify({'error': 'Soundset name is required'}), 400
    if name == '海洋': return jsonify({'error': 'Cannot delete the default soundset "海洋"'}), 403
    file_path = os.path.join(SOUNDSET_FOLDER, f"{name}.json")
    if os.path.exists(file_path):
        os.remove(file_path)
        return jsonify({'message': f'Soundset {name} deleted successfully'})
    return jsonify({'error': 'Soundset not found'}), 404


@app.route('/api/controlsets', methods=['GET'])
def get_controlsets():
    try:
        sets = [f.replace('.json', '') for f in os.listdir(CONTROLSET_FOLDER) if f.endswith('.json')]
        return jsonify(sets)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/controlsets/<name>', methods=['GET'])
def get_controlset_by_name(name):
    return send_from_directory(CONTROLSET_FOLDER, f"{name}.json")


@app.route('/api/controlsets', methods=['POST'])
def save_controlset():
    data = request.json
    name = data.get('name')
    if not name: return jsonify({'error': 'Controlset name is required'}), 400
    file_path = os.path.join(CONTROLSET_FOLDER, f"{name}.json")
    settings = data.get('settings', {})
    with open(file_path, 'w', encoding='utf-8') as f: json.dump(settings, f, ensure_ascii=False, indent=4)
    return jsonify({'message': f'Controlset {name} saved successfully'})


@app.route('/api/controlsets', methods=['DELETE'])
def delete_controlset():
    data = request.json
    name = data.get('name')
    if not name: return jsonify({'error': 'Controlset name is required'}), 400
    if name == '默认配置': return jsonify({'error': 'Cannot delete the default controlset "默认配置"'}), 403
    file_path = os.path.join(CONTROLSET_FOLDER, f"{name}.json")
    if os.path.exists(file_path):
        os.remove(file_path)
        if os.path.exists(DEFAULT_CONFIG_FILE):
            with open(DEFAULT_CONFIG_FILE, 'r', encoding='utf-8') as f:
                if f.read() == name: os.remove(DEFAULT_CONFIG_FILE)
        return jsonify({'message': f'Controlset {name} deleted successfully'})
    return jsonify({'error': 'Controlset not found'}), 404


@app.route('/api/controlsets/default', methods=['GET', 'POST'])
def handle_default_controlset():
    if request.method == 'GET':
        if os.path.exists(DEFAULT_CONFIG_FILE):
            with open(DEFAULT_CONFIG_FILE, 'r', encoding='utf-8') as f: return jsonify({'default': f.read()})
        return jsonify({'default': '默认配置'})
    if request.method == 'POST':
        data = request.json
        name = data.get('name')
        with open(DEFAULT_CONFIG_FILE, 'w', encoding='utf-8') as f: f.write(name)
        return jsonify({'message': f'Set {name} as default successfully'})


# --- Root Route for Frontend ---
# This serves the main index.html file.
@app.route('/')
def serve_index():
    return send_from_directory(app.static_folder, 'index.html')


# --- Main Entry Point for Local Development ---
if __name__ == '__main__':
    initialize_defaults()
    app.run(host='0.0.0.0', debug=True, port=5000)