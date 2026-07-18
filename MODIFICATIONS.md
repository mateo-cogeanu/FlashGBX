# Cartridge Play modifications

Modified from FlashGBX by Lesserkuma on 2026-07-18. This fork remains licensed
under GPL-3.0-or-later; the original copyright and license notices are retained.

## Added

- A dark, cartridge-first Play screen and left navigation shell.
- A dedicated Data page containing the complete existing FlashGBX interface.
- Cartridge title, platform, reader, and readiness presentation on the Play page.
- A single primary action that connects, detects, verifies, and prepares a game.
- Private cached ROM dumps followed by automatic mGBA or SameBoy launch.
- Emulator auto-discovery and a persistent custom-emulator selection.
- Checksum failures block automatic emulator launch and remain visibly reported.
- Cached Libretro box art for database-matched cartridges.
- Two-stage authenticity evidence: instant header checks and optional full-ROM
  CRC verification against the known-release database.

## Hardware behavior

The readers supported by FlashGBX are cartridge dumpers rather than a live
memory bus suitable for emulator fetches. “Play cartridge” therefore creates a
temporary local dump before starting the emulator. This is intentionally hidden
behind one action, but large Game Boy Advance cartridges still take as long as
the connected reader needs to transfer and verify them.

## Not yet included

- Bundling an emulator binary or emulator core.
- Automatic round-trip synchronization of emulator saves back to a cartridge.
- Continuous hot-swap polling on readers whose firmware does not report insert
  events. The Play action performs detection safely on those devices.
