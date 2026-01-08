from flask import Blueprint, render_template
import json

news_blueprint = Blueprint('news', __name__)

@news_blueprint.route('/news')
def news_page():
    try:
        with open('news_data.json', 'r') as f:
            news_articles = json.load(f)
    except FileNotFoundError:
        news_articles = []
    
    return render_template('news.html', articles=news_articles)
