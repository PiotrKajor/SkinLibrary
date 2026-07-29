<div align="center">

<sub><a href="CHANGELOG.md">Polski</a> · <b>English</b></sub>

</div>

# Changelog

Format based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
versioning follows [SemVer](https://semver.org/).

## [1.0.1] — 2026-07-29

### Fixed

- **`/skin` crashed the server on 1.21.9 and 1.21.10.** The mod called
  `ServerPlayer.getServer()`, which those releases no longer have — the `NoSuchMethodError`
  landed in the server tick loop, so the whole server went down, not just the command.
  The server now comes from `CommandSourceStack`.
- **`/skin` failed on 1.21 through 1.21.8.** Messages went out via
  `ServerPlayer.sendSystemMessage`, which only appeared in 1.21.9. Everything now goes
  through `CommandSourceStack.sendSuccess`, which is the same across the whole range.
- **`/skin reset` failed on 1.21.9+.** The player's name came from `GameProfile.getName()`,
  but in newer authlib `GameProfile` is a record with `name()`. The name now comes from the
  command source and authlib is not touched at all.

### Changed

- Supported range narrowed to **1.21 – 1.21.10**. 1.21.11 dropped
  `CommandSourceStack.hasPermission`, which the `requireOperator` option relies on, and we
  have no way to test that version — better to leave it out than to guess.

### Added

- `tools/check_api.py` — checks a built jar against the mappings of every supported
  Minecraft version and rejects it if the mod calls anything missing from any of them.
  It also flags casts to Minecraft types and direct authlib usage: precisely the two traps
  behind the bugs above.

## [1.0.0] — 2026-07-29

First release.

- Clickable in-chat library browser: paged, grouped by author, with Random / Original shortcuts.
- `/skin <name>`, `/skin random`, `/skin player <nick>`, `/skin url <address>`,
  `/skin reset`, `/skin reload`.
- The library is a plain folder of PNGs; optional `skins.json` for richer entries and an
  optional HTTP catalogue (`libraryUrl`).
- Texture cache, tab-complete, `en_us` + `pl_pl` translations, drop-in language files.
- One jar for the whole supported range. On 1.21.4 and older the list prints without click
  support; everything else is unchanged.
