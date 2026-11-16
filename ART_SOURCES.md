# External art inspected for panel tests

Retrieved 2026-11-14. Downloaded artwork and adapted GIFs remain in private,
ignored `captures/`; no third-party artwork is bundled in the source package.

## Native 64×16 eyes

- Source gallery: [educoay, animaciones 64x16](https://educoay.com/animaciones64x16/).
- Selected file: [b.gif](https://educoay.com/wp-content/uploads/2025/05/b.gif).
- Downloaded file: 64×16, 44 frames, 22,176 bytes.
- SHA-256: `532f9901da5ac6a499c1d99d503790853127a461d6eaad6e98309bf994afe9e7`.
- Author/reuse license: not stated on the inspected gallery; do not infer CC0
  or include downloaded/adapted art in a publicly distributed asset package.
- Adaptation for private hardware tests: native dimensions preserved, flattened
  on black, quantized to 32 colors per frame. A centre strip shows encoded fps
  above a continuous three-digit frame index. This slightly covers the centre
  gap; it does not resize the eyes.

`a.gif`, `ccc.gif` and `ddd.gif` from the same gallery were also inspected.
Their dimensions were all 64×16 with 32, 45 and 46 frames respectively.
Source files are under `captures/art-source-20261114/`; the selected asset and
prepared variants are identified in `captures/eyes-bench-20261114/manifest.json`.

## CC0 lava alternative

[16x16 and animated lava tile (45 frames)](https://opengameart.org/content/16x16-and-animated-lava-tile-45-frames),
by davesch, lists CC0 and an intended 10 fps. The downloaded
`lava_spr_strip45.png` is a 720×16 horizontal strip of 45 native 16×16 frames.
It was initially inspected as a potential full-height tiled alternative.
The source comments report imperfect tiling, so seamless 64×16 tiling is not assumed.

Later selected as an ambient display loop at the owner's request. Each source
frame is tiled four times across 64×16, with alternate tiles mirrored to join
matching boundary pixels; the artwork remains at native height. No test labels
or frame counters are added. The resulting private GIF is 49,041 bytes, 45 frames
at encoded 10 fps, with an infinite 4.5-second loop. Source SHA-256:
`89afd60f69cfff1dd577d24a1c2d7381027c9d8c1357784b9c0a81a4e4fb22ae`.

Upload used the actual pinned library, 500-byte acknowledged chunks and slot 0.
It completed with the strict GIF completion reply in 4.554 seconds; the host
then disconnected. The owner reported that the lava looked poor and requested a
video-game animation instead. Source, prepared
GIF, manifest and logs are under private `captures/ambient-lava-20261114-230903/`
(source strip remains in `captures/art-source-20261114/`). This temporary display
does not replace the saved startup GIF. No external artwork was added to the
distributed source assets.

## Mario running across the panel

Selected following the owner's request for Mario or a similar video-game loop.
Source: [Small Mario Walk SMB.gif, Super Mario Wiki](https://www.mariowiki.com/File:Small_Mario_Walk_SMB.gif),
an original Super Mario Bros. sprite animation (16×16, three 100-ms poses).
Downloaded source SHA-256:
`5c0e7d6ab585f46a0cdc04894014dfb419b5c75a034979722b28e81d94235130`.

The sprite keeps its native pixels, colours and pose durations. Our composition
moves it one pixel every 50 ms across a black 64×16 canvas, then repeats after
4.2 seconds. The GIF contains 79 encoded frames and is 11,337 bytes; the encoder
merges consecutive identical blank frames. Decoded images and timings were checked
against the entire prepared timeline. There are no counters, resized pixels or
additional artwork. The acknowledged slot-0 upload completed in 0.804 seconds,
returning `0500030003`; the host disconnected. The owner subsequently described
the result as neat, then requested a more colourful animation.

Source, prepared GIF, manifest and capture are private in
`captures/ambient-mario-20261114-231109/`. The source page labels this a copyrighted
game sprite; no redistribution license is inferred. It is not bundled in the
application or its public assets. The persistent startup GIF remains unchanged.

## Rainbow vortex

For the owner's request to find an existing colourful GIF, selected
[Trippy Tunnel, uploaded by oilbuds on Tenor](https://tenor.com/view/trippy-tunnel-rainbow-tunnel-rainbow-color-gif-16027663).
The downloaded source is 640×360, 121 frames, 12,962,851 bytes, with SHA-256
`dbf791465e9a9a05c1ef84ef9c95ee0a53d1a3ff5d58c698c7078c9be08d606a`.

Adaptation resizes the whole frame to 64×16 using Lanczos, increases saturation
by 1.25× and brightness by 1.15×, and uses a shared 256-colour palette without
dithering. Original timing is retained with an infinite 5.04-second loop. Three
identical neighbouring frames are merged, resulting in 118 encoded frames and
223,114 bytes. Decoded pixels and frame durations match the prepared timeline.
No labels or counters are added. Prepared files, source, manifest and upload log
are private in `captures/ambient-colour-search-20261114-231839/`. No redistribution
licence is inferred, and no downloaded art is bundled in the public application.

The acknowledged slot-0 upload completed in 21.904 seconds, returning
`0500030003`. The host disconnected for autonomous playback. The saved startup
GIF is unchanged. The owner reported that the vortex was too busy and lacked a
recognisable subject, and requested an animation that depicts something.

## Nyan Cat and rainbow

Selected an existing pixel-art character animation in response to that feedback.
Source: Adafruit's [Raspberry Pi matrix GIF example](https://learn.adafruit.com/rgb-matrix-panels-with-raspberry-pi-5/animated-gif),
with [nyan.gif from its example assets](https://github.com/adafruit/Adafruit_Blinka_Raspberry_Pi5_Piomatter/blob/main/examples/nyan.gif).
The downloaded GIF is 64×25, twelve 70-ms frames. Source SHA-256:
`57327203ad32f31d631e7e0022147423a956f989e29c989f55b5ce853e0c683f`.

Adaptation uses nearest-neighbour sampling to 44×16, removes one empty left
border column, and extends the existing rainbow 21 pixels to fill the width.
This sampling retains both eye pixels in every pose; an earlier local preview
dropped an eye and was revised before hardware upload. Colours and pose timing
are unchanged. The final GIF is 4,194 bytes, twelve frames and an infinite
840-ms loop, without labels or counters. Decoded frames match the prepared
pixels. Private sources, manifest, preview and logs are in
`captures/ambient-nyan-20261114-232151/`. No artwork redistribution licence is
inferred and the downloaded animation is not bundled with the public application.
The acknowledged slot-0 upload completed in 0.357 seconds with the strict GIF
completion reply; the host disconnected. Physical playback awaits feedback.
