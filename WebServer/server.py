from flask import Flask, request, jsonify, send_from_directory
import os
from dotenv import load_dotenv
import hashlib
import base64
from werkzeug.utils import secure_filename

load_dotenv()

app = Flask(__name__)

UPLOAD_FOLDER = os.path.join(app.root_path, 'static', 'uploads')
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

API_KEY = os.getenv('API_KEY')
RETURN_DOMAIN = os.getenv('RETURN_DOMAIN')

def encrypt_filename(filename):
    hashed_filename = hashlib.sha256(filename.encode()).digest()
    encoded_filename = base64.urlsafe_b64encode(hashed_filename).decode()
    return encoded_filename
    
@app.route('/upload', methods=['POST'])
def upload_file():
    if 'x-api-key' not in request.headers or request.headers['x-api-key'] != API_KEY:
        return jsonify({"error": "Unauthorized"}), 401

    if 'file' not in request.files:
        return jsonify({"error": "No file part"}), 400

    file = request.files['file']

    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400

    if file:
        filename, file_extension = os.path.splitext(file.filename)
        encrypted_filename = encrypt_filename(filename) + file_extension
        filepath = os.path.join(UPLOAD_FOLDER, secure_filename(encrypted_filename))
        file.save(filepath)
        file_url = f"https://{RETURN_DOMAIN}/i/{encrypted_filename}"
        return jsonify({"url": file_url}), 200

    return jsonify({"error": "File upload failed"}), 500

@app.route('/i/<filename>', methods=['GET'])
def serve_file(filename):
    try:
        return send_from_directory(UPLOAD_FOLDER, filename)
    except Exception as e:
        return jsonify({"error": str(e)}), 404

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
