import os
import logging
import atexit
import requests
import zipfile
import json
import time
import datetime
import shutil
import threading
import paramiko
from pathlib import Path
from flask import Flask, jsonify, request
from flask_cors import CORS
import werkzeug.exceptions
from dotenv import load_dotenv
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

import database

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)
database.init_db()

# Global variables for file relay system
config_data = None
file_observer = None
relay_active = False

class NewFileHandler(FileSystemEventHandler):
    def __init__(self, config):
        self.config = config
        
    def on_created(self, event):
        if event.is_directory:
            return
        
        # Give the system some time to finish writing the file
        time.sleep(1)
        
        file_path = event.src_path
        logger.info(f"New file detected: {file_path}")
        
        # Process the file (relay to configured destinations)
        relay_file_to_destinations(file_path, self.config)

def get_target_destinations(file_name, config):
    """Determine target destinations based on file name patterns"""
    file_patterns = config.get("file_patterns", {})
    destinations = config.get("destinations", [])
    
    # Check for matches in file patterns
    for pattern, targets in file_patterns.items():
        if file_name.startswith(pattern):
            if targets == "all":
                return [dest["name"] for dest in destinations]
            else:
                return targets
    
    # If no pattern matches, use default target
    default_target = config.get("default_target", "all")
    if default_target == "all":
        return [dest["name"] for dest in destinations]
    else:
        return default_target if isinstance(default_target, list) else [default_target]

def send_file_via_sftp(file_path, dest_config):
    """Send file via SFTP to destination"""
    logger.info(f"Sending {file_path} to {dest_config['name']} ({dest_config['ip']})")
    
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    
    try:
        ssh.connect(
            dest_config["ip"],
            username=dest_config["user"],
            password=dest_config["password"],
            port=dest_config.get("port", 22)
        )
        
        # Create target directory if it doesn't exist
        target_dir = dest_config["target_dir"]
        stdin, stdout, stderr = ssh.exec_command(f"mkdir -p {target_dir}")
        
        # Transfer the file
        sftp = ssh.open_sftp()
        target_path = os.path.join(target_dir, os.path.basename(file_path))
        sftp.put(file_path, target_path)
        sftp.close()
        
        logger.info(f"Successfully sent {file_path} to {dest_config['name']}")
        return True
    except Exception as e:
        logger.error(f"Failed to send file to {dest_config['name']}: {str(e)}")
        return False
    finally:
        ssh.close()

def relay_file_to_destinations(file_path, config):
    """Relay file to specific destinations based on configuration"""
    file_name = os.path.basename(file_path)
    file_size = os.path.getsize(file_path)
    
    # Get destinations and target destinations
    destinations = config.get("destinations", [])
    target_dest_names = get_target_destinations(file_name, config)
    target_destinations = [dest for dest in destinations if dest["name"] in target_dest_names]
    
    logger.info(f"Relaying file: {file_name} ({file_size} bytes) to destinations: {', '.join(target_dest_names)}")
    
    # Create a copy in the outgoing directory if specified
    outgoing_dir = config.get("outgoing_dir")
    if outgoing_dir:
        os.makedirs(outgoing_dir, exist_ok=True)
        outgoing_path = os.path.join(outgoing_dir, file_name)
        shutil.copy2(file_path, outgoing_path)
    
    # Record in transfer log
    transfer_log = {
        "file_name": file_name,
        "file_size": file_size,
        "timestamp": datetime.datetime.now().isoformat(),
        "source": file_path,
        "targets": target_dest_names,
        "destinations": []
    }
    
    # Send to each target destination
    for dest in target_destinations:
        try:
            success = send_file_via_sftp(file_path, dest)
            status = "success" if success else "failed"
        except Exception as e:
            logger.error(f"Failed to send file to {dest['name']}: {str(e)}")
            status = f"failed: {str(e)}"
        
        transfer_log["destinations"].append({
            "device": dest["name"],
            "ip": dest["ip"],
            "target_path": os.path.join(dest["target_dir"], file_name),
            "status": status,
            "timestamp": datetime.datetime.now().isoformat()
        })
    
    # Save transfer log if log directory is specified
    log_dir = config.get("log_dir")
    if log_dir:
        os.makedirs(log_dir, exist_ok=True)
        log_file = os.path.join(
            log_dir, 
            f"transfer_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}_{file_name}.json"
        )
        with open(log_file, 'w') as f:
            json.dump(transfer_log, f, indent=2)
        logger.info(f"Transfer log saved to {log_file}")

def start_file_relay(config):
    """Start the file relay system with the given configuration"""
    global file_observer, relay_active
    
    # Stop existing observer if running
    stop_file_relay()
    
    incoming_dir = config.get("incoming_dir")
    if not incoming_dir:
        logger.error("No incoming_dir specified in configuration")
        return False
    
    # Ensure incoming directory exists
    os.makedirs(incoming_dir, exist_ok=True)
    
    # Create and start file observer
    event_handler = NewFileHandler(config)
    file_observer = Observer()
    file_observer.schedule(event_handler, incoming_dir, recursive=False)
    file_observer.start()
    relay_active = True
    
    logger.info(f"File relay system started, watching: {incoming_dir}")
    return True

def stop_file_relay():
    """Stop the file relay system"""
    global file_observer, relay_active
    
    if file_observer and file_observer.is_alive():
        file_observer.stop()
        file_observer.join()
        logger.info("File relay system stopped")
    
    relay_active = False

