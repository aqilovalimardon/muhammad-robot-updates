# muhammad-robot-updates
Automatic updates for Muhammad's desktop robot

## v2.2.20 — petting, emotions and antenna light

- Move the pointer back and forth over the head or body **without holding a mouse button** to make the robot giggle. A single pass, tiny jitter, a drag, the menu and transparent corners do not count as petting.
- Three quick taps show a playful angry face for a moment. **Show next 3D emotion** also cycles through laughing, angry and the existing expressions.
- Softer squash and stretch, separate head/limb lag, and a gentle pulsing antenna halo that changes color with the expression.
- Quiet offline giggles respect **3D effect sounds: On / Off**. Open/Close cues take priority, and continued rubbing cannot flood the audio.
- 3D stays primary; the shared menu, code editor, voice commands and draggable cream orb retain their existing behavior.

The release workflow tests the actual Godot scene, exported Windows EXE, native Windows/Tk popup and installed updater before publishing. `--capture-review` exports real expression frames and WAV cues for review.
