from flask import Flask, request, jsonify, send_from_directory
import cv2
import pytesseract
import numpy as np
from flask_cors import CORS
import re
import os

app = Flask(__name__)
CORS(app)

# Store persons temporarily (normally this would be in a database)
persons = []
items = []

@app.route('/scan-bill', methods=['POST'])
def scan_bill():
    if 'image' not in request.files:
        return jsonify({'error': 'No image provided'}), 400
    
    file = request.files['image']
    # Read and process image
    img = cv2.imdecode(np.frombuffer(file.read(), np.uint8), cv2.IMREAD_COLOR)
    text = pytesseract.image_to_string(img)
    
    # Process the text to extract items and prices
    items = process_receipt_text(text)
    return jsonify({'items': items})

@app.route('/save-bill', methods=['POST'])
def save_bill():
    data = request.json
    # Temporary: just return the data without saving
    return jsonify({
        'status': 'success', 
        'bill_id': '123',  # Dummy ID
        'data': data
    })

@app.route('/add-person', methods=['POST'])
def add_person():
    data = request.json
    if 'name' not in data:
        return jsonify({'error': 'Name is required'}), 400
    persons.append(data['name'])
    return jsonify({'persons': persons})

@app.route('/get-persons', methods=['GET'])
def get_persons():
    return jsonify({'persons': persons})

@app.route('/')
def index():
    return send_from_directory('.', 'index.html')

@app.route('/assign-item', methods=['POST'])
def assign_item():
    data = request.json
    if not all(k in data for k in ['itemIndex', 'selectedPersons']):
        return jsonify({'error': 'Missing required fields'}), 400
    
    # Update the assigned_to list for the item
    item_index = data['itemIndex']
    selected_persons = data['selectedPersons']
    
    if 0 <= item_index < len(items):
        items[item_index]['assigned_to'] = selected_persons
        return jsonify({
            'status': 'success',
            'item': items[item_index]
        })
    
    return jsonify({'error': 'Invalid item index'}), 400

# Modify the process_receipt_text function to include quantity
def process_receipt_text(text):
    # Split text into lines
    lines = text.split('\n')
    items = []
    
    for line in lines:
        # Look for price patterns (e.g., $10.99, 10.99, Rs.100, etc.)
        price_match = re.search(r'\$?\d+\.?\d*', line)
        if price_match:
            price = float(price_match.group().replace('₹', ''))
            # Get item name by removing the price and cleaning up
            item_name = line.replace(price_match.group(), '').strip()
            if item_name:
                items.append({
                    'name': item_name,
                    'price': price,
                    'quantity': 1,  # Default quantity
                    'assigned_to': []  # List of people assigned to this item
                })
    
    return items

if __name__ == '__main__':
    app.run(debug=True)
