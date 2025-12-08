import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, "uploads")

MONGO_URI = "mongodb://localhost:27017/nss_portal"
JWT_SECRET_KEY =  "ssn_nss_super_secret_key_2025"
