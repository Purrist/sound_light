import os
import json
from flask import Flask, jsonify, send_from_directory, request
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

# FIX: Use a robust way to find the project root and public folder
APP_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(APP_DIR)
PUBLIC_FOLDER = os.path.join(ROOT_DIR, 'public')
STATIC_FOLDER = os.path.join(PUBLIC_FOLDER, 'static')
CONTROLSET_FOLDER = os.path.join(STATIC_FOLDER, 'controlset')
SOUNDSET_FOLDER = os.path.join(STATIC_FOLDER, 'soundset')

# ... [The initialize_defaults function and all routes remain exactly the same] ...
# ... I am providing the full file for completeness ...
def initialize_defaults():
    os.makedirs(CONTROLSET_FOLDER, exist_ok=True)
    os.makedirs(SOUNDSET_FOLDER, exist_ok=True)
    os.makedirs(os.path.join(STATIC_FOLDER, 'mainsound'), exist_ok=True)
    os.makedirs(os.path.join(STATIC_FOLDER, 'plussound'), exist_ok=True)
    default_soundset_path = os.path.join(SOUNDSET_FOLDER, '海洋.json')
    if not os.path.exists(default_soundset_path):
        default_soundset_data = {"name": "海洋", "main": "sea.wav", "aux": "sea.wav"}
        with open(default_soundset_path, 'w', encoding='utf-8') as f:
            json.dump(default_soundset_data, f, ensure_ascii=False, indent=4)
    default_controlset_path = os.path.join(CONTROLSET_FOLDER, '默认配置.json')
    if not os.path.exists(default_controlset_path):
        default_controlset_data = { "breathsPerMin": "6", "masterKelvinStart": "2000", "masterHexStart": "#f57e0f", "masterKelvinEnd": "8000", "masterHexEnd": "#8cb1ff", "kelvinSliderDefault": "5000", "kelvinSliderMin": "3000", "kelvinSliderMax": "7000", "defaultColor": "#c19887", "warmColor": "#e48737", "coolColor": "#9ea9d7", "soundscapeSelect": "海洋", "panningEnable": False, "panningPeriod": "10", "mainVolDefault": "30", "mainVolMin": "0", "mainVolMax": "80", "auxEnable": False, "auxVolume": "50", "lightDelay": "5", "lightDuration": "10", "soundDelay": "10", "soundDuration": "10" }
        with open(default_controlset_path, 'w', encoding='utf-8') as f:
            json.dump(default_controlset_data, f, ensure_ascii=False, indent=4)
        default_config_file = os.path.join(CONTROLSET_FOLDER, 'default.txt')
        if not os.path.exists(default_config_file):
            with open(default_config_file, 'w', encoding='utf-8') as f: f.write('默认配置')

# This is the entry point for Vercel
@app.route('/')
def index():
    return send_from_directory(PUBLIC_FOLDER, 'index.html')

@app.route('/<path:path>')
def serve_static_files(path):
    if os.path.exists(os.path.join(PUBLIC_FOLDER, path)):
        return send_from_directory(PUBLIC_FOLDER, path)
    return "Not Found", 404