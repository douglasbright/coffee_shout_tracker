import os
from flask import Flask, redirect, url_for, flash
from flask_wtf import CSRFProtect
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_migrate import Migrate
from config import Config  # Import the config class
from werkzeug.security import generate_password_hash
from .context_processors import inject_quote
from .utils import time_since 
from datetime import datetime

db = SQLAlchemy()
login_manager = LoginManager()
migrate = Migrate()
csrf = CSRFProtect()

def create_app():
    app = Flask(__name__)
    
    # Load configuration from the Config class
    app.config.from_object(Config)
    
    # Initialize extensions
    db.init_app(app)
    login_manager.init_app(app)
    migrate.init_app(app, db)

    # Import the User model (for login_manager and migrations)
    from .models import User

    # User loader function for Flask-Login
    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    # Set the login view for unauthorized users
    login_manager.login_view = 'auth.login'

    # Customize unauthorized access handling
    @login_manager.unauthorized_handler
    def unauthorized():
        flash('You need to log in to access this page.', 'danger')
        return redirect(url_for('main.home'))

    # Register blueprints
    from .routes import main
    from .activity_routes import activity
    from .auth_routes import auth
    from .shout_routes import shout
    from .profile_routes import profile
    from .quote_routes import quote
    from .coffee_shop_routes import coffee_shop

    app.register_blueprint(main)
    app.register_blueprint(activity)
    app.register_blueprint(auth)
    app.register_blueprint(shout)
    app.register_blueprint(profile)
    app.register_blueprint(quote)
    app.register_blueprint(coffee_shop)

    # Register the context processor for injecting quotes
    app.context_processor(inject_quote)

    # Define the time_since filter
    def time_since(dt):
        now = datetime.utcnow()
        diff = now - dt
        if diff.days > 0:
            return f"{diff.days} days"
        elif diff.seconds > 3600:
            return f"{diff.seconds // 3600} hours"
        elif diff.seconds > 60:
            return f"{diff.seconds // 60} minutes"
        else:
            return "just now"

    # Register the time_since filter
    app.jinja_env.filters['time_since'] = time_since

    # Ensure database tables are created before checking for admin
    with app.app_context():
        db.create_all()  # Create all tables if they don't already exist

        # Check if an admin exists, and create one if not
        admin_exists = User.query.filter_by(is_admin=True).first()
        if not admin_exists:
            admin = User(
                username='admin',
                email=app.config['ADMIN_EMAIL'],
                password=generate_password_hash(app.config['ADMIN_PASSWORD'], method='pbkdf2:sha256'),
                is_admin=True
            )
            db.session.add(admin)
            db.session.commit()
            print(f"No admin found, default admin created: {app.config['ADMIN_EMAIL']}")

    return app
