import cv2
import numpy as np
import pytesseract
import os

pytesseract.pytesseract.tesseract_cmd = r'C:\Tesseract-OCR\tesseract.exe'
os.environ['TESSDATA_PREFIX'] = os.path.abspath('tessdata')

img = cv2.imread("debug_last_screen.png")
if img is not None:
    # Crop to the approximate login panel area to avoid background noise and Otsu skew
    # The panel is roughly on the right half of the screen
    h, w = img.shape[:2]
    panel = img[int(h*0.2):int(h*0.8), int(w*0.5):w]
    
    gray = cv2.cvtColor(panel, cv2.COLOR_BGR2GRAY)
    
    # Try different thresholds
    _, thresh = cv2.threshold(gray, 128, 255, cv2.THRESH_BINARY)
    data = pytesseract.image_to_data(thresh, lang='chi_sim', config='--psm 11', output_type=pytesseract.Output.DICT)
    
    print(f"--- Threshold: 128 ---")
    for i in range(len(data['text'])):
        t = str(data['text'][i]).replace(' ', '').strip()
        if t:
            x, y = data['left'][i], data['top'][i]
            print(f"'{t}': (x={x}, y={y})")
