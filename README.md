# LED Wall for the B.K. Light panel

Control the **Action B.K. Light LED matrix, article 3226274**, from a local web
interface. Use one panel or combine several into a shared canvas, upload images
and GIFs, and control playback from a phone on the same network.

Tested hardware: **64x16, device type `0x83`, MCU 14.02 / Bluetooth 7.04**.
Two physical panels have been tested on one Windows 11 host. This is an
experimental Windows preview; Linux Bluetooth playback is not validated.

**Interested in the investigation?** Start with
[what we found](docs/investigation-summary.md): autonomous playback, multi-panel
behavior, performance, persistence, and the limits of the advertised features.

## What the controller does

- Discover and identify panels without editing Bluetooth addresses in source.
- Configure a shared canvas with positions, rotation, row/column presets and
  variable bezel compensation. Hidden pixels behind the gap are not sent.
- Connect, disconnect or remove individual panels. Save the arrangement and
  which panels are enabled.
- Fit PNG images and GIFs to the full canvas before splitting them across panels.
- Stream a seam demo, with optional adaptive timing alignment across panels.
- Use a bundled phone-friendly interface with a short access code or QR code.
  One browser controls playback; other browsers can watch and take over.
- Play the optional Snake, Micromaze and Starfall demos from a phone or keyboard.

The host owns the Bluetooth connections and must stay running for web-controller
playback. The phone talks to the host over the local network. Preview shows the
intended image; it is not a readback of the LEDs.

## Try the Windows preview

The standalone Windows x64 build includes Python, dependencies and the web UI.
A local ZIP has been validated; a public download has not been published yet.
[Build instructions](docs/development.md#windows-standalone-preview) are available
for contributors. Once you have the ZIP:

1. Extract the entire folder and run `LED-Wall.exe`.
2. Power on the panels, enable Bluetooth and close iPixel Color or other panel
   controllers. Find nearby panels, add them, save the layout and connect.
3. Use Identify to check their order, then choose a demo or upload a PNG/GIF.
4. On a phone, open the host's displayed LAN address and enter its six-digit code,
   or scan the QR under **Use your phone**. Allow the application through the
   host firewall on your trusted private network if needed.

Keep the console open while using the controller. Settings live under
`%LOCALAPPDATA%\LED Wall`; uploaded media and game sessions are kept in memory.
Changing the active panel set briefly reconnects the remaining wall, resets
any game and clears uploaded media. Disconnecting stops updates; a panel can
continue displaying its last image.

## Run from source

Requires Python 3.11+ and Git. Python 3.13.9 is the tested runtime. From the
repository root on Windows:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[server]"
.\.venv\Scripts\python.exe -m led_matrix_hacker.server --host 0.0.0.0 --open
```

Alternatively, after installation, double-click
[Start LED Wall Web.cmd](Start%20LED%20Wall%20Web.cmd).
The pinned upstream dependency is installed automatically; no library patches
or private research checkout are needed. Omit `--host 0.0.0.0` for access only
from the host. Keep the access link/code private and use the service on a
trusted local network; it is not intended to be exposed to the internet.

Source-mode settings default to `.state/web-wall-settings.json`, separately
from standalone and desktop settings. Use `--settings` and `--capture-dir` to
choose other paths. Ubuntu/BlueZ investigation is documented in
[compatibility](docs/compatibility.md); working Linux playback is not claimed.

## Known limits

- **10 fps is an output target, not a guaranteed rate.** Observed upload speeds
  vary by panel and session; recent runs include roughly 4-5 updates/s on one
  panel and a faster second panel. The difference is still under investigation.
- Two panels are the hardware-tested baseline. The editor accepts up to 16
  within 512x512; larger configurations and radio capacity are untested.
- Timing alignment improved the observed two-panel test pattern. It does not
  provide an atomic display swap or a shared hardware refresh clock.
- GIFs in the web UI stream from the host. Autonomous native GIF upload and
  saved-slot selection were verified separately but are not exposed in this UI.
- Reconnection is explicit. Unattended service recovery, persistent media,
  a stable automation API and Home Assistant/MQTT integrations are not included.
- Snake needs a rectangular canvas with gap 0. Starfall fits its original 64x16
  scene to the wall. The optional Windows 12-fps profile belongs to the older
  single-panel desktop games; the web/wall worker does not use it.
- Clean-machine acceptance, Android Chrome checks and broader hardware testing
  remain outstanding. Phone control was confirmed in iPhone Safari; our lab
  needed a temporary LAN relay because direct Windows inbound access was blocked.

See [validation](docs/validation.md) for the actual measurements and conditions.

## Read further

| For | Start here |
| --- | --- |
| Buyers and curious owners | [Findings](docs/investigation-summary.md), [compatibility](docs/compatibility.md) |
| Protocol and hardware investigation | [Capability map](docs/panel-capabilities.md), [research archive](docs/archive/README.md) |
| Contributors | [Development](docs/development.md), [architecture](docs/architecture.md), [remaining work](docs/roadmap.md) |
| Older desktop interfaces and games | [Wall controller](games/wall/README.md), [game guides](games/README.md) |
| All documentation | [Documentation index](docs/README.md) |

## Credits and license

[pypixelcolor](https://github.com/lucagoc/pypixelcolor) supplies the command
builders, PNG/GIF framing, CRCs and acknowledgement transport.
[Bleak](https://github.com/hbldh/bleak) supplies platform Bluetooth access.
This repository adds the application lifecycle, layout, coordination, web
interface, renderers and documented experiments. It uses a tested upstream
revision; the [separate chunk-size contribution](patches/README.md) is not
required to run it.

Application code and original documentation/assets are [MIT licensed](LICENSE).
Dependencies and separately attributed third-party material keep their own
licenses. Standalone builds collect dependency notices. Downloaded APKs,
vendor artwork, raw captures and local device settings are not distributed.
