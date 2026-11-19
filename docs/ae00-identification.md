# AE00 identification on both panels

Date: 2026-11-19. Hardware experiment following the
[APK investigation](apk-investigation.md). Both owner-supplied panels were
queried separately; the ring demo was closed gracefully first and restarted
after the probes.

## Result

**Both panels implement an authenticated JieLi RCSP interface on AE00.**
The manufacturer's standalone authentication implementation completed, and
GET_TARGET_INFO returned a successful, structurally valid response containing
each panel's actual BLE address. This advances AE00 from a UUID-based hypothesis
to observed protocol behavior.

It does not identify the exact chip model or establish extra display functions.
The returned identity fields are sparse and partly incompatible with the SDK's
expected field lengths. The feature-map request succeeded with no bitmap.

## Procedure and source

Reference: manufacturer's
[WeChat-Mini-Program-OTA SDK](https://github.com/Jieli-Tech/WeChat-Mini-Program-OTA),
commit `6db11194ba53e9f0caf08321bbbd683a7d904d60`, library
[`lib/cjs/jl_rcsp_2.2.0_ota.js`](https://github.com/Jieli-Tech/WeChat-Mini-Program-OTA/blob/6db11194ba53e9f0caf08321bbbd683a7d904d60/lib/cjs/jl_rcsp_2.2.0_ota.js).
The SDK supplies the Auth implementation, command serializers and response
parser. Its matching declarations describe target-info fields. Manufacturer
[integration documentation](https://doc.zh-jieli.com/Apps/Android/ota/zh-cn/master/development/development_desc.html)
separates initialization/device information from starting a firmware update.

1. Connect using AE00; verify AE01 write-without-response and AE02 notify.
2. Subscribe to AE02. An unauthenticated target-info query on the upper panel
   received no notifications in the five-second observation window.
3. In a fresh connection, run standalone SDK Auth with its optional opcode-6
   reset disabled. Three host authentication writes completed the exchange:
   a 17-byte challenge, `02 70 61 73 73`, and a 17-byte challenge response.
   The panel returned `02 70 61 73 73` and the SDK reported success.
4. Send GET_TARGET_INFO, opcode 3, sequence 0, mask `ffffffff`, platform 0.
5. On subsequent top/bottom comparison runs, also send GET_TARGET_FEATURE_MAP,
   opcode 2, sequence 1, with no additional parameters.
6. Stop notifications and disconnect. No automatic retries.

Exact requests, cross-checked against SDK serialization:

```text
Target info:  fe dc ba c0 03 00 06 00 ff ff ff ff 00 ef
Feature map:  fe dc ba c0 02 00 01 01 ef
```

Only those two RCSP opcodes and the bounded authentication messages were sent
by the identification probe. No iPixel clock/display initialization, firmware
transfer, update-mode entry, reboot, or reset command was sent by the probe.
Restoring the existing wall controller afterward uses its normal initialization.

## Observed fields

Each target-info response is 70 bytes, status 0, sequence 0. Both contain exactly
the same TLV values except types 2 and 17, which contain addresses.

| Field | Upper panel | Lower panel |
| --- | --- | --- |
| BLE address, TLV 17 | `95:53:D1:21:30:2F` | `DE:73:BB:98:C5:FD` |
| EDR address field, TLV 2 | `95:53:D1:8E:71:38` | `DE:73:BB:31:16:A3` |
| RCSP protocol, TLV 0 | 2.0 | 2.0 |
| SDK type, TLV 6 | 1 | 1 |
| Update flags, TLV 8 | `01 00` | `01 00` |
| Protocol send / receive MTU, TLV 13 | 128 / 540 | 128 / 540 |
| Negotiated BLE ATT MTU | 517 | 517 |
| Generic function mask, TLV 4 | `0000004e`, current function 0 | Same |
| Firmware-version field, TLV 5 | One byte `00` | Same |
| Vendor/product/customer field, TLV 10 | One byte `00` | Same |
| Device name / project code | Not returned | Not returned |

Interpretation limits:

- The SDK interprets update flags `01 00` as dual-bank updates supported and
  bootloader download not required. These are device-reported flags; no update
  was attempted. **Dual-bank describes firmware storage, not two displays.**
- The firmware field is shorter than the two bytes the SDK needs; the product
  identifiers are shorter than its four/six-byte layouts. SDK defaults such as
  version 0 or VID/PID/UID 0 must not be presented as decoded identity values.
- No chip-family name or project code was returned. UUIDs and SDK support alone
  do not distinguish a specific AC69xx/AC70xx chip.
- The generic function mask maps to audio-oriented modes in the stock SDK. It
  does not demonstrate that this LED product implements those functions.
- An EDR address and BLE-only flag 0 do not establish a usable Classic Bluetooth
  service. No Classic connection was attempted.
- Protocol MTU fields and negotiated BLE ATT MTU are different quantities.

Both feature-map replies are exactly:

```text
fe dc ba 00 02 00 02 00 01 ef
```

This is status 0, sequence 1, **zero data bytes**. It provides no list of
supported commands. It is not evidence that all commands are supported, or that
no other commands exist.

An advertisement-only scan found both panels using manufacturer-data key 21076
with payload `00720007040083`, and no advertised service UUIDs or service data.
That identical payload did not add a verified chip identifier.

## Evidence and reproduction

Private captures remain ignored by Git:

- `captures/ae00-top-unauth-20261119.jsonl`
- `captures/ae00-top-auth-20261119.jsonl`
- `captures/ae00-top-features-20261119.jsonl`
- `captures/ae00-bottom-features-20261119.jsonl`
- `captures/ae00-advertisements-20261119.json`

Research code is retained in ignored `.research/ae00_probe.py`,
`.research/jieli_auth_bridge.cjs`, and `.research/ae00_decode.py`. The SDK clone
is `.research/jieli-ota-sdk/`; no SDK package was installed in the game environment.
The bridge uses standalone Auth, not an OTA manager or RCSP initialization factory.
It disables the SDK's optional reset command. The Python transport validates
authentication packet shapes and limits the exchange to four host writes.

```powershell
.\.venv\Scripts\python.exe -X utf8 .research/ae00_probe.py DEVICE_ADDRESS --authenticate --feature-map --output captures/NEW_CAPTURE.jsonl
.\.venv\Scripts\python.exe -X utf8 .research/ae00_decode.py
```

The decoder validates frame lengths, trailers, status, sequence, TLV boundaries,
address correspondence and equality outside address fields for the retained
comparison captures. `.research/ae00-results.json` preserves decoded results
alongside all raw TLVs. The upper response was also parsed offline by the
manufacturer's own ResponseTargetInfo implementation with matching field values.

The restored ring-demo controller recorded both panels connected and resumed
acknowledged combined-frame output. Physical appearance was not re-confirmed
by the owner during this experiment.

## Remaining leads

AE00 now gives us a working authenticated protocol connection. The identity
query did not expose model/firmware identifiers or synchronization controls.
The next stronger identification sources are the official app's traffic or
update metadata, a matching firmware image for offline inspection, and chip
markings on the PCB. Do not infer that an audio/TWS function in the generic
JieLi SDK is implemented by these panels.

The [firmware metadata follow-up](firmware-metadata.md) records the subsequent
request-recovery work and distinguishes phone-app updates from panel firmware.
