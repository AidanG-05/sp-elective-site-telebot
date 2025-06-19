import os
import mysql.connector
import requests
from flask import Flask, request, jsonify
from dotenv import load_dotenv

app = Flask(__name__)
load_dotenv()

# bot config
NOTIFIER_TOKEN = os.getenv("NOTIFIER_TOKEN")
NOTIFIER_CHAT_ID = os.getenv("NOTIFIER_CHAT_ID")
APPROVAL_TOKEN = os.getenv("APPROVAL_TOKEN")
APPROVER_CHAT_ID = os.getenv("APPROVAL_CHAT_ID")

# Db config
DB_CONFIG = {
    'host': os.getenv("DB_HOST"),
    'user': os.getenv("DB_USER"),
    'password': os.getenv("DB_PASSWORD"),
    'database': os.getenv("DB_NAME")
}

def send_approval_message(review):
    message = (
        f"🆕 <b>New Review Submission for Approval</b>\n"
        f"<b>Module:</b> {review['Elective_Module']}\n"
        f"<b>Code:</b> {review['Elective_Code']}\n"
        f"<b>Year:</b> {review['Academic_Year']}\n"
        f"<b>Semester:</b> {review['Semester']}\n"
        f"<b>Rating:</b> {review['Ratings']}/5\n\n"
        f"<b>Reason:</b> {review['Rating_Reason']}\n\n"
        f"<b>TL;DR:</b> {review['TLDR_experiences']}\n\n"
        f"<b>Assignment Review:</b> {review['Assignment_Review']}\n"
        f"<b>Weightage:</b> {review['Assignment_Weightage']}\n\n"
        f"<b>Life Hacks:</b> {review['Life_Hacks']}\n\n"
        f"🛠️ <i>Approve or Reject below</i>"
    )
    keyboard = {
        "inline_keyboard": [[
            {"text": "✅ Approve", "callback_data": f"approve|{review['id']}"},
            {"text": "❌ Reject", "callback_data": f"reject|{review['id']}"}
        ]]
    }
    requests.post(f"https://api.telegram.org/bot{APPROVAL_TOKEN}/sendMessage", json={
        "chat_id": APPROVER_CHAT_ID,
        "text": message,
        "parse_mode": "HTML",
        "reply_markup": keyboard
    })

def send_notification_message(review):
    code = review['Elective_Code']
    link = f"https://sp-elective-site-frontend.vercel.app/modules/{code}"
    message = (
        f"🆕 <b>New review</b>\n"
        f"<b>{review['Elective_Module']}</b>\n"
        f"<b>MC: {code}</b>\n"
        f"⭐ Rating: {review['Ratings']}/5\n"
        f'<a href="{link}">🔗 Read full review</a>'
    )
    requests.post(f"https://api.telegram.org/bot{NOTIFIER_TOKEN}/sendMessage", json={
        'chat_id': NOTIFIER_CHAT_ID,
        'text': message,
        'parse_mode': 'HTML'
    })

@app.route('/')
def index():
    return "Combined Flask bot is running."

@app.route('/send-for-approval', methods=['POST'])
def handle_submission():
    data = request.json
    required = [
        'Elective_Module', 'Elective_Code', 'Academic_Year', 'Semester',
        'Ratings', 'Rating_Reason', 'TLDR_experiences', 'Assignment_Review',
        'Assignment_Weightage', 'Life_Hacks'
    ]
    if not all(k in data and data[k] is not None for k in required):
        return jsonify({"error": "Missing required fields"}), 400

    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM pending_reviews ORDER BY id DESC LIMIT 1")
        latest_review = cursor.fetchone()
        cursor.close()
        conn.close()
    except Exception as e:
        return jsonify({"error": str(e)}), 500

    if latest_review:
        send_approval_message(latest_review)
        return jsonify({"status": "Sent for approval"}), 200
    else:
        return jsonify({"error": "No review found"}), 404

@app.route('/webhook', methods=['POST'])
def telegram_webhook():
    update = request.json

    if 'callback_query' in update:
        callback = update['callback_query']
        action, review_id = callback['data'].split('|')
        chat_id = callback['message']['chat']['id']
        message_id = callback['message']['message_id']

        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor(dictionary=True)

        if action == "approve":
            cursor.execute("SELECT * FROM pending_reviews WHERE id = %s", (review_id,))
            row = cursor.fetchone()
            if row:
                insert_sql = """
                    INSERT INTO user_reviews (Elective_Module, Elective_Code, Academic_Year, Semester, Ratings, Rating_Reason, TLDR_experiences, Assignment_Review, Assignment_Weightage, Life_Hacks)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """
                cursor.execute(insert_sql, (
                    row['Elective_Module'], row['Elective_Code'], row['Academic_Year'],
                    row['Semester'], row['Ratings'], row['Rating_Reason'],
                    row['TLDR_experiences'], row['Assignment_Review'],
                    row['Assignment_Weightage'], row['Life_Hacks']
                ))
                cursor.execute("DELETE FROM pending_reviews WHERE id = %s", (review_id,))
                conn.commit()
                reply = f"✅ Approved review for: {row['Elective_Code']}"

                send_notification_message(row)
            else:
                reply = "⚠️ Review not found."

        elif action == "reject":
            cursor.execute("DELETE FROM pending_reviews WHERE id = %s", (review_id,))
            conn.commit()
            reply = f"❌ Rejected review with ID: {review_id}"

        cursor.close()
        conn.close()

        requests.post(f"https://api.telegram.org/bot{APPROVAL_TOKEN}/deleteMessage", json={
            "chat_id": chat_id,
            "message_id": message_id
        })

        requests.post(f"https://api.telegram.org/bot{APPROVAL_TOKEN}/sendMessage", json={
            "chat_id": chat_id,
            "text": reply
        })

        requests.post(f"https://api.telegram.org/bot{APPROVAL_TOKEN}/answerCallbackQuery", json={
            "callback_query_id": callback['id']
        })

    return jsonify({"status": "OK"}), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5002)