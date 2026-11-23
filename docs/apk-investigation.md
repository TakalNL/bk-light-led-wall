# iPixel Color APK investigation

This is a dated investigation report. The readable 3.7.9 follow-up enabled
further analysis after the initial protected-build pass; use the current
[findings](investigation-summary.md) and [capability map](panel-capabilities.md)
for consolidated conclusions. Downloaded APKs and private extraction scripts
are not included in the public repository.

Date: 2026-11-19. Static inspection of the Android APK downloaded by the owner
from the local-server option at `https://api.e-toys.cn/page/app/137`.

## Result

The readable APK material does not establish native dual-panel pairing or
synchronized playback. Its application implementation is protected, so the
absence of a visible dual-panel label does not establish absence of support.
No APK code was installed or executed, and no panel commands were sent.

The owner reports packaging text **Double fun mode / Mode double plaisir** with
two LED displays separated by a plus sign. Treat that as an advertised feature
whose behavior is still unverified. The owner also observed that enabling one
panel in the iPhone app disconnects the other. That establishes the behavior of
the normal device picker, not every possible firmware mode.

## Artifact identity

| Field | Observed value |
| --- | --- |
| Filename | `b9e398e2209df488ea987443f344e314.apk` |
| Size | 170,919,337 bytes |
| Package | `com.wifiled.ipixels` |
| Label | iPixel Color |
| Version | 3.8.0, version code 382 |
| Minimum / target Android API | 26 / 36 |
| APK SHA-256 | `41191c5f7f8e0b3b5983ffdcd93f16a9357d9cb348fb74a15dff25a67fd0162f` |
| Signing-certificate SHA-256 | `73be4bf2cbce09ca31511eb9b681f658a9f7403ed269c7f0adf6e96e1c8b420e` |

