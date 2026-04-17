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
    print("ДАННЫЕ:")
    print(json.dumps(data, indent=2, ensure_ascii=False))
    
    return jsonify({"статус": "ок"}), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
