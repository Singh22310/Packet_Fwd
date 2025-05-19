import os
import requests
from dotenv import load_dotenv

load_dotenv()

response = requests.get(os.getenv("CHECK_UPDATE_API"))
data = response.json()
version_data = data["Update details"]
print(version_data["id"])