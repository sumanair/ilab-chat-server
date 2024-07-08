from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
import os
import logging

# Load configuration
import config
from chathistory import db, ChatSession, Message, Folder, initialize_db

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = config.SQLALCHEMY_DATABASE_URI
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = config.SQLALCHEMY_TRACK_MODIFICATIONS

# Allow CORS from React frontend
CORS(app, resources={r"/*": {"origins": config.CORS_ORIGINS}}, supports_credentials=True)

@app.after_request
def after_request(response):
    response.headers['Access-Control-Allow-Origin'] = config.CORS_ORIGINS[0]
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type,Authorization'
    response.headers['Access-Control-Allow-Methods'] = 'GET,PUT,POST,DELETE,OPTIONS'
    return response

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

external_api_url = config.EXTERNAL_API_ENDPOINT

# Initialize the database
initialize_db(app)

current_session_id = None

@app.route('/api/health', methods=['GET'])
def health_check():
    try:
        response = requests.get(config.EXTERNAL_API_ROOT)
        if response.status_code == 200:
            external_api_status = 'healthy'
        else:
            external_api_status = 'unhealthy'
    except requests.RequestException:
        external_api_status = 'unhealthy'

    return jsonify({'status': 'healthy', 'external_api_status': external_api_status}), 200

@app.route('/api/folders', methods=['GET'])
def get_folders():
    folders = Folder.query.all()
    return jsonify([{'id': folder.id, 'name': folder.name} for folder in folders])

@app.route('/api/folders', methods=['POST'])
def create_folder():
    folder_name = request.json.get('name')
    if not folder_name:
        return jsonify({'error': 'Folder name is required'}), 400
    new_folder = Folder(name=folder_name)
    db.session.add(new_folder)
    db.session.commit()
    return jsonify({'id': new_folder.id, 'name': new_folder.name}), 201

@app.route('/api/folders/<int:folder_id>', methods=['PUT'])
def update_folder(folder_id):
    new_name = request.json.get('name')
    if not new_name:
        return jsonify({'error': 'Folder name is required'}), 400
    folder = Folder.query.get(folder_id)
    if not folder:
        return jsonify({'error': 'Folder not found'}), 404
    folder.name = new_name
    db.session.commit()
    return jsonify({'id': folder.id, 'name': folder.name}), 200

@app.route('/api/folders/<int:folder_id>', methods=['DELETE'])
def delete_folder(folder_id):
    folder = Folder.query.get(folder_id)
    if not folder:
        return jsonify({'error': 'Folder not found'}), 404
    db.session.delete(folder)
    db.session.commit()
    return '', 204

@app.route('/api/folders/<int:folder_id>/delete_with_contents', methods=['DELETE'])
def delete_folder_with_contents(folder_id):
    folder = Folder.query.get(folder_id)
    if not folder:
        return jsonify({'error': 'Folder not found'}), 404

    try:
        sessions = ChatSession.query.filter_by(folder_id=folder_id).all()
        for session in sessions:
            messages = Message.query.filter_by(session_id=session.id).all()
            for message in messages:
                db.session.delete(message)
            db.session.delete(session)
        
        db.session.delete(folder)
        db.session.commit()
        return '', 204
    except Exception as e:
        db.session.rollback()
        logger.exception("Error during delete_folder_with_contents")
        return jsonify({'error': str(e)}), 500

@app.route('/api/sessions', methods=['GET'])
def get_sessions():
    folder_id = request.args.get('folder_id')
    if folder_id:
        sessions = ChatSession.query.filter_by(valid=True, folder_id=folder_id).all()
    else:
        sessions = ChatSession.query.filter_by(valid=True, folder_id=None).all()
    return jsonify([{'id': session.id, 'name': session.name, 'folder_id': session.folder_id} for session in sessions])

@app.route('/api/sessions/<int:session_id>/move', methods=['POST'])
def move_session(session_id):
    folder_id = request.json.get('folder_id')
    session = ChatSession.query.get(session_id)
    if not session:
        return jsonify({'error': 'Session not found'}), 404
    if folder_id is not None:
        session.folder_id = folder_id
    else:
        session.folder_id = None
    db.session.commit()
    return '', 204

@app.route('/api/new_chat', methods=['POST'])
def new_chat():
    global current_session_id
    folder_id = request.json.get('folder_id')
    new_session = ChatSession(folder_id=folder_id)
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
    global current_session_id
    current_session_id = session_id
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
    try:
        with app.app_context():
            # Delete all records from all tables
            db.session.query(Message).delete()
            db.session.query(ChatSession).delete()
            db.session.query(Folder).delete()
            db.session.commit()
            print("Deleted all contents from the database")
        current_session_id = None
        return '', 204
    except Exception as e:
        logger.exception("Error during reset")
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@app.route('/api/delete_sessions', methods=['POST'])
def delete_sessions():
    session_ids = request.json.get('ids', [])
    try:
        for session_id in session_ids:
            session = ChatSession.query.get(session_id)
            if session:
                messages = Message.query.filter_by(session_id=session.id).all()
                for message in messages:
                    db.session.delete(message)
                db.session.delete(session)
        db.session.commit()
        return '', 204
    except Exception as e:
        db.session.rollback()
        logger.exception("Error during delete_sessions")
        return jsonify({'error': str(e)}), 500

@app.route('/api/update_session_name', methods=['POST'])
def update_session_name():
    session_id = request.json.get('session_id')
    new_name = request.json.get('new_name')
    try:
        session = ChatSession.query.get(session_id)
        if session:
            session.name = new_name
            db.session.commit()
            return '', 204
        else:
            return jsonify({'error': 'Session not found'}), 404
    except Exception as e:
        logger.exception("Error during update_session_name")
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@app.route('/api/all_sessions', methods=['GET'])
def all_sessions():
    folders = Folder.query.all()
    folder_data = []
    for folder in folders:
        sessions = ChatSession.query.filter_by(folder_id=folder.id, valid=True).all()
        folder_data.append({
            'id': folder.id,
            'name': folder.name,
            'sessions': [{'id': session.id, 'name': session.name} for session in sessions]
        })
    
    no_folder_sessions = ChatSession.query.filter_by(folder_id=None, valid=True).all()
    no_folder_data = [{'id': session.id, 'name': session.name} for session in no_folder_sessions]
    
    return jsonify({'folders': folder_data, 'no_folder_sessions': no_folder_data})

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
        logger.exception("Error during run_ilab_chat")
        return jsonify({'error': str(e)})

if __name__ == '__main__':
    app.run(host=config.HOST, port=config.PORT, debug=True)
