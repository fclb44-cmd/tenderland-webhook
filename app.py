from flask import Flask, request, jsonify
import json

app = Flask(__name__)

@app.route('/tenderland-webhook', methods=['POST', 'GET'])
def webhook():
    print("="*50)
    print("ВЕБХУК ПОЛУЧЕН")
    print("="*50)
    
    if request.method == 'GET':
        return jsonify({"статус": "ок"}), 200
    
    data = request.json
    print(f"Ключи верхнего уровня: {list(data.keys())}")
    
    items = data.get('items', [])
    print(f"Количество тендеров в items: {len(items)}")
    
    if items:
        for i, item in enumerate(items[:3]):  # Первые 3
            tender = item.get('tender', {})
            print(f"\n--- Тендер {i+1} ---")
            print(f"Номер: {tender.get('regNumber')}")
            print(f"Название: {tender.get('name')}")
            print(f"Файлы: {tender.get('files')}")
    
    return jsonify({"статус": "ок"}), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
