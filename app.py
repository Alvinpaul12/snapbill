from flask import Flask, request, jsonify, send_from_directory
import cv2
import pytesseract
import numpy as np
from flask_cors import CORS
import re
import os
from PIL import Image
import math

pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

app = Flask(__name__)
CORS(app)

# Store persons temporarily (normally this would be in a database)
persons = []
items = []

def enhance_image(img):
    # Enhance image quality
    img = cv2.resize(img, None, fx=1.5, fy=1.5, interpolation=cv2.INTER_CUBIC)
    # Apply adaptive thresholding
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    thresh = cv2.adaptiveThreshold(blurred, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2)
    # Noise removal
    kernel = np.ones((1, 1), np.uint8)
    erosion = cv2.erode(thresh, kernel, iterations=1)
    dilation = cv2.dilate(erosion, kernel, iterations=1)
    return dilation

def detect_text_regions(img):
    # Find contours to detect text regions
    contours, hierarchy = cv2.findContours(img, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    regions = []
    for contour in contours:
        x, y, w, h = cv2.boundingRect(contour)
        if w > 50 and h > 10:  # Filter small regions
            regions.append((x, y, w, h))
    return sorted(regions, key=lambda r: r[1])  # Sort by y-coordinate

@app.route('/scan-bill', methods=['POST'])
def scan_bill():
    if 'image' not in request.files:
        return jsonify({'error': 'No image provided'}), 400
    
    file = request.files['image']
    img = cv2.imdecode(np.frombuffer(file.read(), np.uint8), cv2.IMREAD_COLOR)
    
    # Enhanced preprocessing
    processed_img = enhance_image(img)
    
    # Detect text regions
    regions = detect_text_regions(processed_img)
    
    # Extract text from regions with different configurations
    extracted_text = []
    for x, y, w, h in regions:
        roi = processed_img[y:y+h, x:x+w]
        # Use different PSM modes based on region size
        if w > 300:  # Likely full line
            config = '--oem 3 --psm 6'
        else:  # Likely single word/number
            config = '--oem 3 --psm 7'
        text = pytesseract.image_to_string(roi, config=config).strip()
        if text:
            extracted_text.append(text)
    
    # Process extracted text
    items = process_receipt_text('\n'.join(extracted_text))
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
    lines = [line.strip() for line in text.split('\n') if line.strip()]
    items = []
    
    # Improved patterns
    price_pattern = r'(?:[\$₹]\s*(\d+(?:\.\d{2})?))|\s(\d+(?:\.\d{2}))(?!\d)'
    quantity_pattern = r'^(?:(\d+)\s*[xX]?\s*)|(?:([xX]\s*\d+)\s*)'
    ignore_pattern = r'(?i)(total|sub\s*total|tax|cash|change|balance|card|payment|invoice|date|time|thank|welcome)'
    
    for line in lines:
        if re.search(ignore_pattern, line):
            continue
            
        # Extract quantity
        quantity = 1
        q_match = re.search(quantity_pattern, line)
        if q_match:
            quantity = int(re.findall(r'\d+', q_match.group())[0])
            line = re.sub(quantity_pattern, '', line).strip()
        
        # Extract price
        price_match = re.search(price_pattern, line)
        if price_match:
            try:
                price_str = price_match.group(1) or price_match.group(2)
                price = float(price_str)
                
                # Get item name
                item_name = line[:line.rfind(price_str)].strip()
                item_name = re.sub(r'[^\w\s-]', '', item_name)
                item_name = ' '.join(word.capitalize() for word in item_name.split())
                
                if item_name and price > 0:
                    items.append({
                        'name': item_name,
                        'price': price,
                        'quantity': quantity,
                        'assigned_to': []
                    })
            except (ValueError, AttributeError):
                continue
    
    return items

if __name__ == '__main__':
    app.run(debug=True)
