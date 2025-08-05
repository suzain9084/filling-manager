import sys, os
sys.path.append(os.getcwd())

from dotenv import load_dotenv
from flask import Flask
from flask_cors import CORS
from filing_app.routes.filing_routes import filing_routes_bp
import os

load_dotenv()

app = Flask(__name__)
port = os.getenv("PORT")
CORS(app, resources={r"/*": {"origins": ["http://localhost:5173", "https://your-frontend-domain.com"]}}, supports_credentials=True) 

app.register_blueprint(filing_routes_bp)

if __name__ == "__main__":
    app.run(debug=True,port=5000)