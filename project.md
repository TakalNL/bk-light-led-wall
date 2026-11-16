# Project: LED Matrix Hacker
## Reverse-engineering and controlling a B.K. Light Bluetooth LED matrix with Python

We are starting a new hobby engineering project to reverse-engineer a cheap Bluetooth LED matrix purchased from Action in the Netherlands.

Our goal is to control the matrix directly from Python, without depending on the manufacturer's mobile application.

Ultimately, we want to render custom pixel art, animated sprites, scrolling text, and possibly synchronize multiple matrices.

**Important: This is an experimental hardware reverse-engineering project. Investigate first, implement second. Do not invent protocol details or assume compatibility with existing projects.**

---

# 1. Hardware information

Known information:

- **Brand:** B.K. Light
- **Product:** Flexible LED Matrix
- **Retailer:** Action, Netherlands
- **Action article number:** 3226274
- **Advertised resolution:** 16 × 51 pixels (816 LEDs)
- **Power:** 5V USB
- **Connectivity:** Bluetooth
- **Control:** Manufacturer's mobile application
- **Advertised feature:** Dual-panel pairing mode
- **Purchase price:** Approximately €15

The panel has not yet been fully investigated.

We do not know:

- The controller chipset.
- Whether it uses Bluetooth Low Energy or Bluetooth Classic.
- The Bluetooth device name.
- Its service and characteristic UUIDs.
- The communication protocol.
- Its pixel encoding or color order.
- Its maximum frame rate.
- Whether animations are streamed or uploaded.
- Whether the advertised resolution exactly matches the physical pixel layout.
- Whether it is compatible with other B.K. Light products.

Do not assume any of these details.

# 2. Research existing GitHub implementations first

Before writing a custom Bluetooth protocol, inspect existing open-source projects.

We may be able to adapt a working implementation rather than reverse-engineering everything ourselves.

## Priority 1: B.K. Light devices sold at Action

### Repository A: Bk-Light-AppBypass

https://github.com/Pupariaa/Bk-Light-AppBypass

Reportedly a Python toolkit using Bleak and Pillow to control B.K. Light ACT1025 (64×16) and ACT1026 (32×32) matrices sold at Action.

Investigate:

- Supported device models.
- Bluetooth device discovery.
- GATT services and characteristics.
- Connection initialization.
- Device handshake.
- Packet structures.
- Image and animation transmission.
- Pixel mapping and orientation.
- Brightness control.
- Acknowledgments and flow control.
- Multiple-panel management.
- Error handling and reconnection.

This is our highest-priority reference because the brand and retailer match our hardware.

### Repository B: BK-Light-LED-rx-engine

https://github.com/mx2rel/BK-Light-LED-rx-engine

Reportedly a JavaScript/Web Bluetooth toolkit for a B.K. Light 64×16 LED Fun Screen purchased at Action.

Investigate:

- Bluetooth communication.
- Framebuffer representation.
- RGB encoding.
- Packet fragmentation.
- Rendering pipeline.
- Real-time animation.
- Frame transmission latency.
- Reports of accumulating lag during continuous frame transmission.
- Example applications such as games, clocks, or status displays.

Compare its protocol with Repository A.

Determine whether they use the same controller or different protocol families.

## Priority 2: Related Bluetooth LED protocols

### Repository C: coolledx-driver

https://github.com/UpDryTwist/coolledx-driver

Investigate its Python architecture and any relevant Bluetooth image-upload mechanisms.

### Repository D: coolledux-ble

https://github.com/CharlesLennon/coolledux-ble

Investigate its reverse-engineered BLE protocol, message framing, and image/animation encoding.

### Repository E: mi-led-display

https://github.com/offe/mi-led-display

Investigate its Bluetooth snoop-log analysis techniques and pixel rendering implementation.

## Research requirements

For each repository:

1. Verify that the repository exists and inspect its actual code.
2. Read the README and available documentation.
3. Identify supported hardware.
4. Determine its Bluetooth transport and protocol.
5. Identify reusable ideas or components.
6. Check the license before copying code.
7. Note maintenance status and relevant limitations.
8. Document evidence of compatibility or incompatibility with our hardware.

Create `RESEARCH.md` containing a comparison table.

Clearly distinguish:

- Confirmed findings.
- Plausible similarities.
- Unverified assumptions.
- Known incompatibilities.

**Do not assume that a 16×51 matrix uses the same protocol as a 16×64 matrix.**

