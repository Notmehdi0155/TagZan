# Davat_HotBot - main.py
from flask import Flask, request
from handlers import handle_message, handle_callback
from utils import ping_loop
import threading

app = Flask(__name__)

@app.route('/', methods=['POST'])
def webhook():
    data = request.json
    if 'message' in data:
        handle_message(data['message'])
    elif 'callback_query' in data:
        handle_callback(data['callback_query'])
    return 'ok'

@app.route('/')
def index():
    return 'Bot is running!'

if __name__ == '__main__':
    threading.Thread(target=ping_loop, daemon=True).start()
    app.run(host='0.0.0.0', port=8080)
