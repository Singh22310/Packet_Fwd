import json
import os
import zipfile
import requests
import paramiko
from dotenv import load_dotenv


# Load environment variables from .env file
load_dotenv()

class FileHandler:
    def __init__(self):
        self.config_data = None
        self.filename = None
        self.key = None

    #Extracting zip file
    def unzip_file(self, filename, zip_path, extract_path): 
        self.filename = filename
        if not os.path.exists(extract_path):
            os.makedirs(extract_path)

        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(extract_path)
        
        # unzipped_path = os.path.join(extract_path, filename)
        # config_path = os.path.join(unzipped_path, "config.json")
        enc_file = "encrypted_file.enc"
        key_path = os.path.join(extract_path, "aes-key.enc")

        if not os.path.isfile(key_path):
            raise FileNotFoundError(f"'key.txt' not found in {extract_path}")

        else:
            print(f"Key file found at {key_path}")
            return key_path, enc_file

        # with open(key_path, 'r') as f:
        #     self.key = f.read() 

        # if self.key:
        #     print(self.key)
        #     return True
        # else:
        #     print("Key not found.")
        #     return False
    
    #Forawading file to specific zonal controller
    def file_forwader(self):
        print(self.config_data)
        update = self.config_data["update_details"]
        ip = update["ip"]
        username = update["username"]
        password = update["password"]
        target_dir = update["target_dir"]
        local_path = os.path.join(os.getenv("UNZIP_PATH"), self.filename) # File stored in local machine
        fileName = self.filename # Folder name
        ver_details = self.config_data["update_details"]

        try:
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh.connect(ip, username=username, password=password)
            sftp = ssh.open_sftp()

            #Incase of files
            if os.path.isfile(local_path):
                sftp.put(local_path, os.path.join(target_dir, fileName))
                print(f"Uploaded file: {fileName} to {ip}:{target_dir}")
            
            #Incase of folders
            elif os.path.isdir(local_path):
                remote_path = os.path.join(target_dir, fileName)
                def send_dir(sftp, local_path, remote_path):
                    try:
                        sftp.mkdir(remote_path)
                    except IOError:
                        pass  # dir already exists
                    
                    for file in os.listdir(local_path):
                        local_file = os.path.join(local_path, file)
                        remote_file = os.path.join(remote_path, file)
                        if os.path.isfile(local_file):
                            sftp.put(local_file, remote_file)
                        else:
                            send_dir(sftp, local_file, remote_file)

            send_dir(sftp, local_path, remote_path)
            print(f"Uploaded folder: {fileName} to {ip}:{target_dir}")

            sftp.close()
            ssh.close()
            print(f"File {self.filename} forwarded to {ip}:{target_dir}")
        
        except Exception as e:
            print(f"Failed to forward file: {e}")
            ver_details["status"] = False
            return ver_details

        ver_details["status"] = True
        return ver_details




    
    
    



    

