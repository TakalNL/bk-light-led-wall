LED Wall - Windows x64 preview

1. Extract the entire ZIP into a folder. Keep LED-Wall.exe and _internal together.
2. Power on the LED panels and close iPixel Color and other panel controllers.
3. Double-click LED-Wall.exe. Keep its console window open while using the wall.
4. Your browser opens automatically. Find nearby panels, add them, save the layout,
   then connect. Identify labels help confirm their physical order.
   Each panel card has Connect, Disconnect and Remove controls. Disconnect keeps
   its saved position; Remove forgets it. Changing the active set briefly
   reconnects the remaining wall. A disconnected panel may keep its last image.
5. On a phone using the same local network, type the address shown by LED Wall
   and enter its six-digit code. Or scan the QR under "Use your phone" on the PC.

No Python, Git or Node installation is required. Bluetooth must be enabled.
If Windows asks about network access, allow it on your trusted private network
to use a phone. Network/firewall restrictions can prevent phone access.

The PC runs Bluetooth and the games. Keep it awake and within Bluetooth range.
Closing a browser pauses its game controls; close the console to stop the service.
To stop from the console, press Ctrl+C and wait for Bluetooth cleanup.

Settings and captures are stored in %LOCALAPPDATA%\LED Wall, outside this folder.
Setup is remembered, but reconnecting remains explicit. Uploaded media is currently
kept in memory. GIFs are streamed while LED Wall runs; native saved-slot controls
are not included in this preview.

Tested panel: B.K. Light / Action article 3226274, 64x16, device type 0x83.
Two-panel Windows output has been tested. Linux Bluetooth validation is pending.
Layouts above two panels are experimental and have not been tested on hardware.
The wall targets up to 10 updates per second, but achieved rates vary. Our tested
panels have shown different upload speeds, including roughly 4-5 updates/s.
Snake needs a rectangular wall with gap 0; Starfall fits its original 64x16 scene.

This preview is unsigned and has not been tested on a second clean Windows PC.
The application is MIT licensed; see LICENSE.txt. Third-party dependencies keep
their own licenses. Dependency notices and the exact build environment are
included in licenses and build-info.json.
