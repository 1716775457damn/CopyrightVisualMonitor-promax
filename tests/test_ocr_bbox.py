import cv2
import numpy as np
import pytesseract
import os
import mss

pytesseract.pytesseract.tesseract_cmd = r'C:\Tesseract-OCR\tesseract.exe'
os.environ['TESSDATA_PREFIX'] = os.path.abspath('tessdata')

img = cv2.imread("debug_last_screen.png")
    
gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
data = pytesseract.image_to_data(gray, lang='chi_sim', config='--psm 11', output_type=pytesseract.Output.DICT)

all_texts = []
valid_boxes = []
for i in range(len(data['text'])):
    t = str(data['text'][i]).replace(' ', '').strip()
    if t:
        all_texts.append(t)
        valid_boxes.append({
            'char': t,
            'x': data['left'][i],
            'y': data['top'][i],
            'w': data['width'][i],
            'h': data['height'][i]
        })

full_str = ''.join(b['char'] for b in valid_boxes)
for word in ['个人', '找回', '免']:
    idx = full_str.find(word)
    if idx != -1:
        match = valid_boxes[idx:idx+len(word)]
        if not match:
            continue
        try:
            min_x = min(b['x'] for b in match)
            min_y = min(b['y'] for b in match)
            max_x = max(b['x'] + b['w'] for b in match)
            max_y = max(b['y'] + b['h'] for b in match)
            cx = min_x + (max_x - min_x) // 2
            cy = min_y + (max_y - min_y) // 2
            print(f"Word: {word}, Center: ({cx}, {cy})")
        except Exception as e:
            print(f"Error on word {word}: {e}")

# If we still can't find anchor, print what Tesseract actually read
if '个人' not in full_str:
    print("Full OCR output:")
    print(full_str)
