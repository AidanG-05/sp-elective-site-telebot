from flask import Flask, request, jsonify
import requests
import os
from dotenv import load_dotenv

app = Flask(__name__)


load_dotenv()

TOKEN = os.getenv("TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

print("Loaded TOKEN:", TOKEN)
print("Loaded CHAT_ID:", CHAT_ID)

@app.route('/')
def index():
    return "Telegram notifier Flask app is running."

@app.route('/notify', methods=['POST'])
def notify():
    data = request.json
    module = data.get('Elective_Module')
    code = data.get('Elective_Code')
    rating = data.get('Ratings')

    if not all([module, code, rating]):
        return jsonify({"error": "Missing required fields"}), 400

    link = f"https://sp-elective-site-frontend.vercel.app//modules/{code}"
    message = (
        f"🆕 <b>New review</b> \n"
        f"<b>{module}</b>\n"
        f"<b>MC: {code} </b>\n"
        f"⭐ Rating: {rating}/5\n"
        f'🔗 Read the full review: <a href="{link}">Here</a>'
    )
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"

    try:
        res = requests.post(url, json={
        'chat_id': CHAT_ID,
        'text': message,
        'parse_mode': 'HTML'
    })
        res.raise_for_status()
        return jsonify({"status": "Message sent"}), 200
    except requests.exceptions.RequestException as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5002)
