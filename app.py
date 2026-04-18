from flask import Flask, request, jsonify
import json
import requests
import io
import zipfile
from PyPDF2 import PdfReader
from docx import Document
import pandas as pd

app = Flask(__name__)

TENDERLAND_API_KEY = "shds-AKUw2n4Yd07oKft2HPxY3mGLZyd"
GPTUNNEL_API_KEY = "f6290ba7-3284-46ea-bbe2-5999526a06f6"
ASSISTANT_ID = "@ai3834382"

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

def send_to_assistant(tender, docs_text):
    headers = {
        "Authorization": f"Bearer {GPTUNNEL_API_KEY}",
        "Content-Type": "application/json"
    }
    
    print(f"  🤖 Assistant ID: {ASSISTANT_ID}")
    
    # Формируем сообщение
    msg = f"""ТЕНДЕР № {tender.get('regNumber')}
{tender.get('name')}
Цена: {tender.get('beginPrice')} руб.

ДОКУМЕНТАЦИЯ:
{docs_text[:30000]}"""
    
    # Правильный эндпоинт GPTunnel для ассистентов
    url = f"https://gptunnel.ru/api/assistants/{ASSISTANT_ID}/chat"
    
    payload = {
        "messages": [
            {"role": "user", "content": msg}
        ]
    }
    
    print(f"  📡 POST {url}")
    
    try:
        r = requests.post(url, headers=headers, json=payload, timeout=60)
        print(f"  📡 Статус: {r.status_code}")
        print(f"  📡 Ответ: {r.text[:500]}")
        
        if r.status_code == 200:
            data = r.json()
            reply = data.get('reply') or data.get('response') or data.get('message')
            print(f"  ✅ Ответ ассистента: {reply[:300] if reply else 'Нет ответа'}")
        else:
            print(f"  ❌ Ошибка: {r.text}")
            
    except Exception as e:
        print(f"  ❌ Исключение: {type(e).__name__}: {e}")

@app.route('/tenderland-webhook', methods=['POST', 'GET'])
def webhook():
    if request.method == 'GET':
        return jsonify({"статус": "ок"}), 200
    
    print("\n" + "="*50)
    print("📨 ВЕБХУК ПОЛУЧЕН")
    
    data = request.json
    items = data.get('items', [])
    print(f"📦 Тендеров: {len(items)}")
    
    if items:
        item = items[0]
        tender = item.get('tender', {})
        files_url = tender.get('files')
        
        print(f"📋 {tender.get('regNumber')}")
        print(f"   {tender.get('name')[:60]}...")
        
        if files_url:
            print(f"   📁 Скачивание...")
            docs_text = download_files(files_url)
            if docs_text:
                print(f"   📄 Текст: {len(docs_text)} симв.")
                send_to_assistant(tender, docs_text)
    
    print("="*50)
    return jsonify({"статус": "ок"}), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
