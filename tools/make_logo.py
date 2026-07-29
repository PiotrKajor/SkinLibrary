#!/usr/bin/env python3
"""Składa logo i grafikę do galerii Modrinth z renderów postaci w różnych skinach.

Animacja jest treścią moda: ta sama postać przewija się przez kolejne skiny z biblioteki.
Pierwsza klatka to zawsze czarna sylwetka ze znakiem zapytania — „skin nieustawiony",
od którego gracz zaczyna. Rozpoznajemy ją po liczbie kolorów (ma ich kilka, pozostałe
rendery setki), więc nazwy plików nie mają znaczenia.

Użycie:  python3 tools/make_logo.py [katalog_z_renderami]
Wynik:   docs/media/logo.gif (kwadrat, ikona projektu), logo.png (pierwsza klatka),
         docs/media/hero.gif (szeroka, do galerii)
"""
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

ZRODLA = Path(sys.argv[1] if len(sys.argv) > 1
              else "/home/skynet/pliczki/pliki do loga SkinLibrary")
WYNIK = Path(__file__).resolve().parent.parent / "docs" / "media"
FONTY = Path("/home/skynet/WebRoot/Fonts")

TLO_GORA, TLO_DOL = (16, 18, 22), (25, 29, 35)
ZIELEN = (27, 217, 106)          # akcent Modrintha
SZARY = (150, 158, 170)

MS_SKIN = 850                     # ile trzyma się jeden skin
MS_BLYSK = 70                     # błysk w momencie podmiany


def rendery() -> list[Image.Image]:
    """Rendery przycięte do wspólnego kadru, z sylwetką „bez skina" na początku."""
    pliki = sorted(p for p in ZRODLA.glob("*.png"))
    if not pliki:
        sys.exit(f"BŁĄD: brak plików PNG w {ZRODLA}")
    obrazy = {p: Image.open(p).convert("RGBA") for p in pliki}

    # Wspólny kadr = suma wszystkich ramek, żeby postać nie skakała między klatkami
    # (kapelusze i narzędzia wystają w różnych miejscach).
    ramki = [im.getchannel("A").getbbox() for im in obrazy.values()]
    kadr = (min(r[0] for r in ramki), min(r[1] for r in ramki),
            max(r[2] for r in ramki), max(r[3] for r in ramki))

    def barwy(im):
        return len({p[:3] for p in im.getdata() if p[3] > 200})

    anonim = min(obrazy, key=lambda p: barwy(obrazy[p]))
    kolejnosc = [anonim] + [p for p in pliki if p != anonim]
    return [obrazy[p].crop(kadr) for p in kolejnosc]


