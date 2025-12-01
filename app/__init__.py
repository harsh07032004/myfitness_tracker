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
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-key-secret-123')
    app.config['UPLOAD_FOLDER'] = os.path.join(app.root_path, 'static', 'uploads')
    app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024 
    
    # MongoDB Connection
    mongo_uri = os.environ.get('MONGODB_URI', 'mongodb+srv://AI_GEMINI:db123@cluster0.fmugkof.mongodb.net/calorielens?retryWrites=true&w=majority&appName=Cluster0')
    connect(host=mongo_uri)

    # Google OAuth Config
    app.config['GOOGLE_CLIENT_ID'] = os.environ.get('GOOGLE_CLIENT_ID', '493532333175-qvrnmh9734q0n2ir09o83ge003ldckpb.apps.googleusercontent.com')
    app.config['GOOGLE_CLIENT_SECRET'] = os.environ.get('GOOGLE_CLIENT_SECRET', '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')
    
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