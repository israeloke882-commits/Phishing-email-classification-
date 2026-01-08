from flask import session, render_template, request, jsonify, redirect, url_for, Blueprint
from database import db
from flask_login import current_user, login_required, login_user, logout_user
from models import PredictionLog, User
from prediction_pipeline import get_detector
import traceback

main = Blueprint('main', __name__)

@main.before_request
def make_session_permanent():
    session.permanent = True

@main.route('/')
def index():
    if current_user.is_authenticated:
        return render_template('dashboard.html', user=current_user)
    else:
        return render_template('landing.html')

@main.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    if request.method == 'POST':
        user = User.query.filter_by(email=request.form['email']).first()
        if user is None or not user.check_password(request.form['password']):
            return redirect(url_for('main.login'))
        login_user(user)
        return redirect(url_for('main.index'))
    return render_template('login.html')

@main.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    if request.method == 'POST':
        user = User(email=request.form['email'], first_name=request.form.get('first_name'))
        user.set_password(request.form['password'])
        db.session.add(user)
        db.session.commit()
        return redirect(url_for('main.login'))
    return render_template('register.html')

@main.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('main.index'))

@main.route('/detect', methods=['GET', 'POST'])
@login_required
def detect():
    if request.method == 'GET':
        return render_template('detect.html', user=current_user)
    
    # POST request logic
    try:
        data = request.get_json()
        email_text = data.get('text', '').strip()
        
        if not email_text:
            return jsonify({'error': 'Email text is required'}), 400
        
        detector = get_detector()
        result = detector.predict(email_text)
        
        log = PredictionLog(
            user_id=current_user.id,
            email_text=email_text[:500],
            prediction=result['prediction'],
            confidence=result['confidence'],
            model_stage=result['model_stage']
        )
        db.session.add(log)
        db.session.commit()
        
        return jsonify(result)
    
    except Exception as e:
        print(f"Error in prediction: {str(e)}")
        traceback.print_exc()
        return jsonify({'error': 'Prediction failed'}), 500

@main.route('/detect_url', methods=['POST'])
@login_required
def detect_url():
    try:
        data = request.get_json()
        url_text = data.get('text', '').strip()
        
        if not url_text:
            return jsonify({'error': 'URL is required'}), 400

        # Pre-process the URL to look like email content
        processed_text = f"Subject: URL Link Body: {url_text}"
        
        detector = get_detector()
        result = detector.predict(processed_text)
        
        log = PredictionLog(
            user_id=current_user.id,
            email_text=f"URL: {url_text}",
            prediction=result['prediction'],
            confidence=result['confidence'],
            model_stage=result['model_stage']
        )
        db.session.add(log)
        db.session.commit()
        
        return jsonify(result)
    
    except Exception as e:
        print(f"Error in URL prediction: {str(e)}")
        traceback.print_exc()
        return jsonify({'error': 'URL analysis failed'}), 500

@main.route('/history')
@login_required
def history():
    logs = PredictionLog.query.filter_by(user_id=current_user.id).order_by(PredictionLog.created_at.desc()).limit(20).all()
    return render_template('history.html', user=current_user, logs=logs)

@main.route('/about')
def about():
    return render_template('about.html', user=current_user if current_user.is_authenticated else None)

@main.app_errorhandler(404)
def not_found(e):
    return render_template('404.html'), 404
