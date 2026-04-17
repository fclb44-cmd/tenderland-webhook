from flask import Flask, request, jsonify
import json
import threading
import requests
import time

app = Flask(__name__)

# Ваши ключи
TENDERLAND_API_KEY = "shds-AKUw2n4Yd07oKft2HPxY3mGLZyd"
GPTUNNEL_API_KEY = "f6290ba7-3284-46ea-bbe2-5999526a06f6"
ASSISTANT_ID = "ai3834382"
GPTUNNEL_API_URL = "https://gptunnel.ru/v1"

def process_tender(tender_data):
    """Обрабатывает один тендер в фоне"""
    tender = tender_data.get('tender', {})
    reg_number = tender.get('regNumber')
    name = tender.get('name')
    files_url = tender.get('files')
    
    print(f"📋 Обработка тендера: {reg_number} - {name}")
    
    if files_url:
        print(f"📁 Ссылка на файлы: {files_url}")
        # Здесь будет код для скачивания файлов
        # и отправки в GPTunnel
    
    return reg_number

def process_in_background(data):
    """Фоновая обработка всех тендеров"""
    time.sleep(1)  # Небольшая задержка
    
    if isinstance(data, list):
        for item in data:
            process_tender(item)
    else:
        process_tender(data)
    
    print("✅ Фоновая обработка завершена")

@app.route('/tenderland-webhook', methods=['POST', 'GET'])
def webhook():
    print("="*50)
    print("📨 ВЕБХУК ПОЛУЧЕН")
    print("="*50)
    
    if request.method == 'GET':
        return jsonify({"статус": "ок"}), 200
    
    data = request.json
    print(f"📦 Получено элементов: {len(data) if isinstance(data, list) else 1}")
    
    # Запускаем обработку в фоне
    thread = threading.Thread(target=process_in_background, args=(data,))
    thread.start()
    
    # Мгновенно отвечаем Tenderland
    return jsonify({"статус": "ок", "получено": len(data) if isinstance(data, list) else 1}), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