@app.route('/api/update-checker/', methods=['GET'])
def update_checker():
    response = requests.get(os.getenv("CHECK_UPDATE_API"))
    data = response.json()
    version_data = data["Update details"]
    logger.info(f"Version data: {version_data}")
    
    if database.check_update(version_data["version"]):
        return jsonify({"message": "No update available", "version": version_data["version"]}), 200
    else:
        return jsonify({"message": "Update available", "version": version_data["version"]}), 200

@app.route('/api/download/')
def download_update():
    LOCAL_DOWNLOAD_PATH = os.getenv("DOWNLOAD_PATH")
    try:
        # Send GET request to Django to download file
        response = requests.get('http://192.168.2.124:4000/download', stream=True)
        response.raise_for_status()

        # Extract filename from headers, if provided
        content_disposition = response.headers.get('Content-Disposition')
        if content_disposition and 'filename=' in content_disposition:
            filename = content_disposition.split('filename=')[1].strip('";')
        else:
            filename = 'update.zip'

        full_path = os.path.join(LOCAL_DOWNLOAD_PATH, filename)
        fileName = filename[:-4]
        logger.info(f"File name: {fileName}")

        # Write the content to a local file
        with open(full_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)

        unzip_path = os.getenv("UNZIP_PATH")
        success = unzip_file(fileName, full_path, unzip_path)
        
        if success:
            # Start a thread to shut down the application after a short delay to ensure response is sent
            def shutdown():
                time.sleep(1)  # Brief delay to allow response to be sent
                logger.info("Shutting down application after relaying extracted files")
                os._exit(0)
            
            threading.Thread(target=shutdown).start()
            return jsonify({
                "status": "success",
                "message": "File downloaded, extracted, and relayed. Application will exit."
            })
        else:
            return jsonify({
                "status": "error",
                "message": "File downloaded but failed to relay extracted files"
            }), 500

    except requests.RequestException as e:
        return jsonify({
            "status": "error",
            "message": f"Failed to download file: {e}"
        }), 500    

def unzip_file(filename, zip_path, extract_to):
    """Extract zip file and relay extracted files to destinations"""
    global config_data
    
    try:
        if not os.path.exists(extract_to):
            os.makedirs(extract_to)

        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(extract_to)
        
        unzipped_path = os.path.join(extract_to, filename)
        config_path = os.path.join(unzipped_path, "config.json")

        if not os.path.isfile(config_path):
            logger.error(f"'config.json' not found in {unzipped_path}")
            return False

        with open(config_path, 'r') as f:
            config_data = json.load(f)

        logger.info(f"Configuration loaded: {config_data}")
        
        # Relay all extracted files (except config.json) to destinations
        threads = []
        for root, _, files in os.walk(unzipped_path):
            for file_name in files:
                if file_name != "config.json":  # Skip config.json
                    file_path = os.path.join(root, file_name)
                    logger.info(f"Relaying extracted file: {file_path}")
                    # Use threading to relay files concurrently
                    thread = threading.Thread(
                        target=relay_file_to_destinations,
                        args=(file_path, config_data)
                    )
                    threads.append(thread)
                    thread.start()

        # Wait for all relay threads to complete
        for thread in threads:
            thread.join()

        logger.info("All extracted files have been relayed")
        return True
        
    except Exception as e:
        logger.error(f"Error in unzip_file: {str(e)}")
        return False

@app.route('/api/relay-status/', methods=['GET'])
def relay_status():
    """Get the status of the file relay system"""
    global relay_active, config_data
    
    return jsonify({
        "active": relay_active,
        "config_loaded": config_data is not None,
        "incoming_dir": config_data.get("incoming_dir") if config_data else None,
        "destinations_count": len(config_data.get("destinations", [])) if config_data else 0
    })

@app.route('/api/relay-config/', methods=['GET'])
def get_relay_config():
    """Get the current relay configuration"""
    global config_data
    
    if config_data:
        # Return config without sensitive information like passwords
        safe_config = config_data.copy()
        if "destinations" in safe_config:
            safe_destinations = []
            for dest in safe_config["destinations"]:
                safe_dest = dest.copy()
                if "password" in safe_dest:
                    safe_dest["password"] = "***"
                safe_destinations.append(safe_dest)
            safe_config["destinations"] = safe_destinations
        
        return jsonify(safe_config)
    else:
        return jsonify({"error": "No configuration loaded"}), 404

@app.route('/api/relay-stop/', methods=['POST'])
def stop_relay():
    """Stop the file relay system"""
    stop_file_relay()
    return jsonify({"message": "File relay system stopped"})

@app.route('/api/relay-start/', methods=['POST'])
def start_relay():
    """Start the file relay system with current configuration"""
    global config_data
    
    if not config_data:
        return jsonify({"error": "No configuration loaded"}), 400
    
    success = start_file_relay(config_data)
    if success:
        return jsonify({"message": "File relay system started"})
    else:
        return jsonify({"error": "Failed to start file relay system"}), 500

@app.route('/api/send-file/', methods=['POST'])
def send_file_manually():
    """Manually send a file to destinations"""
    global config_data
    
    if not config_data:
        return jsonify({"error": "No configuration loaded"}), 400
    
    data = request.get_json()
    file_path = data.get('file_path')
    
    if not file_path or not os.path.exists(file_path):
        return jsonify({"error": "Invalid file path"}), 400
    
    try:
        # Use a separate thread to avoid blocking the response
        threading.Thread(
            target=relay_file_to_destinations,
            args=(file_path, config_data)
        ).start()
        
        return jsonify({"message": "File relay started"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Cleanup function to stop file relay when app shuts down
def cleanup():
    stop_file_relay()

atexit.register(cleanup)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)