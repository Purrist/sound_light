from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager

db = SQLAlchemy()
login_manager = LoginManager()
login_manager.login_view = 'auth.login'

@login_manager.user_loader
def load_user(user_id):
    # CRITICAL CHANGE: Import User model *inside* the function.
    # This breaks the import cycle because the import only happens when the function is actually called,
    # by which time all modules have been loaded.
    from .models import User
    return User.query.get(int(user_id))