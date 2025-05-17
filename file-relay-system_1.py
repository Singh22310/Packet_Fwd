#!/usr/bin/env python3
"""
R-Car S4 File Relay System

This script sets up a system that:
1. Receives files on the R-Car S4
2. Relays files to specific Raspberry Pis based on file naming patterns
3. Maintains a detailed log of all file transfers
"""

import os
import sys
import time
import datetime
import logging
import shutil
import json
import socket
import threading
import argparse
from pathlib import Path
import paramiko
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

# Configuration
CONFIG = {
    "incoming_dir": "/home/root/incoming",  # Directory to watch for incoming files
    "outgoing_dir": "/home/root/outgoing",  # Directory to store outgoing files
    "log_dir": "/home/root/logs",           # Directory to store logs
    "raspberry_pis": [
        {"name": "zc1", "ip": "192.168.1.106", "user": "raspberry", "password": "raspberry", "target_dir": "/home/raspberry/received_files"},
        {"name": "zc2", "ip": "192.168.1.245", "user": "raspberry", "password": "raspberry", "target_dir": "/home/raspberry/received_files"},
        {"name": "zc3", "ip": "192.168.1.118", "user": "dev1", "password": "rasp@pi", "target_dir": "/home/dev1/received_files"}
    ],
    "file_patterns": {
        # Format: "pattern": ["raspi1", "raspi2", ...] or "all" for all Raspberry Pis
        "zc1_": ["zc1"],              # Files starting with "raspi1_" go to raspi1
        "zc2_": ["zc2"],              # Files starting with "raspi2_" go to raspi2
        "zc3_": ["zc3"],              # Files starting with "raspi3_" go to raspi3
        "zc12_": ["zc1", "zc2"],   # Files starting with "raspi12_" go to raspi1 and raspi2
        "zc13_": ["zc1", "zc3"],   # Files starting with "raspi13_" go to raspi1 and raspi3
        "zc23_": ["zc2", "zc3"],   # Files starting with "raspi23_" go to raspi2 and raspi3
        "all_": "all"                       # Files starting with "all_" go to all Raspberry Pis
    },
    "default_target": "all",              # Default target if no pattern matches: "all" or specific Pi names
    "server_port": 8000,                  # Port for receiving files via network
    "enable_sftp": True,                  # Enable SFTP server for file reception
    "sftp_port": 2222                     # Port for SFTP server
}

# Setup logging
def setup_logging():
    log_dir = Path(CONFIG["log_dir"])
    log_dir.mkdir(exist_ok=True, parents=True)
    
    log_file = log_dir / f"file_relay_{datetime.datetime.now().strftime('%Y%m%d')}.log"
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(essage)s',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler(sys.stdout)
        ]
    )
    
    return logging.getLogger("FileRelay")

logger = setup_logging()

# Ensure directories exist
def ensure_directories():
    for dir_path in [CONFIG["incoming_dir"], CONFIG["outgoing_dir"], CONFIG["log_dir"]]:
        os.makedirs(dir_path, exist_ok=True)
        logger.info(f"Ensured directory exists: {dir_path}")

# File handler for detecting new files
class NewFileHandler(FileSystemEventHandler):
    def on_created(self, event):
        if event.is_directory:
            return
        
        # Give the system some time to finish writing the file
        time.sleep(1)
        
        file_path = event.src_path
        logger.info(f"New file detected: {file_path}")
        
        # Process the file (relay to all Raspberry Pis)
        relay_file_to_raspberry_pis(file_path)

# Determine target Raspberry Pis based on file name
def get_target_pis(file_name):
    # Check for matches in file patterns
    for pattern, targets in CONFIG["file_patterns"].items():
        if file_name.startswith(pattern):
            if targets == "all":
                return [pi["name"] for pi in CONFIG["raspberry_pis"]]
            else:
                return targets
    
    # If no pattern matches, use default target
    if CONFIG["default_target"] == "all":
        return [pi["name"] for pi in CONFIG["raspberry_pis"]]
    else:
        return CONFIG["default_target"]

# Relay file to specific Raspberry Pis
def relay_file_to_raspberry_pis(file_path):
    file_name = os.path.basename(file_path)
    file_size = os.path.getsize(file_path)
    
    # Determine target Raspberry Pis
    target_pi_names = get_target_pis(file_name)
    target_pis = [pi for pi in CONFIG["raspberry_pis"] if pi["name"] in target_pi_names]
    
    logger.info(f"Relaying file: {file_name} ({file_size} bytes) to Raspberry Pis: {', '.join(target_pi_names)}")
    
    # Create a copy in the outgoing directory
    outgoing_path = os.path.join(CONFIG["outgoing_dir"], file_name)
    shutil.copy2(file_path, outgoing_path)
    
    # Record in transfer log
    transfer_log = {
        "file_name": file_name,
        "file_size": file_size,
        "timestamp": datetime.datetime.now().isoformat(),
        "source": "incoming_dir",
        "targets": target_pi_names,
        "destinations": []
    }
    
    # Send to each target Raspberry Pi
    for pi in target_pis:
        try:
            send_file_via_sftp(file_path, pi)
            status = "success"
        except Exception as e:
            logger.error(f"Failed to send file to {pi['name']}: {str(e)}")
            status = f"failed: {str(e)}"
        
        transfer_log["destinations"].append({
            "device": pi["name"],
            "ip": pi["ip"],
            "target_path": os.path.join(pi["target_dir"], file_name),
            "status": status,
            "timestamp": datetime.datetime.now().isoformat()
        })
    
    # Save transfer log
    log_file = os.path.join(
        CONFIG["log_dir"], 
        f"transfer_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}_{file_name}.json"
    )
    with open(log_file, 'w') as f:
        json.dump(transfer_log, f, indent=2)
    
    logger.info(f"Transfer log saved to {log_file}")

