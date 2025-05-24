import json
import os
import zipfile
import requests
import paramiko
from dotenv import load_dotenv
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

# Load environment variables from .env file
load_dotenv()

class FileHandler:
    def __init__(self, filename):
        self.filename = filename

    #Extracting zip file
    def unzip_file(self, filename, zip_path, extract_path): 
        if not os.path.exists(extract_to):
            os.makedirs(extract_to)

        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(extract_to)
        
        unzipped_path = os.path.join(extract_path, filename)
        config_path = os.path.join(unzipped_path, "config.json")

        if not os.path.isfile(config_path):
            raise FileNotFoundError(f"'config.json' not found in {extract_to}")

        with open(config_path, 'r') as f:
            self.config_data = json.load(f)

        if self.config_data:
            print(self.config_data)
            return True
        else:
            print("No config data found.")
            return False
    
    def file_forwader():
        print(self.config_data)
        update = self.config["update_details"]
        ip = update["ip"]
        username = update["username"]
        password = update["password"]
        target_dir = update["target_dir"]
        
        try:
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh.connect(ip, username=username, password=password)

            sftp = ssh.open_sftp()
            target_path = os.path.join(target_dir, self.filename)
            sftp.put(self.filename, target_path)
            sftp.close()
            ssh.close()
            print(f"File {self.filename} forwarded to {ip}:{target_path}")
        
        except Exception as e:
            print(f"Failed to forward file: {e}")
            return False
        
        return True
    
    


    

