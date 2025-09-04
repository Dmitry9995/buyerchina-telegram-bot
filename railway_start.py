#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import json
import logging
import sys

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)

def setup_environment():
    """Настройка окружения для Railway"""
    try:
        # Проверяем токен бота
        bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
        if not bot_token:
            logger.error("❌ TELEGRAM_BOT_TOKEN not found!")
            return False
        
        logger.info(f"✅ Bot token found: {bot_token[:10]}...")
        
        # Настраиваем credentials.json
        credentials_json = os.getenv('GOOGLE_CREDENTIALS_JSON')
        if credentials_json:
            try:
                # Проверяем что это валидный JSON
                json.loads(credentials_json)
                
                # Создаем файл
                with open('credentials.json', 'w', encoding='utf-8') as f:
                    f.write(credentials_json)
                
                logger.info("✅ credentials.json created")
                
                # Устанавливаем переменную для Google
                os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = 'credentials.json'
                
            except json.JSONDecodeError as e:
                logger.error(f"❌ Invalid JSON in GOOGLE_CREDENTIALS_JSON: {e}")
                return False
        else:
            logger.warning("⚠️ GOOGLE_CREDENTIALS_JSON not found - Google Sheets disabled")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Environment setup failed: {e}")
        return False

def main():
    """Главная функция запуска"""
    logger.info("🚀 Starting BuyerChina Bot on Railway...")
    
    if not setup_environment():
        logger.error("❌ Environment setup failed!")
        sys.exit(1)
    
    try:
        # Импортируем и запускаем бота
        from bot_production import main as bot_main
        logger.info("🤖 Launching bot...")
        bot_main()
        
    except ImportError as e:
        logger.error(f"❌ Import error: {e}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"❌ Bot crashed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
