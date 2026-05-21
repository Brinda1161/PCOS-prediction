from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import joblib
import numpy as np
import pandas as pd
import os

from config import Config

app = Flask(__name__)
app.config.from_object(Config)
app.secret_key = app.config['SECRET_KEY']
app.config['SESSION_TYPE'] = 'filesystem'

# Database initialization
def init_db():
    db_path = app.config['DATABASE_URL']
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Create users table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        email TEXT UNIQUE,
        age INTEGER,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    
    # Create predictions table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS predictions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        prediction_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        risk_level TEXT NOT NULL,
        risk_percentage REAL NOT NULL,
        age INTEGER,
        bmi TEXT,
        hirsutism TEXT,
        acne TEXT,
        menstrual TEXT,
        family_history TEXT,
        waist_hip_ratio REAL,
        amh REAL,
        fasting_glucose INTEGER,
        fasting_insulin INTEGER,
        FOREIGN KEY (user_id) REFERENCES users (id)
    )
    ''')
    
    # Create symptoms tracking table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS symptoms (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        cycle_length INTEGER,
        flow_days INTEGER,
        pain_level INTEGER,
        acne_severity INTEGER,
        hair_growth INTEGER,
        mood_score INTEGER,
        energy_level INTEGER,
        notes TEXT,
        FOREIGN KEY (user_id) REFERENCES users (id)
    )
    ''')
    
    # Create login history table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS login_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        username TEXT NOT NULL,
        login_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        ip_address TEXT,
        user_agent TEXT,
        FOREIGN KEY (user_id) REFERENCES users (id)
    )
    ''')
    
    conn.commit()
    conn.close()

def get_db_connection():
    db_path = app.config['DATABASE_URL']
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn

# Load ML models (with error handling)
try:
    model = joblib.load('pcos_model.pkl')
    scaler = joblib.load('scaler.pkl')
    label_encoders = joblib.load('label_encoders.pkl')
    print("ML models loaded successfully!")
except Exception as e:
    print(f"Warning: Could not load ML models: {e}")
    print("Using fallback risk calculation method")
    model = None
    scaler = None
    label_encoders = None

# Routes
@app.route('/')
def home():
    if 'username' in session:
        return redirect(url_for('dashboard'))
    return render_template('landing.html')

@app.route('/index')
@app.route('/index.html')
def index():
    # Check if user is logged in
    if 'username' not in session:
        flash('Please login to access the assessment', 'info')
        # Store the page they were trying to access
        return redirect(url_for('login', next='index'))
    
    # Verify user exists in database
    conn = get_db_connection()
    user = conn.execute(
        'SELECT * FROM users WHERE username = ?', 
        (session['username'],)
    ).fetchone()
    conn.close()
    
    if not user:
        # User in session but not in database - clear session
        session.clear()
        flash('Session expired. Please login again.', 'warning')
        return redirect(url_for('login'))
    
    return render_template('index.html', username=session['username'])
@app.route('/check-session')
def check_session():
    if 'username' in session:
        return jsonify({
            'logged_in': True,
            'username': session['username'],
            'user_id': session['user_id']
        })
    return jsonify({'logged_in': False})

@app.route('/landing')
def landing():
    return render_template('landing.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        print(f"Login attempt for username: {username}")  # Debug print
        
        conn = get_db_connection()
        user = conn.execute(
            'SELECT * FROM users WHERE username = ?', 
            (username,)
        ).fetchone()
        conn.close()
        
        if user and check_password_hash(user['password'], password):
            # Clear any existing session first
            session.clear()
            
            # Set session variables
            session['username'] = username
            session['user_id'] = user['id']
            session.permanent = True
            session['logged_in'] = True
            
            print(f"User logged in successfully: {username}")
            print(f"Session data: {dict(session)}")
            
            flash('Login successful!', 'success')
            
            # Check if it's an AJAX request
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({
                    'success': True,
                    'redirect': url_for('dashboard'),
                    'message': 'Login successful'
                })
            
            # Regular form submission
            next_page = request.args.get('next')
            if next_page:
                return redirect(next_page)
            return redirect(url_for('dashboard'))
        else:
            print(f"Login failed for username: {username}")
            
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({
                    'success': False,
                    'message': 'Invalid username or password'
                }), 401
            
            flash('Invalid username or password', 'danger')
            return redirect(url_for('login'))
    
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if 'username' in session:
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        username = request.form['username']
        email = request.form.get('email', '')
        password = request.form['password']
        confirm_password = request.form['confirm_password']
        
        if password != confirm_password:
            flash('Passwords do not match', 'danger')
            return redirect(url_for('register'))
        
        conn = get_db_connection()
        try:
            conn.execute(
                'INSERT INTO users (username, email, password) VALUES (?, ?, ?)',
                (username, email, generate_password_hash(password))
            )
            conn.commit()
            flash('Registration successful! Please login.', 'success')
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            flash('Username or email already exists', 'danger')
            return redirect(url_for('register'))
        finally:
            conn.close()
    
    return render_template('register.html')

@app.route('/assessment')
def assessment():
    if 'username' not in session:
        flash('Please login to access this page', 'danger')
        return redirect(url_for('login'))
    return render_template('index.html', username=session['username'])

@app.route('/debug-session')
def debug_session():
    """Debug endpoint to check session state"""
    session_data = {
        'session_keys': list(session.keys()),
        'username': session.get('username'),
        'user_id': session.get('user_id'),
        'logged_in': 'username' in session,
        'session_permanent': session.permanent if hasattr(session, 'permanent') else None
    }
    
    # Check if user exists in database
    if 'username' in session:
        try:
            conn = get_db_connection()
            user = conn.execute(
                'SELECT id, username, email FROM users WHERE username = ?',
                (session['username'],)
            ).fetchone()
            conn.close()
            
            if user:
                session_data['db_user'] = dict(user)
                session_data['db_match'] = (user['id'] == session.get('user_id'))
            else:
                session_data['db_user'] = None
                session_data['db_match'] = False
        except Exception as e:
            session_data['db_error'] = str(e)
    
    return jsonify(session_data)

@app.route('/predict', methods=['GET', 'POST'])
def predict():
    if 'username' not in session:
        flash('Please login to access this page', 'danger')
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        print("="*50)
        print("PREDICTION FORM SUBMITTED")
        print(f"User: {session['username']}")
        print(f"Form data: {dict(request.form)}")
        
        form_data = request.form
        
        # Validate required fields
        required_fields = ['age', 'bmi', 'menstrual']
        missing_fields = [field for field in required_fields if not form_data.get(field)]
        
        if missing_fields:
            print(f"Missing required fields: {missing_fields}")
            flash(f'Please fill in all required fields: {", ".join(missing_fields)}', 'danger')
            return redirect(url_for('index'))
        
        # Calculate risk using ML model or fallback
        try:
            if model is not None and scaler is not None:
                risk_percentage = calculate_risk_ml(form_data)
                print(f"ML risk calculation: {risk_percentage}%")
            else:
                risk_percentage = calculate_risk_fallback(form_data)
                print(f"Fallback risk calculation: {risk_percentage}%")
        except Exception as e:
            print(f"Risk calculation error: {e}")
            risk_percentage = calculate_risk_fallback(form_data)
            print(f"Using fallback after error: {risk_percentage}%")
        
        # Determine risk level
        if risk_percentage < 30:
            risk_level = 'Low'
        elif risk_percentage < 60:
            risk_level = 'Moderate'
        else:
            risk_level = 'High'
        
        print(f"Risk Level: {risk_level}")
        
        # Store in database
        try:
            conn = get_db_connection()
            
            # Insert prediction
            cursor = conn.execute(
                '''INSERT INTO predictions 
                (user_id, risk_level, risk_percentage, age, bmi, hirsutism, acne, menstrual, 
                 family_history, waist_hip_ratio, amh, fasting_glucose, fasting_insulin)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                (
                    session['user_id'], 
                    risk_level, 
                    risk_percentage, 
                    form_data.get('age'),
                    form_data.get('bmi'), 
                    form_data.get('hirsutism', 'No'), 
                    form_data.get('acne', 'No'), 
                    form_data.get('menstrual'),
                    form_data.get('family_history', 'No'),
                    form_data.get('waist_hip_ratio'),
                    form_data.get('amh'), 
                    form_data.get('fasting_glucose'),
                    form_data.get('fasting_insulin')
                )
            )
            conn.commit()
            
            # Get the ID of the inserted record
            prediction_id = cursor.lastrowid
            print(f"✅ Prediction saved to database with ID: {prediction_id}")
            
            # Verify it was saved
            saved = conn.execute(
                'SELECT * FROM predictions WHERE id = ?',
                (prediction_id,)
            ).fetchone()
            
            if saved:
                print(f"✅ Verification: Prediction found in DB: {dict(saved)}")
            else:
                print("❌ Verification failed: Prediction not found after insert")
            
            conn.close()
            
            flash('Assessment completed successfully!', 'success')
            
        except Exception as e:
            print(f"❌ Database error: {e}")
            flash('Error saving assessment. Please try again.', 'danger')
            return redirect(url_for('index'))
        
        return redirect(url_for('dashboard'))
    
    # GET request - show the form
    return render_template('index.html', username=session['username'])


