# muhammad-robot-updates
Automatic updates for Muhammad's desktop robot

## v2.2.21 — voice recovery and dizzy eyes

- Repairs **Hello robot**, **Close robot** and **Open robot**. Already-installed voice support disabled by an old input error is restored once; explicit microphone Off is recorded separately.
- Temporary microphone failures reconnect with bounded backoff, stopped audio streams are detected, and late events from an old microphone session are ignored.
- Downloading optional neural speech no longer pauses recognition. If it times out, speech falls back to Windows; both playback paths have bounded waits. Audio captured during the robot's own speech is discarded before recognition.
- Hold and shake the robot quickly back and forth to see rotating spiral eyes and a wobbly head. It settles after release; ordinary dragging and slow movements keep their existing behavior.
- Windows validation recognizes generated voice WAVs with the shipped Vosk grammar and drives the exported 3D EXE through the real host event and file bridge path. This validates the software path; physical microphone permissions and device availability remain local to each computer.

## v2.2.20 — petting, emotions and antenna light

- Move the pointer back and forth over the head or body **without holding a mouse button** to make the robot giggle. A single pass, tiny jitter, a drag, the menu and transparent corners do not count as petting.
- Three quick taps show a playful angry face for a moment. **Show next 3D emotion** also cycles through laughing, angry and the existing expressions.
- Softer squash and stretch, separate head/limb lag, and a gentle pulsing antenna halo that changes color with the expression.
- Quiet offline giggles respect **3D effect sounds: On / Off**. Open/Close cues take priority, and continued rubbing cannot flood the audio.
- 3D stays primary; the shared menu, code editor, voice commands and draggable cream orb retain their existing behavior.

The release workflow tests the actual Godot scene, exported Windows EXE, native Windows/Tk popup and installed updater before publishing. `--capture-review` exports real expression frames and WAV cues for review.
