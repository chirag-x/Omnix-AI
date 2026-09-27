from pywinauto import Desktop
from utils.logger import log

def get_uia_elements(win, center_x):
    elements = []
    try:
        app = Desktop(backend="uia").window(handle=win._hWnd)
        children = []
        for control_type in ["Edit", "Button", "ListItem", "Hyperlink", "MenuItem", "Text"]:
            try:
                children.extend(app.descendants(control_type=control_type))
            except Exception:
                continue
        
        uia_elements = []
        for child in children:
            rect = child.rectangle()
            x = (rect.left + rect.right) // 2
            y = (rect.top + rect.bottom) // 2
            
            # The 'name' is often the placeholder or accessibility name
            name = child.element_info.name or ""
            # The 'window_text' is often the actual typed value in an Edit control
            val = child.window_text() or ""
            
            # Sometimes name and val are identical. Only treat val as actual input if it differs or is explicit.
            # PyWinAuto UIA for Edit: .window_text() is the user input. 
            
            is_edit = (child.element_info.control_type == "Edit")
            
            display_name = name if name else val
            control_type = child.element_info.control_type or "Element"
            if len(display_name.strip()) > 1 and win.top <= y < win.bottom and win.left <= x < win.right:
                uia_elements.append({
                    'name': display_name.strip(), 
                    'x': x, 
                    'y': y, 
                    'is_edit': is_edit,
                    'val': val.strip() if is_edit else "",
                    'control_type': control_type,
                })

        unique = {}
        for item in uia_elements:
            key = (item['name'].casefold(), item['x'] // 5, item['y'] // 5, item['control_type'])
            unique.setdefault(key, item)
        uia_elements = list(unique.values())

        # Reading order preserves nearby chat rows instead of hiding them based
        # on horizontal distance from the center of the window.
        uia_elements.sort(key=lambda e: (e['y'], e['x'], 0 if e['is_edit'] else 1))
        
        for el in uia_elements[:100]:
            if el['is_edit']:
                val_str = f" (Contains text: '{el['val']}')" if el['val'] else " (Empty)"
                elements.append(f"[Text Input] '{el['name']}'{val_str} at X:{el['x']}, Y:{el['y']}")
            else:
                elements.append(f"[UI {el['control_type']}] '{el['name']}' at X:{el['x']}, Y:{el['y']}")
    except Exception as e:
        log.warning(f"UIA Parsing issue: {e}")
        
    return elements
