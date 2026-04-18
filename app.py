from flask import Flask, request, jsonify
import json
import requests
import io
import time
from PyPDF2 import PdfReader
from docx import Document
import pandas as pd

app = Flask(__name__)

# ✅ ПРАВИЛЬНЫЕ КЛЮЧИ
TENDERLAND_API_KEY = "shds-AKUw2n4Yd07oKft2HPxY3mGLZyd"
GPTUNNEL_API_KEY = "f6290ba7-3284-46ea-bbe2-5999526a06f6"
ASSISTANT_ID = "ai3834382"
GPTUNNEL_API_URL = "https://gptunnel.ru/v1"

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
        response = requests.get(files_url, timeout=30)
        print(f"  📡 Статус: {response.status_code}")
        print(f"  📄 Ответ (первые 300 симв): {response.text[:300]}")
        
        try:
            files_list = response.json()
        except Exception as e:
            print(f"  ❌ Ответ не JSON: {e}")
            return ""
        
        if not isinstance(files_list, list):
            print(f"  ❌ Ответ не список: {type(files_list)}")
            return ""
        
        print(f"  📁 Файлов: {len(files_list)}")
        
        for f in files_list[:5]:
            file_name = f.get('FileName', 'file')
            file_url = f.get('Url')
            if file_url:
                print(f"  📥 {file_name}")
                resp = requests.get(file_url, timeout=60)
                all_text += f"\n--- {file_name} ---\n"
                all_text += extract_text(resp.content, file_name)
    except Exception as e:
        print(f"  ❌ Ошибка: {e}")
    return all_text

def send_to_assistant(tender, docs_text):
    headers = {"Authorization": f"Bearer {GPTUNNEL_API_KEY}", "Content-Type": "application/json"}
    try:
        r = requests.post(f"{GPTUNNEL_API_URL}/threads", headers=headers, json={}, timeout=15)
        thread_id = r.json().get('id')
        print(f"  🧵 Thread: {thread_id}")
        
        msg = f"""ТЕНДЕР № {tender.get('regNumber')}
{tender.get('name')}
Цена: {tender.get('beginPrice')} руб.

ДОКУМЕНТАЦИЯ:
{docs_text[:30000]}"""
        
        requests.post(f"{GPTUNNEL_API_URL}/threads/{thread_id}/messages", headers=headers, json={"role": "user", "content": msg}, timeout=15)
        requests.post(f"{GPTUNNEL_API_URL}/threads/{thread_id}/runs", headers=headers, json={"assistant_id": ASSISTANT_ID}, timeout=15)
        print(f"  ✅ Отправлено")
    except Exception as e:
        print(f"  ❌ Ошибка GPTunnel: {e}")

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
