#!/usr/bin/env python3
"""Sprawdza, czy jar odwołuje się wyłącznie do API obecnego we WSZYSTKICH wspieranych wersjach MC.

„Jeden jar na 1.21+" znaczy tyle, że każde wywołanie Minecrafta musi istnieć w każdym
wydaniu z zakresu. Kompilator widzi tylko wersję, pod którą budujemy (mappings z
gradle.properties) — brak metody w pozostałych wychodzi dopiero u gracza, jako
NoSuchMethodError w środku komendy, czyli crash pętli tickowej.

Metoda: bajtkod jara jest w mapowaniach intermediary (class_1234.method_5678), więc
wystarczy sprawdzić, czy każdy użyty identyfikator występuje w mappings.tiny danej wersji.
Dziedziczenia nie rozwijamy — liczy się samo istnienie symbolu, i to wystarcza:
tak właśnie wyszły oba błędy z 2026-07-29 (method_5682 znikło w 1.21.10,
method_64398 nie istniało przed 1.21.9).

Osobno zgłaszane są dwie rzeczy, których sprawdzenie samych symboli nie łapie:

* **odwołania do com.mojang.authlib** — biblioteka zmienia kształt między wydaniami MC
  (GameProfile bywa klasą z getName(), bywa rekordem z name()) i nie ma jej w mapowaniach;
* **rzuty na typy Minecrafta** (`checkcast`) — symbol może istnieć w każdej wersji, a i tak
  wysypać się na hierarchii. Tak było z `(CommandSource) player`: metoda istniała wszędzie,
  ale w 1.21.9 Entity przestało implementować ten interfejs i każde /skin kończyło się
  ClassCastException. Weryfikacja symboli tego nie widziała.

W obu wypadkach jedyne bezpieczne wyjście to refleksja albo API, które rzutu nie wymaga.

Użycie:  python3 tools/check_api.py build/libs/skinlibrary-1.0.0.jar
Wyjście: 0 = jar bezpieczny dla całego zakresu, 1 = są odwołania nie do odratowania.
"""
import re
import shutil
import subprocess
import sys
import tempfile
import urllib.request
import zipfile
from pathlib import Path

# Zakres deklarowany na Modrinth. Dopisujesz wersję tam → dopisz ją i tutaj.
# 1.21.11 świadomie poza zakresem: zniknęło stamtąd CommandSourceStack.hasPermission
# (method_9259), z którego korzysta opcja requireOperator.
SUPPORTED = ["1.21", "1.21.1", "1.21.2", "1.21.3", "1.21.4", "1.21.5",
             "1.21.6", "1.21.7", "1.21.8", "1.21.9", "1.21.10"]

# Klasy, którym wolno używać nowszego API: ładowane leniwie, z łapaniem Throwable, więc
# ich brak na starszym wydaniu degraduje funkcję zamiast wywalać moda (patrz ChatCompat).
OPCJONALNE = {"ChatCompat$Modern"}

MAVEN = "https://maven.fabricmc.net/net/fabricmc/intermediary/{v}/intermediary-{v}-v2.jar"
CACHE = Path.home() / ".cache" / "skinlibrary-mappings"
SYMBOL = re.compile(r"\b(?:class|method|field)_\d+\b")
RZUT = re.compile(r"checkcast.*net/minecraft/(class_\d+)")

# Rzuty, które wstawia sam kompilator przy wymazywaniu generyków — nie ma ich w źródle,
# więc nie ma czego naprawiać. class_2168 to CommandSourceStack, parametr typu w każdym
# CommandContext i LiteralArgumentBuilder w tym modzie. Typy z com.mojang.brigadier
# pomijamy w ogóle: to osobna biblioteka, jej hierarchia nie zależy od wersji Minecrafta.
RZUTY_Z_GENERYKOW = {"class_2168"}


def symbole_jara(jar: Path) -> tuple[set[str], list[str]]:
    """Identyfikatory MC użyte w bajtkodzie + linie z odwołaniami do authlib.

    Klasy z OPCJONALNE pomijamy: ładują się leniwie, a ich brak jest łapany i obsłużony,
    więc wolno im sięgać po API nowsze niż dolna granica zakresu.
    """
    uzyte: set[str] = set()
    ryzykowne: set[str] = set()
    with tempfile.TemporaryDirectory() as tmp:
        with zipfile.ZipFile(jar) as z:
            z.extractall(tmp)
        klasy = sorted(Path(tmp).rglob("*.class"))
        if not klasy:
            sys.exit(f"BŁĄD: {jar} nie zawiera żadnych klas")
        for plik in klasy:
            if plik.stem in OPCJONALNE:
                continue
            out = subprocess.run(["javap", "-c", "-p", str(plik)],
                                 capture_output=True, text=True, check=True).stdout
            uzyte |= set(SYMBOL.findall(out))
            for linia in out.splitlines():
                if "com/mojang/authlib" in linia:
                    ryzykowne.add(f"authlib wprost: {linia.strip()}")
                rzut = RZUT.search(linia)
                if rzut and rzut.group(1) not in RZUTY_Z_GENERYKOW:
                    ryzykowne.add(f"rzut na typ MC ({rzut.group(1)}): {linia.strip()}")
    return uzyte, sorted(ryzykowne)


def symbole_wersji(wersja: str) -> set[str]:
    CACHE.mkdir(parents=True, exist_ok=True)
    plik = CACHE / f"intermediary-{wersja}.jar"
    if not plik.exists():
        with urllib.request.urlopen(MAVEN.format(v=wersja), timeout=60) as r, \
             tempfile.NamedTemporaryFile(delete=False) as tmp:
            shutil.copyfileobj(r, tmp)
        Path(tmp.name).replace(plik)
    with zipfile.ZipFile(plik) as z:
        return set(SYMBOL.findall(z.read("mappings/mappings.tiny").decode()))


def main() -> int:
    jar = Path(sys.argv[1] if len(sys.argv) > 1
               else "build/libs/skinlibrary-1.0.0.jar")
    if not jar.exists():
        sys.exit(f"BŁĄD: nie ma pliku {jar}")

    uzyte, ryzykowne = symbole_jara(jar)
    print(f"{jar.name}: {len(uzyte)} identyfikatorów MC, {len(SUPPORTED)} wersji do sprawdzenia\n")

    zle = False
    for wersja in SUPPORTED:
        brakuje = sorted(uzyte - symbole_wersji(wersja))
        if brakuje:
            zle = True
            print(f"  {wersja:<8} BRAK: {', '.join(brakuje)}")
        else:
            print(f"  {wersja:<8} ok")

    if ryzykowne:
        zle = True
        print("\n  konstrukcje, których sprawdzenie symboli nie obejmuje:")
        for linia in ryzykowne:
            print(f"    {linia}")

    print("\n" + ("ODRZUCONY — nie wgrywaj tego jara" if zle
                  else "OK — jar bezpieczny dla całego zakresu"))
    return 1 if zle else 0


if __name__ == "__main__":
    sys.exit(main())
