#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import logging
from flask import Flask, request
import requests

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Токен бота
BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
if not BOT_TOKEN:
    logger.error("TELEGRAM_BOT_TOKEN not found!")
    exit(1)

BOT_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"
logger.info(f"Bot initialized: {BOT_TOKEN[:10]}...")

def send_message(chat_id, text):
    try:
        url = f"{BOT_URL}/sendMessage"
        data = {
            'chat_id': chat_id,
            'text': text
        }
        response = requests.post(url, json=data, timeout=10)
        logger.info(f"Message sent to {chat_id}: {response.status_code}")
        return response.json()
    except Exception as e:
        logger.error(f"Send message error: {e}")
        return None

def setup_webhook():
    """Setup webhook for Railway"""
    try:
        railway_url = os.getenv('RAILWAY_PUBLIC_DOMAIN')
        if railway_url:
            webhook_url = f"https://{railway_url}/webhook"
        else:
            webhook_url = f"https://web-production-ea35.up.railway.app/webhook"
        
        delete_url = f"{BOT_URL}/deleteWebhook"
        requests.post(delete_url, timeout=10)
        
        set_url = f"{BOT_URL}/setWebhook"
        data = {'url': webhook_url}
        response = requests.post(set_url, json=data, timeout=10)
        result = response.json()
        
        if result.get('ok'):
            logger.info(f"✅ Webhook set: {webhook_url}")
            return True
        else:
            logger.error(f"❌ Webhook failed: {result}")
            return False
    except Exception as e:
        logger.error(f"Webhook setup error: {e}")
        return False

@app.route('/')
def health():
    return "BuyerChina Bot is running!", 200

@app.route('/set_webhook')
def manual_webhook():
    """Manual webhook setup"""
    if setup_webhook():
        return "✅ Webhook set successfully!"
    else:
        return "❌ Webhook setup failed"

@app.route('/webhook_info')
def webhook_info():
    """Get webhook info"""
    try:
        url = f"{BOT_URL}/getWebhookInfo"
        response = requests.get(url, timeout=10)
        return response.json()
    except Exception as e:
        return {"error": str(e)}

@app.route('/webhook', methods=['POST'])
def webhook():
    try:
        data = request.get_json()
        logger.info(f"Received update: {data}")
        
        if 'message' in data:
            message = data['message']
            chat_id = message['chat']['id']
            user_name = message.get('from', {}).get('first_name', 'User')
            
            if 'text' in message and message['text'] == '/start':
                welcome_text = f"Welcome to BuyerChina, {user_name}! Your assistant for shopping in China."
                send_message(chat_id, welcome_text)
                
            elif 'photo' in message:
                response_text = f"Thank you for the photo, {user_name}! Our manager will contact you soon."
                send_message(chat_id, response_text)
                
            elif 'text' in message:
                text = message['text']
                response_text = f"Thank you for your request, {user_name}! Our manager will process your request."
                send_message(chat_id, response_text)
        
        return "OK", 200
    except Exception as e:
        logger.error(f"Webhook error: {e}")
        return "Error", 500

if __name__ == '__main__':
    try:
        logger.info("🚀 Starting BuyerChina Bot...")
        
        # Setup webhook on startup
        try:
            setup_webhook()
            logger.info("✅ Webhook setup completed")
        except Exception as e:
            logger.error(f"❌ Webhook setup failed: {e}")
        
        port = int(os.getenv('PORT', 5000))
        logger.info(f"Starting server on port {port}")
        app.run(host='0.0.0.0', port=port, debug=False)
    except Exception as e:
        logger.error(f"Startup error: {e}")
        # Minimal startup fallback
        port = int(os.getenv('PORT', 5000))
        app.run(host='0.0.0.0', port=port, debug=False)
