from .extensions import db
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    password_hash = db.Column(db.String(150))
    is_admin = db.Column(db.Boolean, default=False, nullable=False)
    # Relationship to the audio files this user uploaded
    audio_files = db.relationship('AudioFile', backref='uploader', lazy=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

# NEW: AudioFile model to store metadata
class AudioFile(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(300), nullable=False)
    track_type = db.Column(db.String(50), nullable=False) # 'mainsound', 'plussound', or 'mix_elements'
    is_global = db.Column(db.Boolean, default=False, nullable=False) # This is our "tag" for protection
    # Foreign key to link to the User who uploaded it
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    # Make sure a filename is unique for its track type
    __table_args__ = (db.UniqueConstraint('filename', 'track_type', name='_filename_track_type_uc'),)