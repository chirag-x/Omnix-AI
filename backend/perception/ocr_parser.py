import pytesseract
from PIL import ImageGrab
import os
from utils.logger import log

tesseract_path = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
if os.path.exists(tesseract_path):
    pytesseract.pytesseract.tesseract_cmd = tesseract_path

def get_ocr_elements(win, center_x):
    elements = []
    try:
        bbox = (win.left, win.top, win.right, win.bottom)
        img = ImageGrab.grab(bbox)
        data = pytesseract.image_to_data(img, output_type=pytesseract.Output.DICT)
        
        ocr_elements = []
        for i in range(len(data['text'])):
            text = data['text'][i].strip()
            if len(text) > 2:
                x = win.left + data['left'][i] + (data['width'][i] // 2)
                y = win.top + data['top'][i] + (data['height'][i] // 2)
                if 0 <= y <= win.height and 0 <= x <= win.width:
                    ocr_elements.append({'text': text, 'x': x, 'y': y})
        
        ocr_elements.sort(key=lambda e: abs(e['x'] - center_x))
        
        for el in ocr_elements[:30]:
            elements.append(f"[Text] '{el['text']}' at X:{el['x']}, Y:{el['y']}")
    except Exception as e:
        log.warning(f"OCR Parsing issue: {e}")
        
    return elements
