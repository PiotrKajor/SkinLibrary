<div align="center">

<sub><a href="README.md">Polski</a> · <b>English</b></sub>

# 🎭 SkinLibrary

**Server-side skin library for Fabric — players pick a skin from a clickable list in chat.**

Drop `.png` files into a folder; players join with a vanilla client and type `/skin`.
Nothing to install on their side, no web service to host, no API keys.

[![Download jar](https://img.shields.io/badge/Download-skinlibrary.jar-4fb4ff?style=for-the-badge)](../../releases/latest)
&nbsp;
![Minecraft](https://img.shields.io/badge/Minecraft%201.21%2B%20%7C%20Fabric-2a3245?style=for-the-badge)
&nbsp;
![License](https://img.shields.io/badge/license-MIT-3ddc84?style=for-the-badge)

<!-- Hero image/GIF slot: drop the file into docs/media/ and uncomment the line below. -->
<!-- <img src="docs/media/hero.gif" alt="Skin list in Minecraft chat" width="720"> -->

</div>

---

## What it does

| Command | What happens |
|---|---|
| `/skin` | Browse the library — paged, grouped by author, entries are clickable |
| `/skin <name>` | Wear a skin from the library |
| `/skin random` | Wear a random one |
| `/skin player <nick>` | Wear the skin of any Minecraft account |
| `/skin url <address>` | Wear a skin from a PNG link |
| `/skin reset` | Back to your own account skin |
| `/skin reload` | Reload the library (operators) |

[FabricTailor](https://modrinth.com/mod/fabrictailor) does the actual skin swapping and the
MineSkin upload; SkinLibrary adds the curated library and the in-chat browser on top of it.

## What it looks like

Media lives in [`docs/media/`](docs/media/) — the file names below are already wired up,
so once a recording is in place just uncomment the matching line
(recording tips: [docs/media/README.md](docs/media/README.md)).

<!-- ![Browsing the library in chat](docs/media/browser.gif) -->
<!-- ![Changing a skin in game](docs/media/skin-change.gif) -->
<!-- For a longer demo (.mp4), attach it to a release or drag it into an issue and paste the link here. -->

## Features

- 🖱️ **Clickable in-chat list** — paged, grouped by author, with "◀ Previous / Next ▶"
  navigation and 🎲 Random / ↺ Original shortcuts.
- ⌨️ **Tab-complete** for skin names — nobody has to memorise the library.
- 📁 **The library is just a folder** — the file name becomes the skin name, then `/skin reload`.
- 🌐 **Skins from outside the library** — `/skin player <nick>` and `/skin url <address>`,
  both switchable in the config.
- 🧠 **Texture cache** — a texture fetched once is not sent to MineSkin again.
- 🗣️ **Translations** — `en_us` and `pl_pl` built in, your own language without a rebuild.
- 📦 **One jar for 1.21+** — no mixins, no per-version builds.
- 🔌 **Optional HTTP catalogue** (`libraryUrl`) — if you already run a skin service.

## Requirements

A Fabric server on **1.21 or newer**, Java 21, and in `mods/`:
[Fabric API](https://modrinth.com/mod/fabric-api) and [FabricTailor](https://modrinth.com/mod/fabrictailor).

Server-side only — players join with a vanilla client and need nothing installed.

## Quick start

1. Put `fabric-api`, `fabrictailor` and `skinlibrary` into your server's `mods/` folder.
2. Start the server once — it creates `config/skinlibrary/`.
3. Drop `.png` skins (64×64 or 64×32) into `config/skinlibrary/skins/`.
4. `/skin reload`, and they are live.

The file name becomes the skin name: `pirate.png` → `/skin pirate`.

## Configuration

`config/skinlibrary/config.json`, created on first start:

```json
{
  "language": "en_us",
  "allowPlayerSkins": true,
  "allowUrlSkins": true,
  "cooldownSeconds": 5,
  "requireOperator": false,
  "pageSize": 8,
  "slimByDefault": false,
  "libraryUrl": "",
  "commandAliases": ["skin", "skins"]
}
```

Nothing here is required — the defaults work. Notable options:

- **`commandAliases`** — rename the command if another mod already owns `/skin`.
- **`slimByDefault`** — treat file skins as the slim (Alex) model.
- **`libraryUrl`** — optional HTTP catalogue, if you already run one. It must answer with
  `{"skins": [{"name": "...", "value": "...", "signature": "...", "author": "..."}]}`;
  entries may use `url` instead of `value`.

### Richer entries

For anything beyond "a PNG in a folder", add `config/skinlibrary/skins.json`:

```json
{
  "notch":  { "player": "Notch",                      "author": "mojang" },
  "banner": { "url": "https://example.com/skin.png",  "author": "alice"  },
  "alex":   { "file": "alex.png", "slim": true,       "author": "bob"    }
}
```

Entries are grouped by `author` in the browser, so a shared server can see who added what.

### Translations

Built in: `en_us`, `pl_pl`. Set `language` in the config.

To add your own, drop `config/skinlibrary/lang/<code>.json` with the same keys as
[`en_us.json`](src/main/resources/assets/skinlibrary/lang/en_us.json) — no rebuild needed.

## Minecraft versions

One jar covers **1.21 and up**. The mod has no mixins and stays off the parts of the API that
shift between releases, so it does not need a rebuild per point release.

The single exception is clickable chat: Minecraft 1.21.5 replaced the click/hover event API.
On 1.21.5+ the list is clickable; on older releases the same list prints without click support
and everything else works unchanged.

## Building

```bash
./gradlew build              # needs Java 21
python3 tools/check_lang.py  # message keys match across languages
```

The jar lands in `build/libs/`.

## License

[MIT](LICENSE).
