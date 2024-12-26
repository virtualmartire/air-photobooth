import sqlite3
from flask import g, current_app
from threading import Lock

DATABASE = 'photobooth.db'
db_lock = Lock()

def get_db():
    if 'db' not in g:
        g.db = sqlite3.connect(DATABASE, timeout=20)
        g.db.row_factory = sqlite3.Row
    return g.db

def close_db(e=None):
    db = g.pop('db', None)
    if db is not None:
        db.close()

def init_db(app):
    with app.app_context():
        db = get_db()
        with current_app.open_resource('schema.sql', mode='r') as f:
            db.cursor().executescript(f.read())
        db.commit()

def get_current_photo():
    with db_lock:
        db = sqlite3.connect(DATABASE, timeout=20)
        try:
            cursor = db.cursor()
            cursor.execute('SELECT filename FROM current_photo LIMIT 1')
            result = cursor.fetchone()
            return result[0] if result else None
        finally:
            db.close()

def update_current_photo(filename):
    with db_lock:
        db = sqlite3.connect(DATABASE, timeout=20)
        try:
            cursor = db.cursor()
            cursor.execute('DELETE FROM current_photo')
            cursor.execute('INSERT INTO current_photo (filename) VALUES (?)', (filename,))
            db.commit()
        finally:
            db.close()
