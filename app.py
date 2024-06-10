from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
import requests
import os

# Load configuration
import config

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = config.SQLALCHEMY_DATABASE_URI
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = config.SQLALCHEMY_TRACK_MODIFICATIONS
CORS(app)
db = SQLAlchemy(app)

external_api_url = config.EXTERNAL_API_ENDPOINT

class ChatSession(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    valid = db.Column(db.Boolean, default=False)
    messages = db.relationship('Message', backref='session', lazy=True)

class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    role = db.Column(db.String(10), nullable=False)
    content = db.Column(db.Text, nullable=False)
    session_id = db.Column(db.Integer, db.ForeignKey('chat_session.id'), nullable=False)

# Ensure the database and tables are created within the application context
with app.app_context():
    db.create_all()

current_session_id = None

@app.route('/api/health', methods=['GET'])
def health_check():
    try:
        response = requests.get(config.EXTERNAL_API_ROOT)
        if response.status_code == 200:
            external_api_status = 'healthy'
        else:
            external_api_status = 'unhealthy'
    except requests.RequestException as e:
        external_api_status = 'unhealthy'

    return jsonify({'status': 'healthy', 'external_api_status': external_api_status}), 200

@app.route('/api/sessions', methods=['GET'])
def get_sessions():
    sessions = ChatSession.query.filter_by(valid=True).all()
    return jsonify([{'id': session.id} for session in sessions])

@app.route('/api/new_chat', methods=['POST'])
def new_chat():
    global current_session_id
    new_session = ChatSession()
    db.session.add(new_session)
    db.session.commit()
    current_session_id = new_session.id
    return jsonify({'session_id': new_session.id})

@app.route('/api/end_chat', methods=['POST'])
def end_chat():
    global current_session_id
    end_message = Message(role='system', content='exit', session_id=current_session_id)
    db.session.add(end_message)
    db.session.commit()
    current_session_id = None
    return '', 204

@app.route('/api/load_chat/<int:session_id>', methods=['GET'])
def load_chat(session_id):
    messages = Message.query.filter_by(session_id=session_id).all()
    return jsonify([{'role': m.role, 'content': m.content} for m in messages])

@app.route('/api/chat', methods=['POST'])
def chat():
    global current_session_id
    user_input = request.json.get('message')
    if not user_input:
        return jsonify({'error': 'No input provided'}), 400

    user_message = Message(role='user', content=user_input, session_id=current_session_id)
    db.session.add(user_message)
    db.session.commit()

    # Run ilab chat command
    response = run_ilab_chat(user_input)
    assistant_response = response.json().get('choices', [{}])[0].get('message', {}).get('content', 'No response')

    if assistant_response:
        bot_message = Message(role='assistant', content=assistant_response.strip(), session_id=current_session_id)
        db.session.add(bot_message)
        db.session.commit()

        # Mark session as valid
        current_session = ChatSession.query.get(current_session_id)
        current_session.valid = True
        db.session.commit()

    return jsonify({'response': assistant_response})

@app.route('/api/reset', methods=['POST'])
def reset():
    global current_session_id
    db_path = os.path.join(config.basedir, "chat.db")
    if os.path.exists(db_path):
        os.remove(db_path)
        print("Deleted chat.db")
    else:
        print("chat.db does not exist.")
    with app.app_context():
        db.create_all()
        print("Recreated database and tables")
    current_session_id = None
    return '', 204

def run_ilab_chat(message):
    try:
        session_messages = Message.query.filter_by(session_id=current_session_id).all()
        messages = [{'role': m.role, 'content': m.content} for m in session_messages]
        response = requests.post(
            external_api_url,
            json={
                'model': 'gpt-3.5-turbo',
                'messages': [
                    {'role': 'system', 'content': 'You are a helpful assistant.'},
                    *messages
                ]
            }
        )
        response.raise_for_status()
        return response
    except requests.RequestException as e:
        return jsonify({'error': str(e)})

if __name__ == '__main__':
    app.run(host=config.HOST, port=config.PORT, debug=True)