@app.route('/debug/predictions')
def debug_predictions():
    if 'username' not in session:
        return jsonify({'error': 'Not logged in'}), 401
    
    conn = get_db_connection()
    
    # Check if predictions table exists
    tables = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table';"
    ).fetchall()
    
    # Get all predictions for this user
    predictions = conn.execute(
        'SELECT * FROM predictions WHERE user_id = ? ORDER BY prediction_date DESC',
        (session['user_id'],)
    ).fetchall()
    
    # Convert to list of dicts
    predictions_list = []
    for pred in predictions:
        pred_dict = dict(pred)
        # Convert date to string for JSON
        pred_dict['prediction_date'] = str(pred_dict['prediction_date'])
        predictions_list.append(pred_dict)
    
    conn.close()
    
    return jsonify({
        'tables': [table['name'] for table in tables],
        'user_id': session['user_id'],
        'username': session['username'],
        'predictions_count': len(predictions_list),
        'predictions': predictions_list
    })
    
    
@app.route('/test-session')
def test_session():
    return jsonify({
        'session': dict(session),
        'is_authenticated': 'username' in session
    })
    
@app.route('/dashboard')
def dashboard():
    if 'username' not in session:
        flash('Please login to access this page', 'danger')
        return redirect(url_for('login'))
    
    conn = get_db_connection()
    
    # Get user's predictions
    predictions = conn.execute(
        'SELECT * FROM predictions WHERE user_id = ? ORDER BY prediction_date DESC LIMIT 10',
        (session['user_id'],)
    ).fetchall()
    
    # Get user's symptoms
    symptoms = conn.execute(
        'SELECT * FROM symptoms WHERE user_id = ? ORDER BY date DESC LIMIT 7',
        (session['user_id'],)
    ).fetchall()
    
    # Calculate statistics
    total_assessments = conn.execute(
        'SELECT COUNT(*) as count FROM predictions WHERE user_id = ?',
        (session['user_id'],)
    ).fetchone()['count']
    
    if total_assessments > 0:
        latest_prediction = conn.execute(
            'SELECT * FROM predictions WHERE user_id = ? ORDER BY prediction_date DESC LIMIT 1',
            (session['user_id'],)
        ).fetchone()
        latest_risk = latest_prediction['risk_level'] if latest_prediction else 'No data'
        latest_risk_percentage = latest_prediction['risk_percentage'] if latest_prediction else 0
        
        # Risk distribution
        high_risk = conn.execute(
            'SELECT COUNT(*) as count FROM predictions WHERE user_id = ? AND risk_level = "High"',
            (session['user_id'],)
        ).fetchone()['count']
        
        moderate_risk = conn.execute(
            'SELECT COUNT(*) as count FROM predictions WHERE user_id = ? AND risk_level = "Moderate"',
            (session['user_id'],)
        ).fetchone()['count']
        
        low_risk = conn.execute(
            'SELECT COUNT(*) as count FROM predictions WHERE user_id = ? AND risk_level = "Low"',
            (session['user_id'],)
        ).fetchone()['count']
    else:
        latest_risk = 'No data'
        latest_risk_percentage = 0
        high_risk = moderate_risk = low_risk = 0
    
    conn.close()
    
    return render_template('dashboard.html', 
                         username=session['username'],
                         predictions=predictions,
                         symptoms=symptoms,
                         total_assessments=total_assessments,
                         latest_risk=latest_risk,
                         latest_risk_percentage=latest_risk_percentage,
                         high_risk=high_risk,
                         moderate_risk=moderate_risk,
                         low_risk=low_risk)

