import os
import webview
import argparse

def start_renderer(click_through=False, on_top=True, scale=1.0):
    current_dir = os.path.dirname(os.path.abspath(__file__))
    index_path = os.path.join(current_dir, "renderer", "index.html")
    
    size = int(300 * scale)

    window = webview.create_window(
        'Omnix Avatar',
        url=f'file://{index_path}',
        transparent=True,
        frameless=True,
        on_top=on_top,
        width=size,
        height=size,
        easy_drag=True
    )
    
    # In Windows, setting WS_EX_TRANSPARENT via ctypes could enable click-through, 
    # but pywebview doesn't expose HWND natively cleanly without digging. 
    # For now, frameless and transparent is enough for basic desktop widget.
    webview.start(gui='edgechromium' if os.name == 'nt' else None)

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("--click-through", action="store_true")
    parser.add_argument("--scale", type=float, default=1.0)
    parser.add_argument("--on-top", action="store_true", default=True)
    args = parser.parse_args()
    start_renderer(click_through=args.click_through, on_top=args.on_top, scale=args.scale)