If repositories are inaccessible, record that limitation rather than inventing their contents.

# 3. Project architecture

Create a maintainable Python project named:

`led-matrix-hacker`

Use Python 3.11 or newer where available.

Preferred libraries:

- `bleak` — Bluetooth Low Energy communication.
- `Pillow` — Image generation and pixel manipulation.
- `pytest` — Automated testing.
- `argparse` or `Typer` — Command-line interface.
- Python standard-library logging.
- `asyncio` — Asynchronous communication and animation scheduling.

Avoid unnecessary dependencies.

Suggested structure:

```text
led-matrix-hacker/
├── README.md
├── RESEARCH.md
├── PROTOCOL.md
├── pyproject.toml
├── src/
│   └── led_matrix_hacker/
│       ├── __init__.py
│       ├── cli.py
│       ├── discovery.py
│       ├── transport.py
│       ├── protocol.py
│       ├── framebuffer.py
│       ├── animation.py
│       └── device.py
├── examples/
│   ├── scan.py
│   ├── inspect_device.py
│   ├── solid_colors.py
│   ├── pixel_test.py
│   └── sprite_animation.py
├── tests/
│   ├── test_framebuffer.py
│   ├── test_protocol.py
│   └── test_animation.py
└── captures/
    └── README.md
```

Adjust the structure if the research reveals a better design.

Keep Bluetooth transport, protocol encoding, rendering, and animation logic separate.

# 4. Phase 1 — Bluetooth discovery

Our first practical milestone is discovering the device and identifying how it communicates.

Implement a command-line tool supporting:

```bash
led-matrix scan
led-matrix inspect <device>
led-matrix listen <device>
```

The discovery tool should:

1. Scan nearby BLE devices.
2. Display advertised names.
3. Display available device identifiers.
4. Display RSSI values when available.
5. Display advertised service UUIDs.
6. Connect to a selected device.
7. Enumerate GATT services.
8. Enumerate characteristics.
9. Display characteristic properties.
10. Identify writable characteristics.
11. Identify notification characteristics.
12. Save discovery results as JSON.
13. Record notifications with timestamps.

Bluetooth Classic devices may not appear in BLE scans.

If BLE discovery fails, investigate Bluetooth Classic separately.

**Discovery must be read-only by default.**

Do not send unknown commands merely to see what happens.

# 5. Phase 2 — Capture the official application protocol

We need to understand what the manufacturer's app sends to the matrix.

Develop a reproducible protocol-investigation procedure.

If possible, capture Bluetooth communication from the official Android application using Android Bluetooth HCI snoop logging.

Document:

- How to enable logging.
- How to reproduce controlled experiments.
- How to export captures.
- How to inspect packets.
- How to compare commands.
- How to identify relevant BLE writes and notifications.

Do not assume every Android device exposes usable HCI logs.

Create tools to inspect captured traffic where practical.

## Controlled experiments

Perform one change at a time.

Suggested experiments:

1. Connect to the device.
2. Disconnect from the device.
3. Turn the display off.
4. Turn the display on.
5. Display solid red.
6. Display solid green.
7. Display solid blue.
8. Display solid white.
9. Display solid black.
10. Display a single illuminated pixel.
11. Display a horizontal line.
12. Display a vertical line.
13. Change brightness.
14. Display two distinct images.
15. Play a short animation.

For each experiment, record:

- Action performed.
- Timestamp.
- Bluetooth characteristic.
- Bytes transmitted.
- Packet length.
- Device response.
- Observed display behavior.

Compare captures to infer:

- Packet headers.
- Command identifiers.
- Payload lengths.
- Frame boundaries.
- Checksums.
- Color encoding.
- Pixel ordering.
- Compression.
- Image dimensions.
- Acknowledgment behavior.

Maintain `PROTOCOL.md` as a living technical specification.

Never present guessed protocol fields as confirmed.

# 6. Phase 3 — Implement a Python device driver

Once the protocol is sufficiently understood, implement a reusable Python driver.

The intended developer experience should resemble:

```python
from led_matrix_hacker import LEDMatrix

async with LEDMatrix(device_id) as matrix:
    await matrix.set_brightness(50)
    await matrix.show_image(image)
    await matrix.clear()
```

This is an aspirational API, not evidence that these commands are supported.

Implement only operations demonstrated to work.

Desired capabilities:

