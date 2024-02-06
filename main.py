import threading
import requests
import schedule
import time
import json
from flask import request, Flask, jsonify
from whatsapp_chatbot_python import GreenAPIBot, Notification
import logging
import os
logging.basicConfig(filename='app.log', level=logging.DEBUG, format='%(asctime)s %(levelname)s:%(message)s')
from whatsapp_api_client_python import API

app = Flask(__name__)

bot = GreenAPIBot(
    "7103890739", "20bb1e5836f24007a6f1a4ff84ddb8b8e4de20f34f8d4024bc"
)

API_TOKEN = "20bb1e5836f24007a6f1a4ff84ddb8b8e4de20f34f8d4024bc"


def call_my_api(message):
    try:
        response = requests.post('https://www.mprofyendpoint.net/predict', json={'query_text': message})
        if response.status_code == 200:
            return response.json().get('answer', 'Sorry, I could not process your request.')
        else:
            logging.error(f"API call failed with status code {response.status_code}: {response.text}")
            return 'Sorry, there was an error processing your request.'
    except Exception as e:
        logging.exception("Error calling mprofyendpoint API")
        return 'Sorry, there was an error processing your request.'

@bot.router.message()
def message_handler(notification: Notification):
    try:
        if hasattr(notification, 'text'):
            incoming_message = notification.text
        elif hasattr(notification, 'message_text'):
            incoming_message = notification.message_text
        elif hasattr(notification, 'body') and hasattr(notification.body, 'text'):
            incoming_message = notification.body.text
        else:
            raise AttributeError("Unable to find message text in the notification object")

        logging.info(f"Received message: {incoming_message}")

        api_response = call_my_api(incoming_message)

        logging.info(f"API response: {api_response}")

        notification.answer(api_response)

    except Exception as e:
        logging.exception("Error in message_handler")
        notification.answer('Sorry, there was an error processing your message.')



@app.route('/send_message', methods=['POST'])
def send_message():
    # Extract 'chat_id' and 'message' from the request's JSON body
    data = request.get_json()
    if not data:
        return jsonify({'error': 'No JSON payload received'}), 400
    
    chat_id = data.get('chat_id')
    message = data.get('message')
    if not chat_id or not message:
        return jsonify({'error': 'Missing "chat_id" or "message" in the JSON payload'}), 400

    api_url = f"https://api.green-api.com/waInstance7103890739/sendMessage/{API_TOKEN}"
    payload = json.dumps({"chatId": chat_id, "message": message})
    headers = {'Content-Type': 'application/json', 'Authorization': f'Bearer {API_TOKEN}'}
    response = requests.post(api_url, headers=headers, data=payload)
    print(response.text.encode('utf8'))
    return response.text

@app.route('/send_file', methods=['POST'])
def send_file():
    chat_id = request.form.get('chat_id')
    file_caption = request.form.get('file_caption')
    file = request.files.get('file')
    file_type = file.content_type  # Get the content type of the file

    # Check for missing data
    if not file or not chat_id or not file_caption:
        return jsonify({'error': 'Missing data'}), 400

    # Prepare the file data for the request
    files = {
        'file': (file.filename, file, file_type)
    }
    data = {
        'chatId': chat_id,
        'caption': file_caption
    }

    # Construct the headers for the request
    headers = {'Authorization': f'Bearer {API_TOKEN}'}
    api_url = f"https://api.green-api.com/waInstance7103890739/sendFileByUpload/{API_TOKEN}"

    # Attempt to send the file
    try:
        response = requests.post(api_url, headers=headers, data=data, files=files)
        response.raise_for_status()
        return jsonify(response.json()), 200
    except requests.exceptions.RequestException as e:
        # Handle all requests exceptions
        error_details = str(e.response.text) if e.response else str(e)
        print("Error:", error_details)
        return jsonify({'error': 'Request Error', 'details': error_details}), e.response.status_code if e.response else 500


def set_custom_reminder(time_str, message):
    schedule.every().day.at(time_str).do(lambda: send_message("84379760352@c.us", message))


@app.route('/get_contacts', methods=['GET'])
def get_contacts():
    api_url = f"https://api.green-api.com/waInstance7103890739/getContacts/{API_TOKEN}"
    headers = {'Authorization': f'Bearer {API_TOKEN}'}
    response = requests.get(api_url, headers=headers)
    if response.status_code == 200:
        return response.json()
    else:
        print("Failed to get contacts")
        return []

@app.route('/get_chat_history', methods=['GET'])
def get_chat_history():
    contact_id = request.args.get('contact_id')
    max_messages = request.args.get('max_messages', 100)  # Default to 100 if not provided

    # Debug print to check the contact_id format
    print("Contact ID:", contact_id)

    if not contact_id or not (contact_id.endswith("@c.us") or contact_id.endswith("@g.us")):
        return jsonify({"error": "Invalid contact ID format. Please use 'phone_number@c.us' or 'group_id@g.us'."}), 400

    api_url = f"https://api.green-api.com/waInstance7103890739/getChatHistory/{API_TOKEN}"
    payload = {
        "chatId": contact_id,
        "count": int(max_messages)  # Convert max_messages to int, as it will be a string from request.args
    }
    headers = {
        'Authorization': f'Bearer {API_TOKEN}',
        'Content-Type': 'application/json'
    }
    response = requests.post(api_url, headers=headers, json=payload)

    # Debug print to check the response from the API
    print("API Response:", response.text)

    if response.status_code == 200:
        return jsonify(response.json())
    else:
        error_msg = f"Failed to get chat history: {response.status_code}, {response.text}"
        return jsonify({"error": error_msg}), response.status_code
    
image_path = "pizza.png"

def SetProfilePicture(image_path):
    url = f"https://api.green-api.com/waInstance7103890739/setProfilePicture/{API_TOKEN}"
    payload = {}
    files = [('file', (image_path, open(image_path, 'rb'), 'image/jpeg'))]
    headers = {'Authorization': f'Bearer {API_TOKEN}'}
    response = requests.post(url, headers=headers, data=payload, files=files)
    print(response.text.encode('utf8'))
    return response.text

def filter_active_contacts():
    active_contacts = []
    contacts = get_contacts()
    for contact in contacts:
        chat_history = get_chat_history(contact['id'])
        if chat_history:
            active_contacts.append(contact['id'])
    return active_contacts


def run_scheduler():
    while True:
        try:
            schedule.run_pending()
            time.sleep(1)
        except Exception as e:
            with open("error_log.txt", "a") as file:
                file.write(f"An error occurred: {e}\n")

scheduler_thread = threading.Thread(target=run_scheduler, daemon=True)
scheduler_thread.start()


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
    bot.run_forever()
