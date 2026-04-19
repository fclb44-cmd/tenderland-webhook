from flask import Flask, request, jsonify
import json
import requests
import io
import zipfile
import uuid
from PyPDF2 import PdfReader
from docx import Document
import pandas as pd

app = Flask(__name__)

TENDERLAND_API_KEY = "f6290ba7-3284-46ea-bbe2-5999526a06f6"
GPTUNNEL_API_KEY = "shds-AKUw2n4Yd07oKft2HPxY3mGLZyd"
ASSISTANT_CODE_SPEKTR = "ai3834382"
ASSISTANT_CODE_MARK = "ai5744545"

def extract_text(file_bytes, filename):
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
                    text += f"--- Лист: {sheet_name} ---\n{df.to_string()}\n\n"
    except Exception as e:
        text = f"[Ошибка: {e}]"
    return text

def download_files(files_url):
    all_text = ""
    try:
        print(f"  🔗 URL: {files_url}")
        response = requests.get(files_url, timeout=60)
        print(f"  📡 Статус: {response.status_code}")
        
        if response.content[:2] == b'PK':
            print(f"  📦 Это ZIP-архив, распаковываем...")
            with zipfile.ZipFile(io.BytesIO(response.content)) as z:
                file_list = z.namelist()
                print(f"  📁 Файлов в архиве: {len(file_list)}")
                
                for file_name in file_list[:10]:
                    print(f"  📥 {file_name}")
                    with z.open(file_name) as f:
                        file_bytes = f.read()
                        all_text += f"\n--- {file_name} ---\n"
                        all_text += extract_text(file_bytes, file_name)
        else:
            print(f"  ❌ Ответ не ZIP. Первые 2 байта: {response.content[:2]}")
            return ""
            
    except Exception as e:
        print(f"  ❌ Ошибка: {e}")
    return all_text

def call_assistant(assistant_code, message):
    headers = {
        "Authorization": f"Bearer {GPTUNNEL_API_KEY}",
        "Content-Type": "application/json"
    }
    
    chat_id = str(uuid.uuid4())
    
    payload = {
        "chatId": chat_id,
        "assistantCode": assistant_code,
        "message": message
    }
    
    print(f"  🤖 Assistant: {assistant_code}")
    print(f"  🆔 Chat ID: {chat_id}")
    
    try:
        r = requests.post(
            "https://gptunnel.ru/v1/assistant/chat",
            headers=headers,
            json=payload,
            timeout=60
        )
        print(f"  📡 Статус: {r.status_code}")
        
        if r.status_code == 200:
            data = r.json()
            reply = data.get('message', '')
            print(f"  ✅ Ответ получен ({len(reply)} симв.)")
            return reply
        else:
            print(f"  ❌ Ошибка: {r.text[:300]}")
            return None
            
    except Exception as e:
        print(f"  ❌ Исключение: {type(e).__name__}: {e}")
        return None

def find_responsible_in_data(data):
    """Поиск ответственного в данных Tenderland"""
    possible_fields = [
        'manager', 'Manager',
        'responsible', 'Responsible',
        'responsible_user', 'ResponsibleUser',
        'owner', 'Owner',
        'assigned_to', 'AssignedTo',
        'manager_id', 'ManagerId',
        'manager_name', 'ManagerName'
    ]
    
    # Поиск в корне
    for field in possible_fields:
        if field in data:
            return data[field]
    
    # Рекурсивный поиск
    def search(obj):
        if isinstance(obj, dict):
            for key, value in obj.items():
                if key.lower() in [f.lower() for f in possible_fields]:
                    return value
                result = search(value)
                if result:
                    return result
        elif isinstance(obj, list):
            for item in obj:
                result = search(item)
                if result:
                    return result
        return None
    
    return search(data)

@app.route('/tenderland-webhook', methods=['POST', 'GET'])
def webhook():
    if request.method == 'GET':
        return jsonify({"статус": "ок"}), 200
    
    print("\n" + "="*50)
    print("📨 ВЕБХУК ПОЛУЧЕН")
    
    data = request.json
    
    # ============================================================
    # 🔍 ПРОВЕРКА НАЛИЧИЯ ОТВЕТСТВЕННОГО
    # ============================================================
    print("\n🔍 ПОИСК ОТВЕТСТВЕННОГО В ВЕБХУКЕ:")
    print("-" * 40)
    
    responsible = find_responsible_in_data(data)
    
    if responsible:
        print(f"✅ ОТВЕТСТВЕННЫЙ НАЙДЕН: {responsible}")
    else:
        print("❌ ОТВЕТСТВЕННЫЙ НЕ НАЙДЕН")
        print("\n📋 КЛЮЧИ В КОРНЕ JSON:")
        for key in list(data.keys())[:10]:
            print(f"   - {key}")
        
        if 'items' in data and data['items']:
            item = data['items'][0]
            print("\n📋 КЛЮЧИ В items[0]:")
            for key in list(item.keys())[:10]:
                print(f"   - {key}")
            
            if 'tender' in item:
                print("\n📋 КЛЮЧИ В items[0]['tender']:")
                tender = item['tender']
                for key in list(tender.keys())[:15]:
                    print(f"   - {key}")
    
    print("-" * 40)
    
    items = data.get('items', [])
    print(f"\n📦 Тендеров: {len(items)}")
    
    if items:
        item = items[0]
        tender = item.get('tender', {})
        files_url = tender.get('files')
        
        print(f"\n📋 {tender.get('regNumber')}")
        print(f"   {tender.get('name')[:60]}...")
        
        if files_url:
            print(f"   📁 Скачивание...")
            docs_text = download_files(files_url)
            if docs_text:
                print(f"   📄 Текст: {len(docs_text)} симв.")
                
                # Отправка СПЕКТРу
                print(f"\n🔵 СПЕКТР:")
                spektr_response = call_assistant(
                    ASSISTANT_CODE_SPEKTR,
                    f"Проанализируй тендерную документацию:\n\n{docs_text[:30000]}"
                )
                
                # Отправка МАРКу
                print(f"\n🟢 МАРК:")
                mark_response = call_assistant(
                    ASSISTANT_CODE_MARK,
                    f"Заполни чек-лист по документации:\n\n{docs_text[:30000]}"
                )
    
    print("\n" + "="*50)
    return jsonify({"статус": "ок"}), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
