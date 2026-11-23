# What we found

These findings concern two **B.K. Light / Action article 3226274** panels,
reporting **64x16, type `0x83`, MCU 14.02 / Bluetooth 7.04**. Hardware tests used
one Windows host. They are observations of these units, not guarantees for
other batches or every device supported by iPixel Color.

## The useful results

| Question | Observed answer | Practical consequence |
| --- | --- | --- |
| Can I control it without the vendor app? | Yes, through Python and the existing pypixelcolor protocol/library. | Our Windows web controller adds discovery, setup, media and phone access. |
| Can two panels act as one screen? | Yes, with separate BLE links and a host-rendered shared canvas. | Position, mounting rotation and bezel compensation work; only two physical panels have been tested. |
| Can it play without the host? | Native uploaded GIFs and a native clock continued after Bluetooth disconnected. | Autonomous playback exists, but the web controller currently streams its content and must stay running. |
| Does saved content survive power loss? | Two original GIFs survived USB power loss and automatically played as a playlist. | Persistent native content is possible; total capacity and arbitrary slot behavior are not established. |
| Can saved GIFs be selected without uploading again? | A/B/A switching in ordinary slots 1/2 worked with seven-byte commands, including recall after Bluetooth reconnect. | It worked from native GIF playback; the same selector did not replace a temporary HOLD PNG. Display mode matters. |
| Can two native GIFs start together? | Concurrent short restart headers brought deliberately offset loops close together, with a small remaining visible lead. | Useful approximate coordination; no deferred upload/start or atomic synchronized swap was demonstrated. |
| What improves streaming synchronization? | Delaying the faster upload using recent timings improved the observed GO-number transitions, including the owner's review of 240-fps video. | An optional software technique, not measured exact LED synchronization or a throughput increase. |
| What does Double fun mode mean? | The packaging showed two panels and a plus sign. The tested iPhone picker switched between devices; the inspected Android model path excluded this product from dual-eye connections. | We did not establish a native paired-wall mode. That does not prove no alternative mode exists. |

## Streaming speed and native GIF speed are different questions

The wall worker targets at most 10 combined image updates/s, sends panels
concurrently and waits for all completion replies before selecting the latest
canvas. It does not build a queue of old frames. A slow panel therefore limits
the combined rate even when the other panel finishes earlier.

Observed speed has varied. An earlier two-panel chunk-size comparison completed
4.6-5.2 canvases/s. Recent individual sessions measured median upload/reply times
near 224 ms for the top panel and 109 ms for the bottom, roughly 4-5 versus
9-10 uploads/s during changing content. Both separately reported a 22.5-ms
Windows connection interval and zero peripheral latency, so that interval alone
does not explain the difference. Connection scheduling, image processing and
reply timing remain candidates; an identical-workload comparison is still needed.
The latest per-panel UI change did not introduce this observed asymmetry.

The older single-panel desktop Windows throughput profile previously reached
about 12 acknowledged uploads/s on its tested workload. The web/wall worker
does not currently apply that optional profile. Those earlier trials are not a
promise of 12 fps for either current panel, a wall, or every image.

Native GIF playback is autonomous and is not limited by the wall streamer's
10-fps target. Relative counter tests found no observed speed advantage for
20-ms delays over 30-ms delays on the tested path, suggesting a delay floor
near 30 ms. **An exact 33-fps physical rate was not measured.**
All upload timings measure completion replies, not LED refresh or input latency.

## Other verified behavior

- A native clock kept time, with changing minutes, after Bluetooth disconnected.
- A 4,096-frame, 1,915,364-byte GIF played successfully. This is a tested file,
  not a measured storage ceiling.
- Brightness changes and display off/on worked during native animation.
- Hardware orientation 0 restored upright; values 1, 2 and 3 each appeared
  upside down in the tested sequences. They are not four verified rotations.
- Orientation and apparent brightness survived a USB power cycle. Software
  display-off did not: the intro and saved playlist returned after power loss.
- A completion reply did not guarantee correct visible output: indexed PNGs
  appeared black and the tested JPEG path showed the boot image. RGB PNGs are
  the verified live-image path.

## What remains unknown

The exact controller chip, maximum storage/panel count, native paired-wall
support and several generic-app commands remain unresolved. Tested scoreboard,
timer, mirror, movement and mixed-region sequences did not establish correct
visible behavior on this model. Those negative tests are not proof that every
parameter or firmware lacks the feature.

Authenticated AE00 queries identified JieLi RCSP 2.0, but returned no useful
chip identifier or populated feature bitmap. Reconstructed firmware-metadata
requests returned no matching data; no firmware image was obtained or flashed.

The tested Ubuntu/BlueZ configuration discovered the panels but had inconsistent
service/attribute discovery, also seen with an independent tool. Playback on
Linux is unvalidated; this is not a conclusion about all Linux adapters.

## Software, evidence and credit

The application uses [pypixelcolor](https://github.com/lucagoc/pypixelcolor) for
command construction and transport. Our contribution is the application and
multi-panel coordination, original renderers, Windows packaging and this
exact-model investigation. The service is a preview, not a finished unattended
home-automation integration or a replacement firmware.

- [Compatibility](compatibility.md): tested hardware, supported paths and limits.
- [Validation](validation.md): dated runs, measurements and owner observations.
- [Capability map](panel-capabilities.md): command families and evidence levels.
- [APK](apk-investigation.md), [AE00](ae00-identification.md),
  [firmware metadata](firmware-metadata.md): deeper investigation.
- [Research archive](archive/README.md): historical experiment reports.
- [Investigation checkpoints](archive/INVESTIGATION_CHECKPOINTS.md): preserved
  chronological notes, including conclusions later superseded by follow-ups.

Public reports retain packet descriptions, fixture hashes and private capture
references. Raw captures, owner-specific addresses, APKs and downloaded vendor
artwork are not included. Some historical reproduction commands depend on
private research scripts and are not runnable from a public clone; current
supported tools are listed in [development](development.md#diagnostic-toolkit).
