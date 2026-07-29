<div align="center">

<sub><b>Polski</b> · <a href="CHANGELOG.en.md">English</a></sub>

</div>

# Historia zmian

Format wg [Keep a Changelog](https://keepachangelog.com/pl/1.1.0/),
wersjonowanie wg [SemVer](https://semver.org/lang/pl/).

## [1.0.1] — 2026-07-29

### Naprawione

- **`/skin` wywalało serwer na 1.21.9 i 1.21.10.** Mod wołał `ServerPlayer.getServer()`,
  którego w tych wydaniach już nie ma — `NoSuchMethodError` leciał w pętli tickowej, więc
  padał cały serwer, nie sama komenda. Serwer bierzemy teraz z `CommandSourceStack`.
- **`/skin` nie działało na 1.21–1.21.8.** Wysyłka wiadomości szła przez
  `ServerPlayer.sendSystemMessage`, które pojawiło się dopiero w 1.21.9. Wszystkie
  wiadomości idą teraz przez `CommandSourceStack.sendSuccess`, wspólny dla całego zakresu.
- **`/skin reset` nie działało na 1.21.9+.** Nick gracza pochodził z `GameProfile.getName()`,
  a w nowszej wersji authlib `GameProfile` jest rekordem z `name()`. Nick bierzemy ze źródła
  komendy i biblioteki authlib nie dotykamy w ogóle.

### Zmienione

- Wspierany zakres zawężony do **1.21 – 1.21.10**. W 1.21.11 nie ma już
  `CommandSourceStack.hasPermission`, z którego korzysta opcja `requireOperator`,
  a nie mamy jak tej wersji przetestować — lepiej jej nie deklarować, niż zgadywać.

### Dodane

- `tools/check_api.py` — sprawdza gotowy jar wobec mapowań każdej wspieranej wersji
  Minecrafta i odrzuca go, jeśli mod woła cokolwiek, czego w którymś wydaniu nie ma.
  Wyłapuje też rzuty na typy Minecrafta i odwołania do authlib, czyli dokładnie te dwie
  pułapki, które stały za błędami powyżej.

## [1.0.0] — 2026-07-29

Pierwsze wydanie.

- Klikalna lista biblioteki na czacie: stronicowana, pogrupowana po autorach,
  ze skrótami „Losowy" i „Mój skin".
- `/skin <nazwa>`, `/skin random`, `/skin player <nick>`, `/skin url <adres>`,
  `/skin reset`, `/skin reload`.
- Biblioteka to zwykły folder z plikami PNG; opcjonalny `skins.json` na bogatsze wpisy
  i opcjonalny katalog po HTTP (`libraryUrl`).
- Cache tekstur, podpowiedzi nazw, tłumaczenia `en_us` i `pl_pl`, własne pliki językowe.
- Jeden jar na cały wspierany zakres. Na 1.21.4 i starszych lista wypisuje się bez
  klikania, poza tym działa tak samo.
