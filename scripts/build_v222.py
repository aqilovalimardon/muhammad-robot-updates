#!/usr/bin/env python3
"""Build Muhammad Robot v2.2.2 from the public v2.2.1 release.
This patch adds only the 'About robot / version' menu item and bumps the version.
"""
from pathlib import Path
from zipfile import ZipFile
import hashlib
import json
import sys

SOURCE = Path(sys.argv[1])
DEST = Path(sys.argv[2])
DEST.parent.mkdir(parents=True, exist_ok=True)

MENU_OLD = "        self.menu.add_command(label='Drive folder settings',command=self.drive_settings)\n"
MENU_NEW = MENU_OLD + "        self.menu.add_command(label='About robot / version',command=self.show_version)\n"
DEF_OLD = "    def check_updates_now(self):\n"
DEF_NEW = (
    "    def show_version(self):\n"
    "        messagebox.showinfo('Muhammad Robot · Version',\n"
    "            f'Muhammad Robot v{APP_VERSION}\\n\\n'\n"
    "            'GitHub automatic update test release.\\n'\n"
    "            'Your voice commands, Python editor, and saved code are unchanged.',\n"
    "            parent=self.root)\n"
    "\n" + DEF_OLD
)

with ZipFile(SOURCE, 'r') as src, ZipFile(DEST, 'w') as dst:
    files = src.namelist()
    assert 'app/robot_app.py' in files and 'app/robot_core.py' in files
    for entry in src.infolist():
        content = src.read(entry.filename)
        if entry.filename == 'app/robot_app.py':
            text = content.decode('utf-8')
            if text.count(MENU_OLD) != 1 or text.count(DEF_OLD) != 1:
                raise RuntimeError('Unexpected v2.2.1 robot_app.py format')
            content = text.replace(MENU_OLD, MENU_NEW).replace(DEF_OLD, DEF_NEW).encode('utf-8')
        elif entry.filename == 'app/robot_core.py':
            text = content.decode('utf-8')
            old = "APP_VERSION = '2.2.1'"
            if text.count(old) != 1:
                raise RuntimeError('Unexpected v2.2.1 version')
            content = text.replace(old, "APP_VERSION = '2.2.2'").encode('utf-8')
        dst.writestr(entry, content)

with ZipFile(DEST, 'r') as z:
    assert z.testzip() is None
    assert b'About robot / version' in z.read('app/robot_app.py')
    assert b"APP_VERSION = '2.2.2'" in z.read('app/robot_core.py')

manifest = {
    'version': '2.2.2',
    'zip': DEST.name,
    'sha256': hashlib.sha256(DEST.read_bytes()).hexdigest(),
}
(DEST.parent / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n', encoding='utf-8')
print('Created', DEST, 'sha256=', manifest['sha256'])