@app.route('/symptoms', methods=['GET', 'POST'])
def symptoms():
    if 'username' not in session:
        flash('Please login to access this page', 'danger')
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        form_data = request.form
        
        conn = get_db_connection()
        conn.execute(
            '''INSERT INTO symptoms 
            (user_id, cycle_length, flow_days, pain_level, acne_severity, 
             hair_growth, mood_score, energy_level, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)''',
            (session['user_id'], 
             form_data.get('cycle_length'), form_data.get('flow_days'),
             form_data.get('pain_level'), form_data.get('acne_severity'),
             form_data.get('hair_growth'), form_data.get('mood_score'),
             form_data.get('energy_level'), form_data.get('notes'))
        )
        conn.commit()
        conn.close()
        
        flash('Symptoms tracked successfully!', 'success')
        return redirect(url_for('dashboard'))
    
    return render_template('symptoms.html', username=session['username'], today=datetime.today().strftime('%Y-%m-%d'))

@app.route('/symptom-results')
def symptom_results():
    if 'username' not in session:
        flash('Please login to access this page', 'danger')
        return redirect(url_for('login'))
    
    conn = get_db_connection()
    symptoms = conn.execute(
        'SELECT * FROM symptoms WHERE user_id = ? ORDER BY date DESC',
        (session['user_id'],)
    ).fetchall()
    conn.close()
    
    return render_template('symptom_results.html', 
                         username=session['username'],
                         symptom_data=symptoms)
    
        
