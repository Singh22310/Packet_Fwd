import os
import json
import zipfile
import shutil
from dotenv import load_dotenv
from tihan.sdv.securetransfer.rsa_utils import generate_public_key, generate_private_key
from tihan.sdv.securetransfer.file_transfer import FileReceiver 
from filehandler import FileHandler

load_dotenv()

class FileCryptography(FileHandler):
    def __init__(self):
        # super().__init__(filename)
        if os.path.exists(os.getenv("PRIVATE_KEY_FILE")) and os.path.exists(os.getenv("PUBLIC_KEY_FILE")):
            self.private_key_file = os.getenv("PRIVATE_KEY_FILE")
            self.public_key_file = os.getenv("PUBLIC_KEY_FILE")
            with open(self.private_key_file, 'rb') as f:
                self.private_key = f.read()
        else:
            self.keyGeneration()


    def keyGeneration(self):
        privateFile = generate_private_key()
        publicFile = generate_public_key(privateFile)
        # Ensure the KEYS_PATH directory exists and moved the files
        os.makedirs("keys/", exist_ok=True)
        shutil.move(privateFile, os.path.join("keys/", os.path.basename(privateFile)))
        shutil.move(publicFile, os.path.join("keys/", os.path.basename(publicFile)))
        
        #Load the files
        self.private_key_file = os.getenv("PRIVATE_KEY_FILE")
        self.public_key_file = os.getenv("PUBLIC_KEY_FILE")
        print(f"Private key saved to {self.private_key_file}")
        print(f"Public key saved to {self.public_key_file}")
        
        with open(self.private_key_file, 'rb') as f:
            self.private_key = f.read()
        print("Keys generated successfully.")
        
    def fileDecrypt(self, fileList):
        if self.private_key:
            for f in fileList:
                if f.endswith('.enc') and "key" in f:
                    key_file = f
                else:
                    enc_file = f
            receiver = FileReceiver(self.private_key)
            key_path = os.path.join(os.getenv("UNZIP_PATH"), key_file)
            key = receiver.decrypt_key(key_path)
            encryptFile = os.path.join(os.getenv("UNZIP_PATH"), enc_file)
            decryptFilename =  "updateFile.zip"
            decryptFilePath = os.path.join(os.getenv("UNZIP_PATH"), decryptFilename)
            receiver.decrypt_file(encryptFile, key, decryptFilePath)
            print(f"File decrypted successfully and saved to {decryptFilePath}")
            status = True
        else:
            print("Private key not found. Cannot decrypt the file.")
            return False, None
        
        return status, decryptFilePath, decryptFilename
