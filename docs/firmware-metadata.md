# Firmware metadata lookup

This report preserves dated requests and earlier investigation stages. Start
with [findings](investigation-summary.md) for current conclusions. Reproduction
commands referencing `.research/` require private artifacts/scripts that are
not shipped with the application or public source.

Date: 2026-11-19. Follow-up to [AE00 identification](ae00-identification.md).

## Result after inspecting the reference build

The owner supplied `ipixel-color-3-7-9.xapk`. Its base APK identifies itself as
`com.wifiled.ipixels` version 3.7.9, code 381. The application entry point is
`com.wifiled.ipixels.App`; the earlier Baidu protection files are absent and
the application classes are readable. Its extracted signing-certificate SHA-256
matches the original 3.8.0 APK:
`73be4bf2cbce09ca31511eb9b681f658a9f7403ed269c7f0adf6e96e1c8b420e`.
This is a certificate comparison, not independent full APK signature validation.

Artifact hashes:

| Artifact | SHA-256 |
| --- | --- |
| XAPK | `7b40513cda0b495c2d50c3692dd94fa89c7108016c9be0ba89ee7dc4bc7534fb` |
| Base APK | `a9d350c5bae74723b2f8c7d634debffb5267203632ddcacf9d2cf38eeb29fbf4` |

**The actual panel-firmware lookup was recovered and queried.** Its endpoint is:

```text
POST https://manage.heaton.com.cn/api/rm/getFirmwareInfo
```

All four bounded lookups returned HTTP 200 and the same decoded application
response:

```json
{"status":1,"msg":"请求失败,查无数据","data":{"no_data":true}}
```

The message means request failed / no matching data. No firmware URL, version
record, release notes, or explicit `need_update: false` result was returned.
This establishes no matching data for the tested requests at the observation
time. It does not establish that firmware 14.02 is the latest, that no firmware
exists anywhere, or that the hardware lacks additional functions.
These are requests reconstructed from Android 3.7.9, not captured from the
owner's iPhone. Other app versions or platforms may use different lookup paths.

| Request | Reported MCU code | Reported app version | Result |
| --- | --- | --- | --- |
| Signed AES, as used by this model's app path | 1402 | 3.7.9 | no_data |
| Signed AES, earlier version in the same family | 1400 | 3.7.9 | no_data |
| Signed AES, newer known phone-app version | 1402 | 3.8.0 | no_data |
| Legacy form method also declared in the APK | 1402 | 3.7.9 | no_data |

The earlier-version value was supplied only in the HTTP lookup. Nothing was
downgraded. Neither APK was installed or executed, and neither panel was
connected to or updated during this metadata investigation.

## How the exact model request was derived

The reference APK's `BleManager$bleScanCallback$1.onLeScan` parses the vendor
manufacturer-data marker `TR 00 72`, followed by two CID bytes, PID, orientation
and device type. Both panels' retained advertising observations have company
key 21076 (`0x5254`, the little-endian representation of `TR`) and payload
`00 72 00 07 04 00 83`.

Reproducing the app's decimal concatenation and padding gives customer code
`0007`, product code `04`, and device type `0x83`. The firmware code concatenates
MCU major 14 and zero-padded minor 02 into integer `1402`.
`JLOTA.checkOTA` selects the `1400 <= version < 1500` branch, which builds
`R2305R021_14_` plus the customer and product strings. The resulting request is:

```text
appid=137
project_no=R2305R021_14_000704
version=1402
android_version=3.7.9
```

`android_version` is the phone application's version name in this code, not
the Android operating-system version. No panel MAC or user account is included
in this lookup. The product/project code is not a decoded chip-part number.

The exact endpoint and parameter names come from the Retrofit annotations on
`ApiService.firmwareInfo` and `ApiService.newFirmwareInfo`; the base URL comes
from `NetWorkManager.getRequest` / `getStrRequest`.

The model's `JLOTA.checkOTA` path uses the latter method: query parameters
`sign`, `timestamp`, `random`, with a `text/plain` Base64 AES-256-CBC body and
PKCS7 padding. `CryptographicParsingToolKt` sorts and URL-encodes parameters,
computes the lowercase MD5 signature using an app-level shared constant, and
uses the same constant as its AES key with the fixed ASCII-zero IV. Responses
are decoded with that same AES scheme. These operations were reproduced from
the local disassembly; no authentication bypass or guessing of project IDs was
needed. The legacy method uses four ordinary URL-encoded form fields.

The declared `OTAInformation` response model has `desc_cn`, `desc_en`,
`need_update`, `version_no`, `file_path`, and `force`. None of those release
fields was supplied in these replies.

## Current evidence and reproduction

Ignored `.research/firmware-metadata/reference-3.7.9/` contains `base.apk`,
`identity.json`, DEX string dumps, selected class disassembly, interface
annotations, and the advertising-selector caller disassembly.
`dump_reference.py` and `find_identity_callers.py` reproduce the selected static
exports using the isolated Androguard environment.

The standalone `query_firmware.py` reads the retained advertising capture to
derive both panels' matching selector, reproduces the HTTP protocol and saves
the request, raw response and decoded JSON. It contains no BLE or firmware
transfer code. Run from the repository root with a fresh output filename:

```powershell
.\.tools\apk-inspect\Scripts\python.exe -X utf8 .research/firmware-metadata/query_firmware.py --output .research/firmware-metadata/NEW_LOOKUP.json
```

