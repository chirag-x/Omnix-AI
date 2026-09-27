with open(r'e:\Coding\Omnix\ui\tray_manager.py', 'r', encoding='utf-8') as f:
    c = f.read()

avatar_menu = """                pystray.Menu.SEPARATOR,
                pystray.MenuItem("Restart Avatar", self._safe(self._on_restart_avatar)),"""

c = c.replace(
    'pystray.MenuItem("Sleep",         self._safe(self._on_sleep)),', 
    'pystray.MenuItem("Sleep",         self._safe(self._on_sleep)),\n' + avatar_menu
)

avatar_handler = """    def _on_restart_avatar(self):
        from avatar import avatar_process_manager
        avatar_process_manager.stop()
        import time; time.sleep(0.5)
        avatar_process_manager.start()

"""

c = c.replace('def _run(self):', avatar_handler + '    def _run(self):')

open(r'e:\Coding\Omnix\ui\tray_manager.py', 'w', encoding='utf-8').write(c)
