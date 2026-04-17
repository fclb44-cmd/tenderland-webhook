from flask import Flask, request, jsonify
import json
import threading
import requests
import time
import io
from PyPDF2 import PdfReader
from docx import Document
import pandas as pd

app = Flask(__name__)

# Ваши ключи
TENDERLAND_API_KEY = "shds-AKUw2n4Yd07oKft2HPxY3mGLZyd"
GPTUNNEL_API_KEY = "f6290ba7-3284-46ea-bbe2-5999526a06f6"
ASSISTANT_ID = "ai3834382"
GPTUNNEL_API_URL = "https://gptunnel.ru/v1"

def extract_text_from_bytes(file_bytes, filename):
    """Извлекает текст из PDF, DOCX или XLSX"""
    text = ""
    try:
        if filename.lower().endswith('.pdf'):
            with io.BytesIO(file_bytes) as f:
                reader = PdfReader(f)
                for page in reader.pages:
                    text += page.extract_text() or ""
        elif filename.lower().endswith('.docx'):
            with io.BytesIO(file_bytes) as f:
                doc = Document(f)
                for para in doc.paragraphs:
                    text += para.text + "\n"
        elif filename.lower().endswith('.xlsx'):
            with io.BytesIO(file_bytes) as f:
                df_dict = pd.read_excel(f, sheet_name=None)
                for sheet_name, df in df_dict.items():
                    text += f"--- Лист: {sheet_name} ---\n"
                    text += df.to_string() + "\n\n"
        else:
            text = f"[Неподдерживаемый формат: {filename}]"
    except Exception as e:
        text = f"[Ошибка извлечения: {e}]"
    return text

def download_tender_files(entity_id):
    """Скачивает все файлы тендера по entityId"""
    files_url = f"https://tenderland.ru/Api/File/GetAll?entityId={entity_id}&entityTypeId=1&apiKey={TENDERLAND_API_KEY}"
    all_text = ""
    
    try:
        response = requests.get(files_url, timeout=30)
        files_data = response.json()
        print(f"📁 Получен список файлов: {len(files_data) if isinstance(files_data, list) else 0}")
    except Exception as e:
        print(f"❌ Ошибка получения списка файлов: {e}")
        return ""
    
    if not isinstance(files_data, list):
        print(f"❌ Неверный формат списка файлов")
        return ""
    
    for file_info in files_data:
        file_name = file_info.get('FileName', 'unknown')
        file_url = file_info.get('Url')
        
        if not file_url:
            continue
            
        print(f"📥 Скачивание: {file_name}")
        
        try:
            file_response = requests.get(file_url, timeout=60)
            file_content = file_response.content
            text = extract_text_from_bytes(file_content, file_name)
            all_text += f"\n--- ФАЙЛ: {file_name} ---\n{text}\n"
        except Exception as e:
            print(f"❌ Ошибка скачивания {file_name}: {e}")
    
    return all_text

def send_to_gptunnel(tender_info, docs_text):
    """Отправляет данные в GPTunnel"""
    
    headers = {"Authorization": f"Bearer {GPTUNNEL_API_KEY}", "Content-Type": "application/json"}
    
    try:
        thread_resp = requests.post(f"{GPTUNNEL_API_URL}/threads", headers=headers, json={}, timeout=15)
        thread_id = thread_resp.json().get('id')
        print(f"🧵 Thread создан: {thread_id}")
    except Exception as e:
        print(f"❌ Ошибка создания thread: {e}")
        return
    
    # Обрезаем текст если слишком длинный
    if len(docs_text) > 50000:
        docs_text = docs_text[:50000] + "... [обрезано]"
    
    message = f"""ТЕНДЕР: {tender_info.get('name', 'Не указано')}
НОМЕР: {tender_info.get('regNumber', 'Не указан')}
ЦЕНА: {tender_info.get('beginPrice', 'Не указана')} руб.

ДОКУМЕНТАЦИЯ:
{docs_text}"""
    
    try:
        msg_payload = {"role": "user", "content": message}
        requests.post(f"{GPTUNNEL_API_URL}/threads/{thread_id}/messages", headers=headers, json=msg_payload, timeout=15)
        print(f"📤 Сообщение отправлено")
    except Exception as e:
        print(f"❌ Ошибка отправки: {e}")
        return
    
    try:
        run_payload = {"assistant_id": ASSISTANT_ID}
        requests.post(f"{GPTUNNEL_API_URL}/threads/{thread_id}/runs", headers=headers, json=run_payload, timeout=15)
        print(f"▶️ Ассистент запущен")
    except Exception as e:
        print(f"❌ Ошибка запуска: {e}")

def process_single_tender(data):
    """Обрабатывает один тендер (новый формат)"""
    
    # Выводим структуру для отладки
    print(f"🔍 Ключи данных: {list(data.keys())}")
    
    # Пробуем найти тендер в разных местах
    tender = data.get('tender', {})
    if not tender:
        tender = data
    
    reg_number = tender.get('regNumber') or tender.get('number') or data.get('tenderId')
    name = tender.get('name') or tender.get('title')
    entity_id = tender.get('entityId') or data.get('entityId') or data.get('id')
    files_url = tender.get('files')
    
    print(f"📋 regNumber: {reg_number}")
    print(f"📌 name: {name}")
    print(f"🆔 entityId: {entity_id}")
    print(f"📁 files: {files_url}")
    
    if files_url:
        print(f"📁 Скачивание документации...")
        docs_text = download_tender_files(entity_id) if entity_id else ""
        
        if docs_text:
            print(f"📄 Текст получен, {len(docs_text)} символов")
            tender_info = {
                'name': name,
                'regNumber': reg_number,
                'beginPrice': tender.get('beginPrice')
            }
            send_to_gptunnel(tender_info, docs_text)
        else:
            print(f"❌ Документация не получена")
    else:
        print(f"❌ Нет ссылки на файлы")

def process_in_background(data):
    """Фоновая обработка"""
    time.sleep(1)
    
    print(f"🔍 Тип данных: {type(data)}")
    
    if isinstance(data, list):
        print(f"📋 Обработка списка из {len(data)} элементов")
        for item in data[:3]:  # Только первые 3 для теста
            process_single_tender(item)
    else:
        print(f"📋 Обработка одного элемента")
        process_single_tender(data)
    
    print("\n✅ Обработка завершена")

@app.route('/tenderland-webhook', methods=['POST', 'GET'])
def webhook():
    print("="*50)
    print("📨 ВЕБХУК ПОЛУЧЕН")
    print("="*50)
    
    if request.method == 'GET':
        return jsonify({"статус": "ок"}), 200
    
    data = request.json
    print(f"📦 Данные получены")
    
    thread = threading.Thread(target=process_in_background, args=(data,))
    thread.start()
    
    return jsonify({"статус": "ок"}), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
