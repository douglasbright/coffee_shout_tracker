import os

class Config:
    SECRET_KEY = os.getenv('SECRET_KEY')
    SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URL')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    WTF_CSRF_ENABLED = True
    WTF_CSRF_SECRET_KEY = os.getenv('WTF_CSRF_SECRET_KEY')

    # Global admin details (better stored as environment variables)
    ADMIN_EMAIL = os.getenv('ADMIN_EMAIL')
    ADMIN_PASSWORD = os.getenv('ADMIN_PASSWORD')

    # Debugging statements
    print(f"SECRET_KEY: {SECRET_KEY}")
    print(f"DATABASE_URL: {SQLALCHEMY_DATABASE_URI}")
    print(f"WTF_CSRF_SECRET_KEY: {WTF_CSRF_SECRET_KEY}")
    print(f"ADMIN_EMAIL: {ADMIN_EMAIL}")
    print(f"ADMIN_PASSWORD: {ADMIN_PASSWORD}")
