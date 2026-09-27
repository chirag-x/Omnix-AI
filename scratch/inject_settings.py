with open(r'e:\Coding\Omnix\backend\core\settings.py', 'r', encoding='utf-8') as f:
    c = f.read()

avatar_defaults = """    "avatar_enabled": True,
    "avatar_always_on_top": True,
    "avatar_click_through": False,
    "avatar_scale": 1.0,
    "avatar_position_x": 0,
    "avatar_position_y": 0,
    "avatar_model_path": "",
    "avatar_renderer_port": 21212,
"""
c = c.replace('"vision_cloud_confidence": 0.86,', '"vision_cloud_confidence": 0.86,\n' + avatar_defaults)

open(r'e:\Coding\Omnix\backend\core\settings.py', 'w', encoding='utf-8').write(c)
