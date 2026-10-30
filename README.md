# muhammad-robot-updates
Automatic updates for Muhammad's desktop robot

## v2.2.22 — responsive menu and voice commands

- Replaces the modal Windows popup with a regular dismissible window. **Close robot** and **Open robot** keep running while it is open and dismiss the menu before changing the avatar.
- The belly button, right-click and middle-click share a non-modal menu. Click outside, switch windows or press Escape to dismiss it; selecting an action or giving Open/Close also closes it.
- All existing commands remain available in both 3D and Classic. The menu shows the current voice status and keeps the Classic avatar hidden when 3D is active.
- Regression checks exercise actual outside clicks, ongoing Tk timers, and real speech samples through the shipped host and 3D EXE with the menu open. The old native menu services timers on some Windows/Tk builds, so validation does not assume that it always blocks recognition. Physical microphone permissions and device selection still depend on the user's computer.

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

The release workflow tests the actual Godot scene, exported Windows EXE, Windows/Tk popup and its event timers and installed updater before publishing. `--capture-review` exports real expression frames and WAV cues for review.
