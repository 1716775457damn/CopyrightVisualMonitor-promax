import cv2
import numpy as np
import sys
import pytesseract

pytesseract.pytesseract.tesseract_cmd = r'C:\Tesseract-OCR\tesseract.exe'

def find_text_on_screen(img, target_text, lang='chi_sim', binarize=False):
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    scale = 1.0
    data = pytesseract.image_to_data(gray, lang=lang, config='--psm 11', output_type=pytesseract.Output.DICT)
    
    all_texts = []
    valid_boxes = []
    for i in range(len(data['text'])):
        text = str(data['text'][i]).replace(' ', '').strip()
        if text:
            all_texts.append(text)
            for char in text:
                valid_boxes.append({
                    'char': char,
                    'x': int(data['left'][i] / scale),
                    'y': int(data['top'][i] / scale),
                    'w': int(data['width'][i] / scale),
                    'h': int(data['height'][i] / scale)
                })
            
    full_ocr_str = "".join(b['char'] for b in valid_boxes)
    if binarize == False:
        print(f"DEBUG OCR string (len={len(full_ocr_str)}): {full_ocr_str[:150]}...")
        
    idx = full_ocr_str.find(target_text)
    if idx != -1:
        match_boxes = valid_boxes[idx:idx+len(target_text)]
        min_x = min(b['x'] for b in match_boxes)
        min_y = min(b['y'] for b in match_boxes)
        max_x = max(b['x'] + b['w'] for b in match_boxes)
        max_y = max(b['y'] + b['h'] for b in match_boxes)
        cx = min_x + (max_x - min_x) // 2
        cy = min_y + (max_y - min_y) // 2
        return (cx, cy), (min_x, min_y, max_x - min_x, max_y - min_y), all_texts
    return None, None, all_texts

def debug_crop():
    bg_img_path = r"C:\Users\UserX\.gemini\antigravity\brain\4552a260-8189-46b2-a1e5-e89be368fd0b\media__1772290416007.png"
    img = cv2.imread(bg_img_path)
    if img is None:
        print("Failed to load image")
        return
        
    title_hint, bbox, _ = find_text_on_screen(img, "安全验证")
    if not title_hint:
        title_hint, bbox, _ = find_text_on_screen(img, "请完成")
        
    if title_hint:
        print(f"Found title hint at {title_hint}, bbox: {bbox}")
        sx, sy, sw, sh = bbox
        
        cv2.rectangle(img, (sx, sy), (sx+sw, sy+sh), (0, 255, 0), 2)
        
        # Based on "请完成安全验证" title at the top left
        # The puzzle image is directly below the title padding
        img_top = sy + sh + 15
        img_bottom = img_top + 212
        img_left = sx - 20
        img_right = img_left + 340
        
        print(f"Estimated crop area: L:{img_left}, R:{img_right}, T:{img_top}, B:{img_bottom}")
        cv2.rectangle(img, (img_left, img_top), (img_right, img_bottom), (0, 0, 255), 2)
        
        # Crop and do Canny
        if img_top > 0 and img_left > 0:
            captcha_img = img[img_top:img_bottom, img_left:img_right]
            cv2.imwrite("debug_crop.png", captcha_img)
            
            gray = cv2.cvtColor(captcha_img, cv2.COLOR_BGR2GRAY)
            edges = cv2.Canny(gray, 100, 200)
            ch, cw = edges.shape
            
            slider_width_estimate = 65 # Standard puzzle piece width is around 50-60px
            slider_template = edges[:, :slider_width_estimate]
            search_area = edges[:, slider_width_estimate:]
            
            res = cv2.matchTemplate(search_area, slider_template, cv2.TM_CCOEFF)
            min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(res)
            
            target_x_offset = max_loc[0] + slider_width_estimate
            print(f"TM_CCOEFF offset: {target_x_offset} with max_val {max_val}")
            
            # draw result on crop
            cv2.rectangle(captcha_img, (target_x_offset, 0), (target_x_offset+slider_width_estimate, ch), (255, 0, 0), 2)
            cv2.imwrite("debug_crop_result.png", captcha_img)
            
        cv2.imwrite("debug_layout.png", img)
    else:
        print("Hint not found")

if __name__ == "__main__":
    debug_crop()
