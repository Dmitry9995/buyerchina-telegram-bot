# 🔧 Google Credentials Setup Guide

## Проблема: Invalid JSON in GOOGLE_CREDENTIALS_JSON

Ошибка `Extra data: line 1 column 7 (char 6)` означает неправильный формат JSON в переменной окружения.

## ✅ Правильный формат для Railway:

### 1. Скачайте credentials.json из Google Cloud Console

### 2. Откройте файл и скопируйте ВЕСЬ JSON как одну строку:

```json
{"type":"service_account","project_id":"your-project","private_key_id":"...","private_key":"-----BEGIN PRIVATE KEY-----\n...","client_email":"...","client_id":"...","auth_uri":"...","token_uri":"...","auth_provider_x509_cert_url":"...","client_x509_cert_url":"..."}
```

### 3. В Railway Variables добавьте:
- **Имя**: `GOOGLE_CREDENTIALS_JSON`
- **Значение**: Вставьте JSON БЕЗ кавычек, БЕЗ переносов строк

### ❌ Неправильно:
```
"{"type":"service_account"...}"
```

### ✅ Правильно:
```
{"type":"service_account","project_id":"your-project"...}
```

## 🔍 Проверка после исправления:

1. Перезапустите деплой в Railway
2. Проверьте: `https://ваш-домен.railway.app/sheets_status`
3. Тестируйте: `https://ваш-домен.railway.app/test_sheets`

## 📋 Если все еще не работает:

1. Убедитесь что Service Account имеет роль "Editor"
2. Включите Google Sheets API в Google Cloud Console
3. Расшарьте таблицу с email Service Account
