# Muhammad Robot — Release Guide

This public repository distributes **application updates only** for Muhammad's Windows desktop robot.

## Privacy
Do **not** upload a child's Python scripts, voice recordings, private memory, Google Drive contents, API keys or credentials.

## Release layout
Create a GitHub Release with a tag like `v2.2.0`, and attach **both** files:
- `MuhammadRobot-2.2.0.zip` — contains only the program's `app/` files.
- `manifest.json` — contains `version`, `zip`, and `sha256`.

The updater checks the pinned GitHub repository, compares version numbers, downloads over HTTPS, verifies the SHA-256 and ZIP paths, and stages the new program in a new version directory. The user's personal files stay outside the updated directory.

## Installation transition
Existing v2.1.5 clients first receive v2.2 through the **existing Google Drive release flow**. From v2.2 onward the robot checks GitHub Releases periodically and can restart automatically when the Python editor is closed and no voice command is in progress.

## Rollback
The old application version is retained. Keep backups of both the local and Drive `MyCode` folders. A GitHub release is not proof of Windows compatibility: test it on the intended school-managed device before considering it stable.