def tlo(szer: int, wys: int, srodek_x: int) -> Image.Image:
    """Ciemny gradient z lekkim rozjaśnieniem tam, gdzie stanie postać."""
    plotno = Image.new("RGB", (szer, wys))
    rysuj = ImageDraw.Draw(plotno)
    for y in range(wys):
        t = y / max(wys - 1, 1)
        rysuj.line([(0, y), (szer, y)],
                   fill=tuple(round(g + (d - g) * t) for g, d in zip(TLO_GORA, TLO_DOL)))

    promien = int(wys * 0.55)
    reflektor = Image.radial_gradient("L").resize((promien * 2, promien * 2))
    reflektor = reflektor.point(lambda v: int((255 - v) * 0.10))
    plotno.paste(Image.new("RGB", reflektor.size, (90, 105, 125)),
                 (srodek_x - promien, wys // 2 - promien), reflektor)
    return plotno


def obrys(warstwa: Image.Image) -> Image.Image:
    """Zielona poświata z konturu postaci.

    Bez niej pierwsza klatka — czarna sylwetka — znika na ciemnym tle, a to ona ma być
    twarzą moda. Przy okazji odcina od tła każdy kolejny skin.
    """
    ksztalt = warstwa.getchannel("A")
    ksztalt = ksztalt.filter(ImageFilter.MaxFilter(9)).filter(ImageFilter.GaussianBlur(16))
    ksztalt = ksztalt.point(lambda v: int(v * 0.55))
    swiatlo = Image.new("RGBA", warstwa.size, ZIELEN + (0,))
    swiatlo.putalpha(ksztalt)
    return swiatlo


def postac(render: Image.Image, wysokosc: int) -> Image.Image:
    szer = round(render.width * wysokosc / render.height)
    return render.resize((szer, wysokosc), Image.LANCZOS)


def rozjasniona(warstwa: Image.Image) -> Image.Image:
    """Ta sama sylwetka rozjaśniona do bieli — moment założenia skina."""
    biel = Image.new("RGBA", warstwa.size, (255, 255, 255, 0))
    biel.putalpha(warstwa.getchannel("A"))
    return Image.blend(warstwa, biel, 0.7)


def klatki(plotno_tla: Image.Image, warstwy: list[Image.Image],
           pozycja) -> tuple[list[Image.Image], list[int]]:
    """Każdy skin trzyma się chwilę, podmiana idzie przez jednoklatkowy błysk."""
    obrazy, czasy = [], []
    for warstwa in warstwy:
        swiatlo = obrys(warstwa)
        for wersja, ms in ((rozjasniona(warstwa), MS_BLYSK), (warstwa, MS_SKIN)):
            kadr = plotno_tla.copy()
            gdzie = pozycja(wersja)
            kadr.paste(swiatlo, gdzie, swiatlo)
            kadr.paste(wersja, gdzie, wersja)
            obrazy.append(kadr)
            czasy.append(ms)
    return obrazy, czasy


def zapisz_gif(sciezka: Path, obrazy: list[Image.Image], czasy: list[int]) -> None:
    """Każda klatka dostaje własną paletę, bez ditheringu.

    Wspólna paleta na osiem różnych skinów nie starcza: 256 kolorów rozkłada się na
    wszystkie stroje naraz i cieniowanie rozłazi się w szum (z ditheringiem) albo
    w plamy (bez). GIF pozwala na paletę lokalną per klatka — tła i tak nie rusza,
    bo we wszystkich klatkach jest identyczne.
    """
    w_palecie = [o.quantize(colors=255, method=Image.MEDIANCUT, dither=Image.NONE)
                 for o in obrazy]
    w_palecie[0].save(sciezka, save_all=True, append_images=w_palecie[1:],
                      duration=czasy, loop=0, optimize=False)
    print(f"  {sciezka.relative_to(WYNIK.parent.parent)}  "
          f"{len(obrazy)} klatek, {sciezka.stat().st_size // 1024} KB")


def logo(warstwy_zrodlowe: list[Image.Image]) -> None:
    bok = 640
    wysokosc = int(bok * 0.72)
    warstwy = [postac(r, wysokosc) for r in warstwy_zrodlowe]
    plotno = tlo(bok, bok, bok // 2)
    pozycja = lambda w: ((bok - w.width) // 2, int(bok * 0.95) - w.height)

    obrazy, czasy = klatki(plotno, warstwy, pozycja)
    zapisz_gif(WYNIK / "logo.gif", obrazy, czasy)
    obrazy[1].save(WYNIK / "logo.png")          # klatka bez błysku = ikona statyczna
    print(f"  docs/media/logo.png  {(WYNIK / 'logo.png').stat().st_size // 1024} KB")


def hero(warstwy_zrodlowe: list[Image.Image]) -> None:
    szer, wys = 1280, 640
    wysokosc = int(wys * 0.80)
    warstwy = [postac(r, wysokosc) for r in warstwy_zrodlowe]
    lewa = int(szer * 0.23)
    plotno = tlo(szer, wys, lewa)

    rysuj = ImageDraw.Draw(plotno)
    tytul = ImageFont.truetype(str(FONTY / "Poppins-ExtraBold.ttf"), 92)
    podtytul = ImageFont.truetype(str(FONTY / "Poppins-Medium.ttf"), 32)
    mono = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf", 34)

    x = int(szer * 0.42)
    rysuj.text((x, 210), "SkinLibrary", font=tytul, fill=(255, 255, 255))
    rysuj.text((x, 320), "Change your skin without leaving the server",
               font=podtytul, fill=SZARY)

    # Pigułka z komendą — to pierwsza rzecz, której szuka się w opisie moda.
    napis = "/skin"
    w_tekstu = rysuj.textlength(napis, font=mono)
    rysuj.rounded_rectangle((x, 390, x + w_tekstu + 52, 462), radius=14, fill=(31, 35, 41))
    rysuj.text((x + 26, 403), napis, font=mono, fill=ZIELEN)

    pozycja = lambda w: (lewa - w.width // 2, int(wys * 0.94) - w.height)
    obrazy, czasy = klatki(plotno, warstwy, pozycja)
    zapisz_gif(WYNIK / "hero.gif", obrazy, czasy)


def main() -> None:
    WYNIK.mkdir(parents=True, exist_ok=True)
    zrodla = rendery()
    print(f"{len(zrodla)} renderów z {ZRODLA}")
    logo(zrodla)
    hero(zrodla)


if __name__ == "__main__":
    main()
