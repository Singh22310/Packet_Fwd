import os
import json
import zipfile
from dotenv import load_dotenv
from tihan.sdv.securetransfer.rsa_utils import generate_public_key, generate_private_key
from tihan.sdv.securetransfer.file_transfer import FileReceiver 
from filehandler import FileHandler

load_dotenv()

class FileCryptography(FileHandler):
    def __init__(self):
        super().__init__(filename)
        if os.path.exists(os.getenv("PUBLIC_KEY_PATH")) and os.path.exists(os.getenv("PRIVATE_KEY_PATH")):
            self.private_key_file = os.getenv("PRIVATE_KEY_PATH")
            self.public_key_file = os.getenv("PUBLIC_KEY_PATH")
            with open(self.private_key_file, 'rb') as f:
                self.private_key = f.read()
        else:
            self.private_key_file = None
            self.public_key_file = None
            self.private_key = None
    
    def keyGeneration(self):
        if self.private_key_file and self.public_key_file:
            print("Keys already exist.")
            
        else:
            self.private_key_file = generate_private_key()
            self.public_key_file = generate_public_key(self.private_key_file)
            print(f"Private key saved to {self.private_key_file}")
            print(f"Public key saved to {self.public_key_file}")
            with open(self.private_key_file, 'rb') as f:
                self.private_key = f.read()
            print("Keys generated successfully.")
        
    def fileDecrypt(self):
        if self.private_key:
            receiver = FileReceiver(self.private_key)
            
