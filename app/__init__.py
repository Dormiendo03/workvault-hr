from flask import Flask
from flask_login import LoginManager
from config import config
import os

login_manager = LoginManager()

def create_app(config_name='default'):
    """Application factory pattern"""
    # Set template and static folders relative to project root
    import os
    basedir = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
    template_dir = os.path.join(basedir, 'templates')
    static_dir = os.path.join(basedir, 'static')
    
    app = Flask(__name__, 
                template_folder=template_dir,
                static_folder=static_dir)
    app.config.from_object(config[config_name])
    
    # Initialize extensions
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Please log in to access this page.'
    login_manager.login_message_category = 'info'
    
    # Create necessary directories
    os.makedirs(app.config['FACE_ENCODINGS_PATH'], exist_ok=True)
    
    # Create reports directory with absolute path
    reports_dir = os.path.join(basedir, 'reports')
    os.makedirs(reports_dir, exist_ok=True)
    
    # Register blueprints
    from app.routes import auth, admin, hr, employee, notifications, attendance_corrections
    app.register_blueprint(auth.bp)
    app.register_blueprint(admin.bp)
    app.register_blueprint(hr.bp)
    app.register_blueprint(employee.bp)
    app.register_blueprint(notifications.bp)
    app.register_blueprint(attendance_corrections.bp)
    
    # Register user loader
    from app.models.user import User
    
    @login_manager.user_loader
    def load_user(user_id):
        return User.get_by_id(user_id)
    
    return app
