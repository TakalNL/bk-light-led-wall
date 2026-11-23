# Remaining work

The target is a complete package for owners of the Action B.K. Light panel,
article 3226274: download, start, discover panels and use a local web interface
without editing the upstream library. The browser is the primary interface;
the older desktop applications remain available.

## Current checkpoint: 23 November 2026

A standalone Windows x64 preview bundles Python, dependencies and frontend.
It has real one-panel/two-panel output, reconnect and per-panel management
checks. The owner confirmed iPhone Safari access and physical Micromaze control.
Layouts, enabled panels and timing preferences persist. The interface includes
media streaming, a seam demo and three optional games. Four PR #88-dependent
experiments are skipped in the normal source test suite.

The project is MIT licensed. The pinned upstream is unmodified; no new upstream
PR is required. Dated [validation](validation.md) preserves actual observations;
the original internal planning documents remain in the maintainer's private archive.

The [first Windows prerelease](https://github.com/TakalNL/bk-light-led-wall/releases/tag/v0.1.0-preview.1)
provides the standalone ZIP and SHA-256 checksum. It is an experimental preview,
not a claim that the broader acceptance checks below are complete.

## Before a stable release or broader support claims

- Explain and measure achieved output speed. Recent sessions show a repeatable
  top/bottom upload difference; compare the same workload on each panel, reverse
  connection order and evaluate the existing optional Windows connection hint.
  Display actual throughput without implying it measures physical LED refresh.
- Exercise a clean Windows host without Python, Git, saved identifiers, private
  scripts or the lab relay. Confirm discovery, short-code/QR phone access,
  restart/settings persistence, individual controls and actionable errors.
- Check iPhone Safari again on the final artifact and add Android Chrome coverage.
- Check busy/missing devices, USB power loss and interrupted uploads. Keep
  reconnection bounded and explicit; never retry ambiguous partial writes blindly.
- Verify each advertised game/layout combination and visible timing alignment
  across fresh connections. More than two panels remains experimental.
- Keep project/dependency notices, inspected artifacts and published checksums
  with each release. Automating reproducible release builds remains future work;
  the first prerelease uses the manually built and checked Windows artifact.

Documentation and the research write-up can be shared with the preview limits
stated. A broad "works immediately on any host" claim is not established.

## Deferred Linux acceptance

The owner deferred Linux Bluetooth investigation after the tested Ubuntu/Intel
configuration showed inconsistent GATT discovery and reads. A second adapter
or Linux host is needed before blaming a controller or claiming BlueZ support.
A Steam Deck or Bluetooth-capable Raspberry Pi is a possible comparison host;
neither has been tested. Do not imply ARM support from source portability.

After real one-panel/two-panel Linux playback is verified, provide an installation
path with BlueZ prerequisites, saved user data and optional systemd startup.
Validate natively before adding containers. Linux packaging and unattended
startup are not part of the current validated Windows preview.

## Later application work

- Persist selected content/settings and implement deliberate desired-state
  restoration, accounting for changes between native playback and temporary PNGs.
- Expose verified brightness, display power and orientation controls with clear
  distinctions between requested state, readback and what survives power loss.
- Integrate native GIF upload/slot selection if autonomous playback is needed;
  keep its state/context restrictions visible in the user flow.
- Define a supported automation API before adding Home Assistant/MQTT clients.
  Neither integration is required for the standalone controller.
- Test another purchaser's unit/batch and larger walls before widening claims.

Firmware flashing, unknown destructive commands, an exact native storage limit,
atomic hardware synchronization and universal maximum panel/FPS claims are not
requirements for this preview. The [findings](investigation-summary.md) and
[capability map](panel-capabilities.md) distinguish verified behavior from leads.
