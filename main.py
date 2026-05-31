from flask import Flask, send_from_directory
from flask_cors import CORS
from extensions import db, mongo
from models import Movie, User
from movieService import movieService_bp
from reviewService import review_bp
from authService import auth_bp
from analyticsService import analytics_bp
from dotenv import load_dotenv
from werkzeug.middleware.proxy_fix import ProxyFix
import os

# # Load environment variables from .env file
load_dotenv()

# Create Flash app
def create_app():
    app = Flask(__name__, static_folder=".", static_url_path="")
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-secret-change-me')
    app.config['SESSION_COOKIE_HTTPONLY'] = True
    app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
    app.config['SESSION_COOKIE_SECURE'] = os.getenv('SESSION_COOKIE_SECURE', 'false').lower() == 'true'
    app.config['PREFERRED_URL_SCHEME'] = 'https' if app.config['SESSION_COOKIE_SECURE'] else 'http'
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)


    # SQL Database configuration
    app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'sqlite:///movies.db')   # Povemo, da bomo uporabljal SQLite bazo z imenom movies.db
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False            # Izklopimo sledenje spremembam, ker ni potrebno in lahko povzroči dodatno porabo pomnilnika


    # MongoDB configuration
    app.config["MONGO_URI"] = os.getenv("MONGO_URI", "mongodb://localhost:27017/movieDB")
    mongo.init_app(app)


    # Povežemo SQLAlchemy z našo Flask aplikacijo (db objekt je it extensions.py)
    db.init_app(app)    


    # Register Blueprints
    app.register_blueprint(movieService_bp, url_prefix='/movies')
    app.register_blueprint(review_bp, url_prefix='/api/reviews')
    app.register_blueprint(auth_bp)
    app.register_blueprint(analytics_bp)

    # Enable CORS for the app - omogoča, da lahko frontend komunicira z backend 
    CORS(app, supports_credentials=True)

    with app.app_context():
        db.create_all()

    
    # Homepage route
    @app.route("/")
    def home():
        return send_from_directory(app.static_folder, 'index.html')
        
    return app


# Expose app for production WSGI servers (for example, Gunicorn)
app = create_app()


# Run the app
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "5000")), debug=os.getenv("FLASK_DEBUG", "0") == "1")