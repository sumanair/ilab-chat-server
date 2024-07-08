from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class Folder(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    sessions = db.relationship('ChatSession', backref='folder', lazy=True)

class ChatSession(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    valid = db.Column(db.Boolean, default=False)
    name = db.Column(db.String(100), nullable=True)
    folder_id = db.Column(db.Integer, db.ForeignKey('folder.id'), nullable=True)
    messages = db.relationship('Message', backref='session', lazy=True)

class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    role = db.Column(db.String(10), nullable=False)
    content = db.Column(db.Text, nullable=False)
    session_id = db.Column(db.Integer, db.ForeignKey('chat_session.id'), nullable=False)

def initialize_db(app):
    with app.app_context():
        db.init_app(app)
        db.create_all()
