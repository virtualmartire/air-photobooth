from flask import Flask, render_template, request, flash, redirect, url_for, session, send_file
import os
from werkzeug.utils import secure_filename
from database import init_db, get_db, close_db, get_current_photo, update_current_photo, DATABASE
from threading import Thread
import time
from datetime import datetime
from functools import wraps
import sqlite3
import secrets
import zipfile
from io import BytesIO

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def init_app():

    app = Flask(__name__)

    app.config['SECRET_KEY'] = secrets.token_hex(16)        # to manage cryptographic things
    app.config['PASSWORD'] = os.environ.get('PASSWORD')
    app.config['UPLOAD_FOLDER'] = 'static/uploads'
    app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024

    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    
    init_db(app)

    # Scan and add existing photos to database
    with app.app_context():
        db = get_db()
        cursor = db.cursor()
        for filename in os.listdir(app.config['UPLOAD_FOLDER']):
            if allowed_file(filename):
                cursor.execute('INSERT OR IGNORE INTO photos (filename, upload_date) VALUES (?, ?)',
                             (filename, datetime.now()))
        db.commit()
    
    app.teardown_appcontext(close_db)
    
    return app

app = init_app()

def require_password(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('authenticated'):
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        if request.form.get('password') == app.config['PASSWORD']:
            session['authenticated'] = True
            return redirect(url_for('index'))
        flash('Incorrect password')
    return render_template('login.html')

@app.route('/')
@require_password
def index():
    current_photo = get_current_photo()
    return render_template('index.html', photo=current_photo)

@app.route('/upload', methods=['POST'])
@require_password
def upload_photo():
    if 'photo' not in request.files:
        flash('No file uploaded')
        return redirect(url_for('index'))
    
    file = request.files['photo']
    if file.filename == '':
        flash('No file selected')
        return redirect(url_for('index'))
    
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_')
        filename = timestamp + filename
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(file_path)
        
        db = get_db()
        cursor = db.cursor()
        cursor.execute('INSERT INTO photos (filename, upload_date) VALUES (?, ?)',
                      (filename, datetime.now()))
        db.commit()
        
        flash('Photo uploaded successfully!')
        return redirect(url_for('index'))
    
    flash('Invalid file type')
    return redirect(url_for('index'))

@app.route('/download', methods=['GET', 'POST'])
@require_password
def download():
    if request.method == 'POST':
        if request.form.get('download_password') == os.environ.get('DOWNLOAD_PASSWORD'):
            # Create zip file in memory
            memory_file = BytesIO()
            with zipfile.ZipFile(memory_file, 'w') as zf:
                db = get_db()
                cursor = db.cursor()
                cursor.execute('SELECT filename FROM photos')
                photos = cursor.fetchall()
                
                for photo in photos:
                    file_path = os.path.join(app.config['UPLOAD_FOLDER'], photo['filename'])
                    if os.path.exists(file_path):
                        zf.write(file_path, photo['filename'])
            
            memory_file.seek(0)
            return send_file(
                memory_file,
                mimetype='application/zip',
                as_attachment=True,
                download_name='photobooth_photos.zip'
            )
        flash('Incorrect download password')
    return render_template('download.html')

def update_displayed_photo():
    """Update the currently displayed photo (runs in background)"""
    while True:
        try:
            db = sqlite3.connect(DATABASE, timeout=20)
            cursor = db.cursor()
            cursor.execute('SELECT filename FROM photos ORDER BY RANDOM() LIMIT 1')
            random_photo = cursor.fetchone()
            db.close()
            
            if random_photo:
                update_current_photo(random_photo[0])
        except Exception as e:
            print(f"Error updating displayed photo: {e}")
        finally:
            time.sleep(120)  # Wait 2 minutes

if __name__ == '__main__':

    # Start background thread for photo updates
    photo_thread = Thread(target=update_displayed_photo, daemon=True)
    photo_thread.start()
    
    app.run(debug=True)
