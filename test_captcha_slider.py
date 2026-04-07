import cv2
import numpy as np
import sys

def identify_gap_x_offset(bg_img_path):
    print(f"Loading {bg_img_path}")
    img = cv2.imread(bg_img_path)
    if img is None:
        print("Error loading image")
        return
        
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    edges = cv2.Canny(gray, 100, 200)
    h, w = edges.shape
    
    # The slider piece is typically on the far left. Let's crop it.
    slider_width_estimate = int(w * 0.20) # Assume slider piece is in the first 20%
    slider_template = edges[:, :slider_width_estimate]
    
    # We want to match this template against the REST of the image
    search_area = edges[:, slider_width_estimate:]
    
    res = cv2.matchTemplate(search_area, slider_template, cv2.TM_CCOEFF_NORMED)
    min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(res)
    
    # The true X offset from the very left edge of the image
    # is the location in the search area PLUS the width we cropped off.
    target_x = max_loc[0] + slider_width_estimate
    
    print(f"Match confidence: {max_val:.2f}")
    if max_val > 0.1:
        print(f"✅ Found target gap at X offset: {target_x}")
        # Draw the found location
        cv2.rectangle(img, (target_x, 0), (target_x + slider_width_estimate, h), (0, 0, 255), 2)
        cv2.imwrite('debug_captcha_result.png', img)
    else:
        print("❌ Could not confidently locate the gap.")
        
if __name__ == "__main__":
    test_img = sys.argv[1] if len(sys.argv) > 1 else 'test.png'
    identify_gap_x_offset(test_img)
