from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    fics = db.relationship('Fic', backref='owner', lazy=True, cascade="all, delete-orphan")

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class Fic(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    author = db.Column(db.String(100), nullable=False)
    fandom = db.Column(db.String(200), nullable=False)
    relationship = db.Column(db.String(200), nullable=True)
    summary = db.Column(db.Text, nullable=True)
    tags = db.Column(db.Text, nullable=True)
    status = db.Column(db.String(50), nullable=True)
    date_published = db.Column(db.String(50), nullable=True)
    content = db.Column(db.Text, nullable=False)
    source_url = db.Column(db.String(500), nullable=True)
    
    # Campos do usuário
    date_read = db.Column(db.Date, nullable=True)
    comment = db.Column(db.String(500), nullable=True)
    
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)