import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY = os.getenv('SECRET_KEY', 'pcos_secret_key_2026_xyz')
    DATABASE_TYPE = os.getenv('DATABASE_TYPE', 'sqlite')
    DATABASE_URL = os.getenv('DATABASE_URL', 'database.db')
    MONGO_URI = os.getenv('MONGO_URI', 'mongodb://localhost:27017/pcos_prediction')
    DEBUG = os.getenv('DEBUG', 'True') == 'True'
    PORT = int(os.getenv('PORT', 5000))