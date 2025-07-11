from flask import Flask, render_template, request, redirect, session, jsonify
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
import os
from db_config import get_connection

app = Flask(__name__)
app.secret_key = 'your_secret_key'

# Upload folder setup
UPLOAD_FOLDER = 'static/uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16 MB max

# Allowed file extensions
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# ---------- ROUTES ----------

@app.route('/')
def home():
    return render_template('index.html', logged_in='user_id' in session)

@app.route('/register', methods=['GET', 'POST'])
def register():
    conn = None
    message = None
    error = None
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password = generate_password_hash(request.form['password'])

        try:
            conn = get_connection()
            cur = conn.cursor()  # NO dictionary=True here
            cur.execute("SELECT * FROM users WHERE email=%s", (email,))
            if cur.fetchone():
                error = "User already exists"
            else:
                cur.execute("INSERT INTO users (name, email, password) VALUES (%s, %s, %s)", (name, email, password))
                conn.commit()
                message = "Registration successful! Please login."
                return redirect('/login')
        except Exception as e:
            error = f"Database Error: {e}"
        finally:
            if conn:
                conn.close()

    return render_template('register.html', message=message, error=error, logged_in='user_id' in session)

@app.route('/login', methods=['GET', 'POST'])
def login():
    conn = None
    message = None
    error = None

    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        try:
            conn = get_connection()
            cur = conn.cursor()  # NO dictionary=True here
            cur.execute("SELECT * FROM users WHERE email=%s", (email,))
            user = cur.fetchone()

            if user and check_password_hash(user['password'], password):
                session['user_id'] = user['id']
                session['name'] = user['name']
                return redirect('/dashboard')
            else:
                error = "Invalid email or password"
        except Exception as e:
            error = f"Login Error: {e}"
        finally:
            if conn:
                conn.close()

    return render_template('login.html', message=message, error=error, logged_in='user_id' in session)

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect('/login')
    return render_template('dashboard.html', name=session['name'], logged_in=True)

@app.route('/cropinfo')
def cropinfo():
    conn = None
    crops = []
    error = None
    try:
        conn = get_connection()
        cur = conn.cursor()  # NO dictionary=True here
        cur.execute("""
            SELECT id, name, season, soil_type, care, image, description, care_tips, weather_preferred, tips, cures, fertilizers
            FROM crops
        """)
        crops = cur.fetchall()  # returns dicts because of DictCursor set in db_config.py
    except Exception as e:
        error = f"Error loading crop info: {e}"
    finally:
        if conn:
            conn.close()

    return render_template('cropinfo.html', crops=crops, error=error, logged_in='user_id' in session)

@app.route('/upload', methods=['GET', 'POST'])
def upload():
    message = None
    error = None
    uploaded_filename = None

    if request.method == 'POST':
        if 'image' not in request.files:
            error = 'No file part in the request.'
        else:
            file = request.files['image']
            if file.filename == '':
                error = 'No file selected.'
            elif file and allowed_file(file.filename):
                filename = secure_filename(file.filename)

                # Make sure the folder exists
                os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

                filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)

                # Avoid overwriting files
                counter = 1
                while os.path.exists(filepath):
                    name, ext = os.path.splitext(filename)
                    filename = f"{name}_{counter}{ext}"
                    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                    counter += 1

                try:
                    file.save(filepath)
                    uploaded_filename = filename
                    message = '✅ File uploaded successfully!'
                except Exception as e:
                    error = f"Upload failed: {e}"
            else:
                error = 'Invalid file type. Allowed: png, jpg, jpeg, gif'

    return render_template(
        'upload.html',
        message=message,
        error=error,
        filename=uploaded_filename,
        logged_in='user_id' in session
    )

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')

# Optional API login route (for mobile)
@app.route('/api/login', methods=['POST'])
def api_login():
    data = request.get_json()
    email = data.get('email')
    password = data.get('password')

    conn = get_connection()
    cursor = conn.cursor()  # NO dictionary=True here
    cursor.execute("SELECT * FROM users WHERE email=%s", (email,))
    user = cursor.fetchone()
    conn.close()

    if user and check_password_hash(user['password'], password):
        return jsonify({'status': 'success', 'user': user})
    else:
        return jsonify({'status': 'fail', 'message': 'Invalid credentials'})

if __name__ == '__main__':
    app.run()
