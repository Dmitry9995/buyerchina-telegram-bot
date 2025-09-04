#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Простой запуск для Railway.app без лишних зависимостей
"""

import os
import logging
import sys

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def main():
    """Простой запуск Flask приложения"""
    logger.info("🚀 Starting BuyerChina Bot on Railway...")
    
    # Проверяем токен бота
    bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
    if not bot_token:
        logger.error("❌ TELEGRAM_BOT_TOKEN not found!")
        sys.exit(1)
    
    logger.info(f"✅ Bot token found: {bot_token[:10]}...")
    
    try:
        # Импортируем Flask приложение
        from flask_app import app
        logger.info("✅ Flask app imported successfully")
        
        # Получаем порт от Railway
        port = int(os.getenv('PORT', 5000))
        logger.info(f"🌐 Starting server on port {port}")
        
        # Запускаем приложение
        app.run(host='0.0.0.0', port=port, debug=False)
        
    except ImportError as e:
        logger.error(f"❌ Import error: {e}")
        logger.error("Make sure flask_app.py is in the same directory")
        sys.exit(1)
    except Exception as e:
        logger.error(f"❌ Server crashed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
