import os
import logging
import atexit
import requests
import zipfile
import json
import shutil
from flask import Flask, jsonify, request
from flask_cors import CORS
import werkzeug.exceptions
from dotenv import load_dotenv
from filehandler import FileHandler
from database import DatabaseHandler 
from filecryptography import FileCryptography

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)
db = DatabaseHandler()
fh = FileHandler()
fc = FileCryptography()

@app.route('/api/update-checker/', methods=['GET'])
def update_checker():
    response = requests.get(os.getenv("CHECK_UPDATE_API"))
    data = response.json()
    version_data = data["Update details"]
    logger.info(f"Version data: {version_data}")
    # return jsonify({"message": "Update details fetched successfully", "version": version_data}), 200
    if db.check_update(version_data["version"]):
        return jsonify({"message": "No update available", "version": version_data["version"]}), 200
    else:
        return jsonify({"message": "Update available", "version": version_data["version"]}), 200

@app.route('/api/download/')
def download_update():
    LOCAL_DOWNLOAD_PATH = os.getenv("DOWNLOAD_PATH")
    try:
        # Send GET request to Django to download file
        response = requests.get('http://192.168.2.166:4000/download', stream=True)
        response.raise_for_status()

        # Extract filename from headers, if provided
        content_disposition = response.headers.get('Content-Disposition')
        if content_disposition and 'filename=' in content_disposition:
            filename = content_disposition.split('filename=')[1].strip('";')
        else:
            filename = 'update.zip'

        full_path = os.path.join(LOCAL_DOWNLOAD_PATH, filename)

        fileName = filename[:-4]
        print(f"File name: {fileName}")

        
        # Write the content to a local file
        with open(full_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)

        unzip_path = os.getenv("UNZIP_PATH")
        
        # Unzip the file and forwarding it to zonal controller
        if fh.unzip_file(fileName, full_path, unzip_path):
            print("Successfully unzipped the file.")
            # status = fh.file_forwader()
            # if status['status']:
            #     print("File forwarded successfully.")
            #     if db.put_update(status['update_version'], status['update_type']):
            #         print("Update details saved to database.")

        return jsonify({
            "status": "success",
            "message": f"File downloaded and saved as {full_path}"
        })

    except requests.RequestException as e:
        return jsonify({
            "status": "error",
            "message": f"Failed to download file: {e}"
        }), 500    


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)


