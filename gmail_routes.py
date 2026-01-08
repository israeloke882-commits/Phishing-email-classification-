from flask import Blueprint, current_app, redirect, request, url_for, session, render_template, jsonify
from flask_login import login_user, login_required, current_user
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import google.auth.transport.requests
import google.auth.exceptions
import json
import traceback
import base64
import csv
import os

# Import the database object, User model, and the prediction function
from database import db
from models import User
from prediction_pipeline import get_detector

gmail_blueprint = Blueprint('gmail', __name__)

# Add openid, email, and profile scopes to get user info
SCOPES = [
    'https://www.googleapis.com/auth/gmail.readonly',
    'openid',
    'https://www.googleapis.com/auth/userinfo.email',
    'https://www.googleapis.com/auth/userinfo.profile'
]

def get_google_flow():
    client_config = {
        "web": {
            "client_id": current_app.config['GOOGLE_CLIENT_ID'],
            "client_secret": current_app.config['GOOGLE_CLIENT_SECRET'],
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": [url_for('gmail.authorized', _external=True)],
        }
    }
    return Flow.from_client_config(
        client_config=client_config,
        scopes=SCOPES,
        redirect_uri=url_for('gmail.authorized', _external=True)
    )

@gmail_blueprint.route('/login') # No login_required here
def login():
    if not current_app.config.get('GOOGLE_CLIENT_ID') or not current_app.config.get('GOOGLE_CLIENT_SECRET'):
        return "Google Client ID or Secret is not configured.", 500
    flow = get_google_flow()
    authorization_url, state = flow.authorization_url(
        access_type='offline', prompt='consent', include_granted_scopes='true'
    )
    session['state'] = state
    return redirect(authorization_url)

@gmail_blueprint.route('/authorized') # No login_required here
def authorized():
    state = session.pop('state', None)
    flow = get_google_flow()
    flow.fetch_token(authorization_response=request.url)
    credentials = flow.credentials

    # Get user info from Google
    user_info_service = build('oauth2', 'v2', credentials=credentials)
    user_info = user_info_service.userinfo().get().execute()

    # Find or create the user
    user = User.query.filter_by(email=user_info['email']).first()
    if not user:
        user = User(
            email=user_info['email'],
            first_name=user_info.get('given_name')
        )
        db.session.add(user)
    
    # Save credentials and log in the user
    user.google_credentials_json = credentials.to_json()
    db.session.commit()
    login_user(user)
    
    return redirect(url_for('gmail.list_emails'))

@gmail_blueprint.route('/emails')
@login_required
def list_emails():
    if not current_user.google_credentials_json:
        return redirect(url_for('gmail.login'))
    try:
        creds = Credentials.from_authorized_user_info(json.loads(current_user.google_credentials_json), SCOPES)
        if not creds.valid:
            if creds.expired and creds.refresh_token:
                creds.refresh(google.auth.transport.requests.Request())
                current_user.google_credentials_json = creds.to_json()
                db.session.commit()
            else:
                return redirect(url_for('gmail.login'))
        service = build('gmail', 'v1', credentials=creds)
        results = service.users().messages().list(userId='me', maxResults=20, q="is:inbox").execute()
        messages = results.get('messages', [])
        emails = []
        for message in messages:
            msg = service.users().messages().get(userId='me', id=message['id'], format='full').execute()
            headers = msg['payload']['headers']
            subject = next((h['value'] for h in headers if h['name'] == 'Subject'), '')
            sender = next((h['value'] for h in headers if h['name'] == 'From'), '')
            snippet = msg['snippet']
            emails.append({'id': message['id'], 'subject': subject, 'sender': sender, 'snippet': snippet})
        return render_template("gmail.html", emails=emails, user=current_user)
    except HttpError as e:
        error_details = json.loads(e.content.decode('utf-8'))
        error_reason = error_details.get('error', {}).get('message', 'No reason provided.')
        return f"<h1>Google API Error: {e.status_code}</h1><pre>{error_reason}</pre>"
    except Exception as e:
        return f"<h1>An Unknown Error Occurred</h1><pre>{str(e)}</pre><pre>{traceback.format_exc()}</pre>"

@gmail_blueprint.route('/analyze/<message_id>')
@login_required
def analyze_email(message_id):
    if not current_user.google_credentials_json:
        return jsonify({'error': 'Authentication required'}), 401
    try:
        creds = Credentials.from_authorized_user_info(json.loads(current_user.google_credentials_json), SCOPES)
        if not creds.valid:
            return jsonify({'error': 'Invalid credentials'}), 401
        service = build('gmail', 'v1', credentials=creds)
        msg = service.users().messages().get(userId='me', id=message_id, format='full').execute()
        headers = msg['payload']['headers']
        subject = next((h['value'] for h in headers if h['name'] == 'Subject'), '')
        body = ''
        if 'parts' in msg['payload']:
            for part in msg['payload']['parts']:
                if part['mimeType'] == 'text/plain':
                    encoded_body = part['body'].get('data', '')
                    body = base64.urlsafe_b64decode(encoded_body).decode('utf-8')
                    break
        elif 'data' in msg['payload']['body']:
            encoded_body = msg['payload']['body']['data']
            body = base64.urlsafe_b64decode(encoded_body).decode('utf-8')
        full_email_text = f"Subject: {subject}\n\n{body}"
        detector = get_detector()
        result = detector.predict(full_email_text)
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': f'An error occurred: {str(e)}'}), 500

@gmail_blueprint.route('/collect_emails')
@login_required
def collect_emails():
    if not current_user.google_credentials_json:
        return redirect(url_for('gmail.login'))
    try:
        creds = Credentials.from_authorized_user_info(json.loads(current_user.google_credentials_json), SCOPES)
        if not creds.valid:
            return redirect(url_for('gmail.login'))
        
        service = build('gmail', 'v1', credentials=creds)
        results = service.users().messages().list(userId='me', maxResults=100, q="is:inbox").execute()
        messages = results.get('messages', [])
        
        os.makedirs('dataset', exist_ok=True)
        
        with open('dataset/my_emails.csv', 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['text', 'label'])
            
            for message in messages:
                msg = service.users().messages().get(userId='me', id=message['id'], format='full').execute()
                headers = msg['payload']['headers']
                subject = next((h['value'] for h in headers if h['name'] == 'Subject'), '')
                body = ''
                if 'parts' in msg['payload']:
                    for part in msg['payload']['parts']:
                        if part['mimeType'] == 'text/plain':
                            encoded_body = part['body'].get('data', '')
                            body = base64.urlsafe_b64decode(encoded_body).decode('utf-8')
                            break
                elif 'data' in msg['payload']['body']:
                    encoded_body = msg['payload']['body']['data']
                    body = base64.urlsafe_b64decode(encoded_body).decode('utf-8')
                
                full_email_text = f"Subject: {subject}\n\n{body}"
                writer.writerow([full_email_text, 0]) # 0 for legitimate
                
        return "Successfully collected 100 emails and saved to dataset/my_emails.csv"

    except Exception as e:
        return f"An error occurred: {str(e)}", 500