The four responses are retained in `firmware-1402-signed.json`,
`firmware-1400-signed.json`, `firmware-1402-app380-signed.json`, and
`firmware-1402-legacy.json`. All were observed on 2026-11-19. No firmware image
was returned or downloaded.

The readable build also enabled a broader [capability survey](panel-capabilities.md),
including two-output coordination code that was unavailable in the protected
APK. Firmware lookup results do not limit what can be learned from that code.

## First pass, before the reference build was supplied

The sections below retain the earlier investigation state and explain why the
second download was needed. Their missing-input statements describe that first
pass; they are superseded by the successful request recovery above.

No panel-firmware lookup request or matching firmware download was recovered
in the initial pass. This was a request-recovery limitation, not a server response
saying that the owner's panels have no update.

The known vendor **app-update** endpoint was queried successfully and returns
the same iPixel Color 3.8.0 Android APK already inspected. It must not be
confused with panel-firmware metadata.

No panel connection or application command was needed for this investigation.
The existing ring-demo controller was left running.

## Confirmed vendor response

The public [app download page](https://api.e-toys.cn/page/app/137) returns its
local-download URL and Google Play link. Its local URL points to the existing
APK under `resources/upload/files/20261028/`.

A single metadata request was made to the known app-update endpoint:

```text
POST https://api.e-toys.cn/api/app/lastUpdate
Content-Type: application/x-www-form-urlencoded

app_id=137&platform=Android
```

The HTTP 200 JSON response has status 0 and reports:

| Field | Value |
| --- | --- |
| app_version | 3.8.0 |
| app_version_number | 382 |
| update_type | alone |
| app_url basename | b9e398e2209df488ea987443f344e314.apk |
| app_modified | 2026-10-28 12:27:42, server-provided timezone unspecified |
| English app_update | Optimize user experience |

These are phone-app fields. The response contains no panel model selector,
panel firmware image, RCSP version, or panel release notes. The returned APK
URL was not downloaded again. A successful metadata request does not start an
update or install the APK.

## Static APK checks

The retained 3.8.0 APK was searched again across all four ordinary DEX string
tables, resolved default/English/Chinese resources, archive paths, and readable
HTTP URL bytes in assets and native libraries. No panel-firmware request URL
or identifiable firmware image was found. The relevant application code remains
inside the protected payload described in the [APK report](apk-investigation.md).

The update-dialog layout contains old/new version fields, release notes,
cancel and confirm controls. App strings distinguish MCU, Bluetooth and Wi-Fi
firmware across its supported product families. This suggests model/component
selection matters, but neither the resource layout nor the generic labels
establish a request schema or Wi-Fi support on the owner's panels.

The published content manifest `http://app.heaton.cn/sucai_define.json` was
retrieved successfully. It is a material/category configuration, not an
identified firmware catalog. Its HTTPS URL failed local certificate validation;
that validation was not disabled.

## Primary research and reference-build lead

An earlier owner of an Action/B.K. Light panel
[reported an OTA API response with no data](https://github.com/lucagoc/pypixelcolor/issues/13#issuecomment-3407117343),
including after changing the reported version. The comment does not provide
the endpoint or exact request. It concerns earlier hardware and does not
establish current availability for the owner's 2026 panels.

The upstream maintainer's [firmware research repository](https://github.com/lucagoc/iPixel-CFW)
documents AC6951C hardware on the researched board, but does not supply the
missing update request. That chip identification remains a comparison lead,
not a hardware identification for these specific panels.

A public [3.7.9 reference download page](https://ipixel-color.en.uptodown.com/android/download/1228602000)
was retrieved. It identifies package `com.wifiled.ipixels` and describes the
build as matching the published Google Play version. This makes it a candidate
for readable application code, not proof that it is unprotected or authentic.
The actual file has not been obtained or verified.

The site's public download script requires a solved interactive Turnstile
challenge before requesting a file URL. No file-URL request or challenge bypass
was attempted. APKMirror and APKPure automated download attempts returned 403.

## Next input

The next useful input is either:

1. A reference Play-distribution APK/XAPK/APKM, whose base APK can be inspected
   for protection, package/version, signing certificate and update request code.
   The candidate page above is a normal browser download route. A match is not
   assumed before inspecting the file.
2. A network trace of the official app's firmware availability check, including
   the endpoint, component/model/version parameters and reply. Firmware transfer
   is not needed to investigate the lookup metadata.

Displayed device-info firmware versions can help interpret selectors once the
request is recovered. They cannot by themselves identify the lookup URL.

The owner subsequently reported the iPhone device-information screen as:

| Field | Displayed value |
| --- | --- |
| Device Type | 64x16 |
| MCU firmware version | 14.02 |
| Bluetooth firmware version | 7.04 |

These match the earlier iPixel version reply's MCU bytes `[14, 2]` and secondary
bytes `[7, 4]`. The app observation identifies that second pair as Bluetooth
firmware and establishes its displayed formatting. The owner did not specify
which panel was viewed or report an update-availability status. These are
installed versions, not evidence of the latest available versions. They also
do not repair the separate AE00 target-info reply's undersized version field.

## Retained evidence

Ignored `.research/firmware-metadata/` contains the vendor page, full app-update
response, request/status summary, static candidate lists, native/asset URL scan,
reference download pages and decoded download script, and primary GitHub
research responses. `http-*.json` files distinguish failed requests from actual
server data. No firmware image was obtained, installed or sent to a panel.
