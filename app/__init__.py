import os
from flask import Flask
from flask_login import LoginManager
from mongoengine import connect
from authlib.integrations.flask_client import OAuth

login_manager = LoginManager()
oauth = OAuth()

def create_app():
    app = Flask(__name__)
    
    # Configuration
    # SECURITY WARNING: Change 'dev-key-secret-123' in production!
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-key-secret-123')
    app.config['UPLOAD_FOLDER'] = os.path.join(app.root_path, 'static', 'uploads')
    app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024 
    
    # MongoDB Connection
    # REQUIRED: Set MONGODB_URI env var (e.g. in Render or .env)
    mongo_uri = os.environ.get('MONGODB_URI')
    if not mongo_uri:
        print("WARNING: MONGODB_URI not set. Using local SQLite fallback or failing.")
        mongo_uri = 'mongodb://localhost:27017/titan_local' # Safe local default
    
    connect(host=mongo_uri)

    # Google OAuth Config
    # REQUIRED: Set GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET env vars
    app.config['GOOGLE_CLIENT_ID'] = os.environ.get('GOOGLE_CLIENT_ID', 'YOUR_GOOGLE_CLIENT_ID')
    app.config['GOOGLE_CLIENT_SECRET'] = os.environ.get('GOOGLE_CLIENT_SECRET', 'YOUR_GOOGLE_CLIENT_SECRET')
    
    oauth.init_app(app)
    oauth.register(
        name='google',
        client_id=app.config['GOOGLE_CLIENT_ID'],
        client_secret=app.config['GOOGLE_CLIENT_SECRET'],
        server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
        client_kwargs={'scope': 'openid email profile'}
    )

    # Initialize Plugins
    login_manager.init_app(app)
    login_manager.login_view = 'main.login'

    # Register Blueprints
    from app.routes import main
    app.register_blueprint(main)
    
    # Default User Initialization
    with app.app_context():
        from app.models import User
        try:
            if not User.objects(username='titan').first():
                default_user = User(username='titan', password='123', 
                                    height=175, weight=70, age=25, 
                                    goal_calories=2200, goal_protein=160, goal_water=10)
                default_user.save()
                print("Default user 'titan' created in MongoDB.")
        except Exception as e:
            print(f"Database warning (safe to ignore if first run): {e}")

    return app