@app.route('/period-tracker', methods=['GET'])
def period_tracker():
    if 'username' not in session:
        flash('Please login to access this page', 'danger')
        return redirect(url_for('login'))
    
    from datetime import date
    today = date.today().isoformat()
    
    return render_template('period_tracker.html', 
                         username=session['username'],
                         today=today)

@app.route('/save-period-tracker', methods=['POST'])
def save_period_tracker():
    if 'username' not in session:
        flash('Please login to access this page', 'danger')
        return redirect(url_for('login'))
    
    form_data = request.form
    
    # Get symptoms as comma-separated string
    symptoms_list = form_data.getlist('symptoms')
    symptoms_str = ', '.join(symptoms_list) if symptoms_list else None
    
    conn = get_db_connection()
    
    # Insert into symptoms table
    conn.execute(
        '''INSERT INTO symptoms 
        (user_id, date, cycle_length, flow_days, pain_level, acne_severity, 
         mood_score, energy_level, notes)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)''',
        (session['user_id'],
         form_data.get('tracking_date'),
         form_data.get('cycle_length'),
         None,  # flow_days - can be calculated from cycle
         form_data.get('pain_level'),
         3 if 'Acne' in symptoms_list else 2,  # acne severity based on symptom
         {'Very Happy': 10, 'Happy': 8, 'Neutral': 6, 'Sad': 4, 'Anxious': 3, 'Irritable': 2}.get(form_data.get('mood'), 5),
         7,  # energy level default
         f"Mood: {form_data.get('mood')}, Flow: {form_data.get('flow')}, Symptoms: {symptoms_str}\n{form_data.get('notes')}")
    )
    conn.commit()
    conn.close()
    
    flash('Period tracker entry saved successfully!', 'success')
    return redirect(url_for('symptom_results'))
@app.route('/history')
def history():
    if 'username' not in session:
        flash('Please login to access this page', 'danger')
        return redirect(url_for('login'))
    return render_template('user-history.html', username=session['username'])

@app.route('/blog')
def blog():
    return render_template('blog.html')

