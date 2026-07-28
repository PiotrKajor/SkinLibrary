# SkinLibrary

Server-side skin library for Fabric with a browsable, clickable list in chat.

Drop `.png` files into a folder — players pick skins with `/skin`, tab-complete included.
No web service to host, no API keys, no client-side mod.

[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

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
MineSkin upload; SkinLibrary adds the library, the browser and the sharing on top of it.

## Install

1. Put `fabric-api`, `fabrictailor` and `skinlibrary` into your server's `mods/` folder.
2. Start the server once — it creates `config/skinlibrary/`.
3. Drop `.png` skins (64×64 or 64×32) into `config/skinlibrary/skins/`.
4. `/skin reload`, and they are live.

The file name becomes the skin name: `pirate.png` → `/skin pirate`.

Server-side only — players join with a vanilla client and need nothing installed.

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
./gradlew build     # needs Java 21
```

The jar lands in `build/libs/`.

## License

MIT — see [LICENSE](LICENSE).
