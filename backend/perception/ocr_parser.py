import pytesseract
from PIL import ImageGrab
import os
from utils.logger import log
from perception.text_targeting import build_tesseract_candidates

tesseract_path = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
if os.path.exists(tesseract_path):
    pytesseract.pytesseract.tesseract_cmd = tesseract_path

def get_ocr_elements(win, center_x):
    elements = []
    try:
        bbox = (win.left, win.top, win.right, win.bottom)
        img = ImageGrab.grab(bbox, all_screens=True)
        data = pytesseract.image_to_data(img, output_type=pytesseract.Output.DICT)
        
        candidates = build_tesseract_candidates(data, win.left, win.top)
        candidates = [candidate for candidate in candidates
                      if win.left <= candidate.center[0] < win.right
                      and win.top <= candidate.center[1] < win.bottom
                      and len(candidate.text.strip()) > 1]

        # Prefer complete phrases, then preserve reading order. This gives the
        # brain contact names and button labels instead of isolated OCR words.
        phrases = [candidate for candidate in candidates if candidate.source == "ocr-phrase"]
        phrases = [
            candidate for candidate in phrases
            if not any(
                other is not candidate
                and other.left <= candidate.left and other.right >= candidate.right
                and other.top <= candidate.center[1] <= other.bottom
                and len(other.text) > len(candidate.text)
                for other in phrases
            )
        ]
        singles = [candidate for candidate in candidates if candidate.source != "ocr-phrase"]
        selected = phrases if phrases else singles
        selected.sort(key=lambda candidate: (candidate.center[1], candidate.center[0]))
        for candidate in selected[:60]:
            x, y = candidate.center
            elements.append(
                f"[OCR Text conf={candidate.confidence:.2f}] '{candidate.text}' at X:{x}, Y:{y}"
            )
    except Exception as e:
        log.warning(f"OCR Parsing issue: {e}")
        
    return elements
