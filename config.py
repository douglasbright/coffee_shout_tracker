
import os

class Config:
    SECRET_KEY = os.getenv('SECRET_KEY', 'mysecret')
    SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URL', 'sqlite:///coffee_shout.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    WTF_CSRF_ENABLED = True
    WTF_CSRF_SECRET_KEY = 'your_csrf_secret_key'

    # Global admin details (better stored as environment variables)
    ADMIN_EMAIL = os.getenv('ADMIN_EMAIL', 'admin@mail.com')  # Store in env variable in production
    ADMIN_PASSWORD = os.getenv('ADMIN_PASSWORD', '3684')    # Store in env variable in production