- Device discovery.
- Connection management.
- Graceful disconnection.
- Automatic reconnection where appropriate.
- Image rendering.
- Brightness control if supported.
- Display clearing.
- Orientation configuration.
- RGB conversion.
- Pixel coordinate mapping.
- Protocol packet encoding.
- Acknowledgment handling.
- Transmission timeouts.
- Useful error messages.

Avoid embedding protocol-specific assumptions throughout the application.

If multiple controller variants are discovered, support separate protocol implementations.

# 7. Phase 4 — Framebuffer and image rendering

Use Pillow for image processing.

Support the actual verified panel dimensions, initially expected to be 51×16 or 16×51 depending on orientation.

Implement:

- RGB images.
- Pixel coordinate mapping.
- Rotation.
- Mirroring.
- Scaling.
- Cropping.
- Centering.
- Transparency handling.
- Optional brightness adjustment.
- Conversion to the controller's required pixel format.

Provide diagnostic images:

- Red, green, and blue test screens.
- Checkerboard.
- Numbered rows and columns.
- Single-pixel movement.
- Color gradients.
- Border outlines.

Use these to verify physical pixel ordering.

Add automated tests for image transformations.

# 8. Phase 5 — Pixel-art animations

The primary creative goal is to display original Game Boy Color-style sprite animations.

Examples:

- 8×8 pixel characters.
- 16×16 pixel characters.
- Walking animations.
- Running animations.
- Sword swings.
- Jumping animations.
- Idle animations.
- Scrolling text.
- Simple particle effects.
- Animated icons.

Use original sprite artwork or appropriately licensed assets.

Develop an animation engine supporting sequences of Pillow images.

Example intended interface:

```python
await matrix.play(
    frames=animation_frames,
    fps=12,
    loop=True,
)
```

Again, this is an intended interface, not a guaranteed hardware capability.

## Performance testing

Measure actual device performance:

- Maximum sustainable frame rate.
- Frame transmission latency.
- Effective Bluetooth throughput.
- Dropped frames.
- Corrupted frames.
- Queue buildup.
- Device acknowledgment latency.
- Connection stability.
- Host CPU utilization.

Test several target frame rates:

- 1 FPS
- 5 FPS
- 10 FPS
- 15 FPS
- 20 FPS
- 30 FPS

Only test higher rates if the device can handle them.

Distinguish between:

1. Streaming frames in real time.
2. Uploading a precomputed animation.
3. Triggering an animation stored on the device.

These have very different performance characteristics.

If continuous transmission causes lag, investigate:

- Backpressure.
- Frame dropping.
- Acknowledgment pacing.
- Packet batching.
- Connection parameters.
- Sending only changed pixels, if supported.
- Avoiding unbounded frame queues.

Prioritize stable animation over theoretical maximum throughput.

# 9. Phase 6 — Multiple LED panels

The manufacturer advertises a dual-panel pairing mode.

Investigate:

- Whether pairing happens in the mobile app or on the controllers.
- Whether each panel has its own Bluetooth identity.
- Whether Python can connect to both independently.
- Whether one panel forwards commands to another.
- Whether synchronized frame updates are possible.
- Whether panels can display different parts of one larger image.

Potential experiments:

- Two panels displaying identical images.
- Two panels displaying different images.
- One animation spanning two panels.
- Synchronized sprite movement.
- Measuring timing differences between panels.

Investigate whether more than two panels could theoretically be coordinated from Python.

Do not assume this is supported.

If it is possible, design a virtual canvas that can distribute frames across multiple physical panels.

# 10. Phase 7 — Browser-based pixel editor

After basic device control works, consider a lightweight local web interface.

Potential features:

- Pixel drawing canvas.
- Color palette.
- Import PNG images.
- Preview panel dimensions.
- Rotate and mirror images.
- Upload images to the matrix.
- Build frame-by-frame animations.
- Preview animation playback.
- Select connected devices.
- Configure brightness.

Keep this optional until the underlying protocol is stable.

# 11. Phase 8 — REST API and MCP integration

We have an existing homelab ecosystem with:

- An HP t630 thin client called Minifig.
- An Energy Monitor service.
- A LEGO scraper.
- An AI Lab.
- A home dashboard.

Eventually, the LED matrix could become a physical status display for these systems.

Potential REST endpoints:

```text
GET  /api/v1/matrix/devices
GET  /api/v1/matrix/status
POST /api/v1/matrix/text
POST /api/v1/matrix/image
POST /api/v1/matrix/animation
POST /api/v1/matrix/brightness
POST /api/v1/matrix/clear
```

