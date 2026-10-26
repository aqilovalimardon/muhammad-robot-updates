#!/usr/bin/env python3
"""Minimal auto-update verification: v2.2.3 -> v2.2.4.
Only APP_VERSION changes. No personal data, audio or visual changes.
"""
import hashlib
import json
import os
from pathlib import Path
import sys
from zipfile import ZipFile

src = Path(sys.argv[1])
dest = Path(sys.argv[2])
dest.parent.mkdir(parents=True, exist_ok=True)
expected = "a2da891b9d5db2a1b01f581670bfe47cfa1c6b9061210cd27b788c4eccb9ba77"
sha = hashlib.sha256(src.read_bytes()).hexdigest()
if sha != expected and os.environ.get("ALLOW_LOCAL_TEST_SHA") != sha:
    raise ValueError("Source ZIP does not match published verified v2.2.3 release")

with ZipFile(src, "r") as zin, ZipFile(dest, "w") as zout:
    names = zin.namelist()
    if not names or any(not p.startswith("app/") or ".." in Path(p).parts for p in names):
        raise ValueError("ZIP must contain only app/ files")
    if zin.testzip() is not None:
        raise ValueError("Corrupted v2.2.3 ZIP")
    if names.count("app/robot_core.py") != 1:
        raise ValueError("Unexpected app structure")
    for entry in zin.infolist():
        contents = zin.read(entry.filename)
        if entry.filename == "app/robot_core.py":
            text = contents.decode("utf-8")
            old, new = "APP_VERSION = '2.2.3'", "APP_VERSION = '2.2.4'"
            if text.count(old) != 1:
                raise ValueError("Wrong source version")
            text = text.replace(old, new)
            compile(text, "robot_core.py", "exec")
            contents = text.encode("utf-8")
        zout.writestr(entry, contents)

with ZipFile(dest) as result:
    if result.testzip() is not None:
        raise ValueError("Corrupted output ZIP")
    if b"APP_VERSION = '2.2.4'" not in result.read("app/robot_core.py"):
        raise ValueError("Version mismatch")

manifest = {
    "version": "2.2.4",
    "zip": dest.name,
    "sha256": hashlib.sha256(dest.read_bytes()).hexdigest(),
}
(dest.parent / "manifest.json").write_text(
    json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
)
print("Verified auto-update test release:", json.dumps(manifest))
