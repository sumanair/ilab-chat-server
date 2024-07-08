import os
import sys
from sqlalchemy import create_engine, MetaData, Table, text

# Add the parent directory to the sys.path to import config
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config

engine = create_engine(config.SQLALCHEMY_DATABASE_URI)
meta = MetaData()

# Reflect the existing database
meta.reflect(bind=engine)

# Access the chat_session table
chat_session = Table('chat_session', meta, autoload_with=engine)

# Check if the folder_id column exists, if not, add it
if not hasattr(chat_session.c, 'folder_id'):
    with engine.connect() as conn:
        conn.execute(text('ALTER TABLE chat_session ADD COLUMN folder_id INTEGER REFERENCES folder(id)'))

print("Migration completed successfully!")