@app.route('/recommend')
def recommend():
    if 'username' not in session:
        flash('Please login to access this page', 'danger')
        return redirect(url_for('login'))
    
    # Get user's latest prediction for personalized recommendations
    conn = get_db_connection()
    latest = conn.execute(
        'SELECT * FROM predictions WHERE user_id = ? ORDER BY prediction_date DESC LIMIT 1',
        (session['user_id'],)
    ).fetchone()
    conn.close()
    recommendations = get_personalized_recommendations(latest)
    return render_template('recommend.html', 
                         username=session['username'],
                         recommendations=recommendations,
                         risk_level=latest['risk_level'] if latest else 'Unknown')
@app.route('/learn_more')
def learn_more():
    return render_template('learn_more.html')

@app.route('/logout')
def logout():
    session.pop('username', None)
    session.pop('user_id', None)
    flash('You have been logged out', 'info')
    return redirect(url_for('landing'))

@app.route('/profile', methods=['GET', 'POST'])
def profile():
    if 'username' not in session:
        flash('Please login to access this page', 'danger')
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        conn = get_db_connection()
        try:
            conn.execute(
                '''UPDATE users SET 
                   email = ?, 
                   age = ? 
                   WHERE id = ?''',
                (request.form.get('email'), request.form.get('age'), session['user_id'])
            )
            conn.commit()
            flash('Profile updated successfully!', 'success')
        except Exception as e:
            print(f"Error updating profile: {e}")
            flash('Error updating profile.', 'danger')
        finally:
            conn.close()
        return redirect(url_for('profile'))
    
    conn = get_db_connection()
    try:
        user = conn.execute('SELECT * FROM users WHERE id = ?', (session['user_id'],)).fetchone()
    finally:
        conn.close()
    
    return render_template('profile.html', username=session['username'], user=user)

@app.route('/api/login-history')
def get_login_history():
    if 'user_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    conn = get_db_connection()
    history = conn.execute(
        'SELECT * FROM login_history WHERE user_id = ? ORDER BY login_time DESC LIMIT 50',
        (session['user_id'],)
    ).fetchall()
    conn.close()
    
    # Convert to list of dictionaries
    history_list = []
    for entry in history:
        history_list.append({
            'id': entry['id'],
            'username': entry['username'],
            'login_time': entry['login_time'],
            'ip_address': entry['ip_address']
        })
    
    return jsonify(history_list)

@app.route('/api/predictions')
def api_predictions():
    if 'username' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    conn = get_db_connection()
    predictions = conn.execute(
        'SELECT * FROM predictions WHERE user_id = ? ORDER BY prediction_date DESC',
        (session['user_id'],)
    ).fetchall()
    conn.close()
    
    return jsonify([dict(pred) for pred in predictions])

# Helper functions
def calculate_risk_ml(form_data):
    """Calculate risk using ML model"""
    try:
        # This needs to be adapted based on your model's features
        features = []
        
        # Example feature extraction (adjust based on your model)
        age = float(form_data.get('age', 30))
        bmi_map = {'Underweight': 0, 'Normal': 1, 'Overweight': 2, 'Obese': 3}
        bmi = bmi_map.get(form_data.get('bmi', 'Normal'), 1)
        hirsutism = 1 if form_data.get('hirsutism') == 'Yes' else 0
        acne = 1 if form_data.get('acne') == 'Yes' else 0
        menstrual = 0 if form_data.get('menstrual') == 'Regular' else 1
        family_history = 1 if form_data.get('family_history') == 'Yes' else 0
        waist_hip = float(form_data.get('waist_hip_ratio', 0.8))
        amh = float(form_data.get('amh', 2.5))
        glucose = float(form_data.get('fasting_glucose', 90))
        insulin = float(form_data.get('fasting_insulin', 10))
        
        features = [age, bmi, hirsutism, acne, menstrual, family_history, 
                   waist_hip, amh, glucose, insulin]
        
        # Scale features
        features_scaled = scaler.transform([features])
        
        # Get prediction probability
        probability = model.predict_proba(features_scaled)[0]
        
        # Return risk percentage (assuming binary classification)
        return round(probability[1] * 100, 2)
        
    except Exception as e:
        print(f"ML prediction error: {e}")
        return calculate_risk_fallback(form_data)