Potential MCP tools:

```text
list_led_matrices()
get_led_matrix_status()
display_text(text)
display_image(image_reference)
play_animation(animation_id)
set_brightness(level)
clear_display()
```

The REST API and MCP server should reuse the same device-control layer.

Do not expose unauthenticated Bluetooth device control to the public internet.

Avoid arbitrary file-system access through image or animation inputs.

These integrations are future milestones, not initial requirements.

# 12. Phase 9 — Energy Monitor integration

We already have an Energy Monitor service capable of:

- Collecting smart-plug power readings.
- Storing historical energy data.
- Exposing REST and MCP interfaces.
- Tracking named workload intervals.
- Recording event annotations.
- Estimating workload energy consumption.
- Using configurable electricity tariffs.

Eventually, investigate whether we can measure the LED matrix's electrical consumption.

Potential experiments:

- Display off.
- Solid black.
- Solid white.
- Full red.
- Full green.
- Full blue.
- Minimum brightness.
- Maximum brightness.
- Static images.
- Animated images.
- Different animation frame rates.

Measure:

- Idle power.
- Maximum power.
- Average animation power.
- Brightness versus consumption.
- Energy used per animation session.

If we can safely power the matrix through a monitored smart plug and compatible USB power adapter, we can record its energy usage.

Do not assume the smart plug can accurately measure very small loads.

Potential future use cases:

- Display Minifig CPU activity.
- Display current household power consumption.
- Show solar production.
- Indicate grid import or export.
- Display AI Lab activity.
- Show LEGO scraping progress.
- Animate alerts when a workload finishes.

# 13. Testing and reliability

Implement automated tests for:

- Pixel coordinate mapping.
- Image orientation.
- RGB conversion.
- Protocol packet construction.
- Checksums, if applicable.
- Frame segmentation.
- Animation timing logic.
- Invalid input handling.
- Reconnection behavior where mockable.

Use recorded protocol fixtures where available.

Tests must not require physical hardware unless explicitly marked as hardware integration tests.

Do not run destructive or uncontrolled Bluetooth experiments.

Keep debug logs useful but avoid storing sensitive Bluetooth identifiers or unrelated nearby-device data unnecessarily.

# 14. Documentation

Maintain:

**README.md**
- Installation.
- Supported hardware.
- CLI usage.
- Examples.
- Known limitations.

**RESEARCH.md**
- GitHub reference projects.
- Hardware comparisons.
- Compatibility findings.
- Relevant external documentation.

**PROTOCOL.md**
- Confirmed Bluetooth protocol details.
- Packet formats.
- Characteristic UUIDs.
- Observed responses.
- Unknown fields.
- Experimental findings.

**HARDWARE_TESTS.md**
- Reproducible experiments.
- Test results.
- Device observations.
- Performance measurements.

# 15. Development priorities

Work in this order:

1. Research the existing GitHub implementations.
2. Identify the most promising compatible protocol.
3. Set up the Python project.
4. Implement BLE discovery.
5. Implement GATT inspection.
6. Identify the actual LED controller.
7. Capture or reproduce one safe, known-good command.
8. Display a static image from Python.
9. Verify pixel mapping.
10. Test animation capabilities.
11. Benchmark throughput.
12. Investigate multi-panel support.
13. Add optional REST and MCP interfaces.
14. Explore Energy Monitor integration.

Do not build everything at once.

Keep the codebase small, understandable, and maintainable.

# 16. Immediate assignment

**Start with research and first-contact tooling only.**

Specifically:

1. Inspect the five GitHub repositories listed above.
2. Identify which implementations are most likely to support our hardware.
3. Produce `RESEARCH.md` with evidence and compatibility findings.
4. Create the Python project skeleton.
5. Implement a BLE scanning CLI.
6. Implement a GATT inspection CLI.
7. Create a first-contact hardware checklist.
8. Add basic tests.
9. Document exact commands needed to run the discovery tools.

Then stop and report:

- What was discovered.
- What remains unknown.
- Which existing implementation looks most promising.
- What hardware information is needed from me.
- The safest next experiment.

**Do not implement a speculative full driver before we have verified hardware observations.**

Our first milestone is simple:

**Make one pixel change color from Python without using the manufacturer's application.**

After that, we'll find out whether we can make a tiny pixel-art swordsman run across the display.

Let's hack this thing.