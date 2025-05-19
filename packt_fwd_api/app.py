import os
import logging
import atexit
import requests
from flask import Flask, jsonify, request
from flask_cors import CORS
import werkzeug.exceptions
from dotenv import load_dotenv

# import database

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)
# database.init_db()

@app.route('/update-checker/', methods=['GET'])
def update_checker():
    response = requests.get(os.getenv("CHECK_UPDATE_API"))
    data = response.json()
    version_data = data["Update details"]
    logger.info(f"Version data: {version_data}")
    return jsonify({"message": "Update details fetched successfully", "version": version_data}), 200
    # if database.check_update(version_data["id"]):
        # return jsonify({"message": "Update available", "version": version_data["id"]}), 200
    # else:
        # return jsonify({"message": "No update available", "version": version_data["id"]}), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)