The certificate fingerprint matches the one published for Heaton's
[3.7.9 distribution](https://www.apkmirror.com/apk/heaton/ipixel-color/ipixel-color-3-7-9-release/ipixel-color-3-7-9-android-apk-download/).
This is a certificate comparison, not an independent full APK signature validation
or a demonstration that Android and iPhone implementations behave identically.

## Readable interface and assets

| Evidence | Finding and limit |
| --- | --- |
| `dialog_connect`, `item_connect` layouts | Device-connection list, refresh, device name, edit and state icons. The layouts do not reveal the selection handler or prove its connection policy. |
| `ChannelListActivity`, `activity_channel`, `title_channel_list` | The visible title is Program List. Controls select, delete and send programs. These are not evidence of radio channels or groups of panels. |
| `SelectTemplateActivity`, `EditTemplateActivity`, `SubzoneListActivity` | Templates contain combinations of text and image regions, including a `template_3264` container and per-region views. This suggests single-panel mixed-content layouts; the protected handlers could not be traced. |
| `fragment_settings_main` | Controls for language, clearing data, orientation, brightness, device information and password; also Help Center and User Manual entries. |
| Manifest and string resources | Game screens/labels for Snake, PingPong and Tetris; clock, countdown, stopwatch, alarms, scheduling, riding, image/text and projection screens. Presence in the generic app does not establish execution on this panel model or whether computation occurs on the phone. |
| `homeConfig.json`, `sucai_define.json` | Product-ID and size-dependent branding/content configuration exists. App features and content can vary by product family. These files did not identify a dual-panel mode. |

Resolved resources contain no explicit double-fun, dual-screen, multi-screen,
pairing, mirroring or splicing label found by the targeted English/Chinese
searches. The extraction contained 24,720 resolved string values across locales,
including default, English, French, Dutch and Chinese values. A generic geometric
resource named `circle_group` is unrelated evidence and was excluded.

## Why command analysis is incomplete

The application entry point is `com.sagittarius.v6.StubApplication`.
`libbaiduprotect.so`, `assets/baiduprotect*.jar` and small companion DEX containers
are present. The four ordinary root DEX string tables expose the loader and
dependencies, but no `com/wifiled/...` application class descriptors or ordinary
FA02/FA03 display-control strings.

The five `baiduprotect*.i.dex` files are ZIP containers holding DEX placeholders.
Although their expanded lengths range from 112,184 to 3,944,012 bytes, each has
only 50 or 51 nonzero bytes and no string/type/method/class tables. They do not
contain the missing implementation in directly disassemblable form.

Consequently this inspection cannot establish Android connection exclusivity,
find hidden pairing commands, or map its packet builders. No conclusion about
those behaviors should be drawn from the manifest or resource names alone.
A public 3.7.9 reference download was attempted but returned HTTP 403; it was
not available for independent command-code inspection.

## AE00: a narrower hypothesis

Our earlier hardware inspection recorded service `AE00`, characteristic `AE01`
with write-without-response, and characteristic `AE02` with notifications. See
the [protocol ledger](archive/PROTOCOL.md).

This APK includes `libjl_ota_auth.so` for both ARM architectures, the activity
`com.tiro.jlotalibrary.JLDialogActivity`, and app-specific OTA activities and
firmware labels. JieLi's
[official OTA SDK documentation](https://doc.zh-jieli.com/Apps/iOS/ota/zh-cn/master/Other/jl_ota_sdk_qa.html)
specifies AE00 / AE01 / AE02 as its default service/write/notification interface.

**Inference:** the additional service is consistent with a JieLi OTA/control
path. It is not evidence of a second display link. The exact chipset, protocol
features and service purpose remain unconfirmed on our hardware. No firmware
update, authentication sequence or experimental AE00 command was attempted.

Follow-up on 2026-11-19: [AE00 identification](ae00-identification.md) completed
SDK authentication and read-only identity queries on both panels, confirming
JieLi RCSP behavior. The exact chip model remains unknown. The statement above
describes the APK-only inspection, before the hardware follow-up.

## Next evidence that would resolve the question

1. Check the official app's Help Center / User Manual for the advertised mode.
   The Android APK contains these entries; their availability in the owner's
   iPhone version needs observation.
2. Obtain the exact model's instructions or a manufacturer explanation of the
   two-panel icon. The retailer's current page did not explain the mode.
3. Capture the official app performing the mode, if accessible. Record both
   device connections and compare writes with a single-panel baseline. Separate
   app streaming, independent GIF uploads and explicit coordination commands.
4. Test frame-number alignment over time and after phone disconnection.
   Continuing playback alone proves autonomy, not inter-panel communication.
5. An unprotected same-signer build or a runtime trace of the protected build
   could expose additional command constructors. That is further work, not a
   capability established by this static inspection.

## Reproduction and retained files

The APK, decoded material and inspection scripts remain in ignored
`.research/ipixel-apk/`. Androguard 4.1.4 was installed in the separate ignored
`.tools/apk-inspect` environment. The game environment was not modified.

Retained material includes `metadata.json`, `AndroidManifest.xml`,
`archive-inventory.json`, `resources-public.xml`, `resource-strings.json`,
`feature-label-evidence.json`, `other-feature-evidence.json`, the configuration
JSON files, four DEX string dumps, 1,166 decoded binary XML files and 438 layouts
mapped back to their original resource names. Decompiled app resources and the
third-party APK are not included in Git.

Decoded XML is stored in `xml-by-path/`, with `xml-index.json` mapping exact APK
paths to case-safe filenames. Named layouts are stored in `named-layouts/`.

The metadata, resource, string and XML extraction can be repeated with:

```powershell
.\.tools\apk-inspect\Scripts\python.exe -X utf8 .research/ipixel-apk/inspect_apk.py
```

Later reference-build follow-up: the supplied 3.7.9 XAPK has the same extracted
signing-certificate fingerprint and readable application classes without the
Baidu protection files. The [firmware metadata investigation](firmware-metadata.md)
records the recovered model-specific update lookup and server responses. The
protection limitation in this report describes the original 3.8.0 local-server
APK, not that reference build.

The subsequent [capability survey](panel-capabilities.md) found concrete
two-output eye-upload and synchronization paths in the readable build, together
with model exclusions and a newer active picker. The earlier absence of readable
dual-panel implementation in the protected APK must not be treated as evidence
that no such application code exists.