def calculate_risk_fallback(form_data):
    """Fallback risk calculation"""
    risk = 20  # Base risk
    
    # BMI impact
    bmi = form_data.get('bmi')
    if bmi == 'Overweight':
        risk += 10
    elif bmi == 'Obese':
        risk += 20
    
    # Menstrual irregularity
    if form_data.get('menstrual') == 'Irregular':
        risk += 25
    elif form_data.get('menstrual') == 'Absent':
        risk += 35
    
    # Family history
    if form_data.get('family_history') == 'Yes':
        risk += 15
    
    # Hirsutism
    if form_data.get('hirsutism') == 'Yes':
        risk += 10
    
    # Acne
    if form_data.get('acne') == 'Yes':
        risk += 5
    
    # Age factor
    try:
        age = int(form_data.get('age', 30))
        if age < 20:
            risk += 5
        elif age > 35:
            risk += 10
    except (ValueError, TypeError):
        pass  # If age is invalid, skip this factor
    
    # Ensure risk is between 0 and 100
    risk = max(0, min(100, risk))
    return round(risk, 2)

def get_personalized_recommendations(prediction):
    """Generate personalized recommendations based on prediction"""
    if not prediction:
        return {
            'diet': ['Maintain a balanced diet', 'Stay hydrated', 'Limit processed foods'],
            'exercise': ['Regular moderate exercise (30 min/day)', 'Mix cardio and strength training'],
            'lifestyle': ['Manage stress', 'Get adequate sleep', 'Regular health check-ups'],
            'medical': ['Consult healthcare provider for baseline assessment']
        }
    
    risk_level = prediction['risk_level']
    
    if risk_level == 'Low':
        return {
            'diet': [
                'Continue balanced nutrition',
                'Include anti-inflammatory foods',
                'Maintain healthy weight through diet'
            ],
            'exercise': [
                '30 minutes of moderate exercise daily',
                'Mix of cardio and strength training',
                'Stay active throughout the day'
            ],
            'lifestyle': [
                'Monitor menstrual cycle regularly',
                'Practice stress management techniques',
                'Annual wellness check-ups'
            ],
            'medical': [
                'Regular gynecological check-ups',
                'Monitor any symptom changes',
                'Consider fertility planning if desired'
            ]
        }
    elif risk_level == 'Moderate':
        return {
            'diet': [
                'Low glycemic index foods',
                'Increase fiber intake',
                'Limit sugar and refined carbs',
                'Consider anti-inflammatory diet'
            ],
            'exercise': [
                '45 minutes of exercise 5 days/week',
                'Focus on insulin-sensitizing activities',
                'Include HIIT workouts',
                'Strength training 2-3 times/week'
            ],
            'lifestyle': [
                'Track all symptoms systematically',
                'Stress reduction techniques (yoga, meditation)',
                'Optimize sleep (7-8 hours)',
                'Consider supplements (consult doctor)'
            ],
            'medical': [
                'Schedule consultation with endocrinologist',
                'Consider hormonal panel testing',
                'Monitor insulin and glucose levels',
                'Discuss metformin or other medications'
            ]
        }
    else:  # High risk
        return {
            'diet': [
                'Strict low glycemic diet',
                'Eliminate processed foods and sugars',
                'Consult with nutritionist specialized in PCOS',
                'Consider meal planning services'
            ],
            'exercise': [
                'Daily exercise regimen',
                'Mix of cardio and resistance training',
                'Focus on insulin sensitivity workouts',
                'Consider working with a personal trainer'
            ],
            'lifestyle': [
                'Comprehensive symptom diary',
                'Intensive stress management program',
                'Sleep hygiene optimization',
                'Support group participation'
            ],
            'medical': [
                'Immediate consultation with endocrinologist',
                'Complete metabolic and hormonal testing',
                'Pelvic ultrasound if not done recently',
                'Discuss treatment options including medications',
                'Regular monitoring of progress'
            ]
        }

@app.context_processor
def utility_processor():
    return dict(
        now=datetime.now(),
        enumerate=enumerate,
        zip=zip
    )

if __name__ == '__main__':
    init_db()
    app.run(debug=True, host='0.0.0.0', port=5000)