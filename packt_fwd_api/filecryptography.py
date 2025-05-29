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
            self.keyGeneration()
        else:
            self.private_key_file = os.getenv("PRIVATE_KEY_PATH", "private_key.pem")
            self.public_key_file = os.getenv("PUBLIC_KEY_PATH", "public_key.pem")
            with open(self.private_key_file, 'rb') as f:
                self.private_key = f.read()

    def keyGeneration(self):
        privateFile = generate_private_key()
        publicFile = generate_public_key(privateFile)
        # Ensure the KEYS_PATH directory exists and moved the files
        os.makedirs(os.getenv("KEYS_PATH"), exist_ok=True)
        shutil.move(privateFile, os.path.join(target_dir, os.path.basename(privateFile)))
        shutil.move(publicFile, os.path.join(target_dir, os.path.basename(publicFile)))
        
        #Load the files
        self.private_key_file = os.path.join(os.getenv("KEYS_PATH"), "private_key.pem")
        self.public_key_file = os.path.join(os.getenv("KEYS_PATH"), "public_key.pem")
        print(f"Private key saved to {self.private_key_file}")
        print(f"Public key saved to {self.public_key_file}")
        
        with open(self.private_key_file, 'rb') as f:
            self.private_key = f.read()
        print("Keys generated successfully.")
        
    def fileDecrypt(self, key_path, key_file, enc_file):
        if self.private_key:
            receiver = FileReceiver(self.private_key)
            key = receiver.decrypt_key(key_path)
            encryptFile = os.path.join(os.getenv("UNZIP_PATH"), enc_file)
            decryptFile = os.path.join(os.getenv("UNZIP_PATH"), "updateFile.zip")
            receiver.decrypt_file(encryptFile, key, decryptFile)
            print(f"File decrypted successfully and saved to {decryptFile}")
        
        else:
            print("Private key not found. Cannot decrypt the file.")
            return False
        
        return True