# Send file via SFTP
def send_file_via_sftp(file_path, pi_config):
    logger.info(f"Sending {file_path} to {pi_config['name']} ({pi_config['ip']})")
    
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    
    try:
        ssh.connect(
            pi_config["ip"],
            username=pi_config["user"],
            password=pi_config["password"]
        )
        
        # Create target directory if it doesn't exist
        stdin, stdout, stderr = ssh.exec_command(f"mkdir -p {pi_config['target_dir']}")
        
        # Transfer the file
        sftp = ssh.open_sftp()
        target_path = os.path.join(pi_config["target_dir"], os.path.basename(file_path))
        sftp.put(file_path, target_path)
        sftp.close()
        
        logger.info(f"Successfully sent {file_path} to {pi_config['name']}")
    finally:
        ssh.close()

# TCP server for receiving files over network
class FileReceiver:
    def __init__(self, host='0.0.0.0', port=CONFIG["server_port"]):
        self.host = host
        self.port = port
        self.server_socket = None
    
    def start(self):
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        
        try:
            self.server_socket.bind((self.host, self.port))
            self.server_socket.listen(5)
            logger.info(f"File receiver server started on {self.host}:{self.port}")
            
            while True:
                client_socket, addr = self.server_socket.accept()
                logger.info(f"Connection from {addr}")
                
                # Handle client in a new thread
                client_thread = threading.Thread(
                    target=self.handle_client,
                    args=(client_socket, addr)
                )
                client_thread.daemon = True
                client_thread.start()
                
        except Exception as e:
            logger.error(f"Server error: {str(e)}")
        finally:
            if self.server_socket:
                self.server_socket.close()
    
    def handle_client(self, client_socket, addr):
        try:
            # Receive header with file name and size
            header_data = client_socket.recv(1024).decode('utf-8')
            header = json.loads(header_data)
            
            file_name = header.get('file_name')
            file_size = header.get('file_size')
            
            if not file_name or not isinstance(file_size, int):
                raise ValueError("Invalid file header")
            
            logger.info(f"Receiving file: {file_name} ({file_size} bytes) from {addr}")
            
            # Define the destination path
            dest_path = os.path.join(CONFIG["incoming_dir"], file_name)
            
            # Send acknowledgment
            client_socket.send(b"ACK")
            
            # Receive and write the file
            with open(dest_path, 'wb') as f:
                bytes_received = 0
                while bytes_received < file_size:
                    chunk = client_socket.recv(min(4096, file_size - bytes_received))
                    if not chunk:
                        break
                    f.write(chunk)
                    bytes_received += len(chunk)
            
            logger.info(f"File {file_name} received successfully from {addr}")
            client_socket.send(b"SUCCESS")
            
        except Exception as e:
            logger.error(f"Error handling client {addr}: {str(e)}")
            try:
                client_socket.send(f"ERROR: {str(e)}".encode('utf-8'))
            except:
                pass
        finally:
            client_socket.close()

# Main function
def main():
    logger.info("Starting R-Car S4 File Relay System")
    
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="R-Car S4 File Relay System")
    parser.add_argument("--config", help="Path to configuration file")
    args = parser.parse_args()
    
    # Load configuration from file if specified
    if args.config:
        try:
            with open(args.config, 'r') as f:
                config_data = json.load(f)
                global CONFIG
                CONFIG.update(config_data)
                logger.info(f"Loaded configuration from {args.config}")
        except Exception as e:
            logger.error(f"Failed to load configuration: {str(e)}")
    
    # Ensure necessary directories exist
    ensure_directories()
    
    # Start file watcher for incoming directory
    event_handler = NewFileHandler()
    observer = Observer()
    observer.schedule(event_handler, CONFIG["incoming_dir"], recursive=False)
    observer.start()
    logger.info(f"Watching for new files in {CONFIG['incoming_dir']}")
    
    # Start TCP server for file reception in a new thread
    file_receiver = FileReceiver()
    server_thread = threading.Thread(target=file_receiver.start)
    server_thread.daemon = True
    server_thread.start()
    
    try:
        # Keep the main thread running
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("Stopping file relay service...")
        observer.stop()
    
    observer.join()
    logger.info("File relay service stopped")

if __name__ == "__main__":
    main()
