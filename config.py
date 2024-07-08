import os

basedir = os.path.abspath(os.path.dirname(__file__))

# Database configuration
SQLALCHEMY_DATABASE_URI = f'sqlite:///{os.path.join(basedir, "chat.db")}'
SQLALCHEMY_TRACK_MODIFICATIONS = False

# External API configuration
EXTERNAL_API_ROOT = 'http://127.0.0.1:8000'
EXTERNAL_API_ENDPOINT = f'{EXTERNAL_API_ROOT}/v1/chat/completions'

# Flask app configuration
HOST = '127.0.0.1'
PORT = 5001

# CORS configuration
CORS_ORIGINS = ["http://localhost:3000", "http://127.0.0.1:3000", "*"]
CORS_HEADERS = ['Content-Type', 'Authorization']
