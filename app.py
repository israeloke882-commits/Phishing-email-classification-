from flask import Flask
import os
import logging
from flask_login import LoginManager
from database import db
import models

logging.basicConfig(level=logging.DEBUG)

os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'

app = Flask(__name__)

app.secret_key = "dev"
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///db.sqlite"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["GOOGLE_CLIENT_ID"] = "1018542354231-5vgfpu6u9gm9ccv94t5chd68q2faeh3s.apps.googleusercontent.com"
app.config["GOOGLE_CLIENT_SECRET"] = "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"

db.init_app(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'main.login'

from routes import main
from gmail_routes import gmail_blueprint
# The news blueprint is now removed
app.register_blueprint(main)
app.register_blueprint(gmail_blueprint, url_prefix="/google")

@login_manager.user_loader
def load_user(user_id):
    return models.User.query.get(int(user_id))

with app.app_context():
    db.create_all()
    logging.info("Database tables created")

if __name__ == "__main__":
    app.run(debug=True, use_reloader=False)
