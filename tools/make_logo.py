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
SWIATLO = (86, 104, 128)          # snop w tle, chłodny — postać ma się na czym odciąć

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


def tlo(szer: int, wys: int, reflektor=None, cien_y: int = 0) -> Image.Image:
    """Ciemny gradient, opcjonalny snop światła w tle i cień pod stopami.

    Światło idzie ZA postać, nie na nią: aura obrysowująca sylwetkę wyglądała jak mgła,
    a rozjaśniona plama tła robi to samo — odcina czarną sylwetkę „bez skina" — i przy
    okazji osadza postać w kadrze zamiast doklejać jej świecącą obwódkę.
    """
    plotno = Image.new("RGB", (szer, wys))
    rysuj = ImageDraw.Draw(plotno)
    for y in range(wys):
        t = y / max(wys - 1, 1)
        rysuj.line([(0, y), (szer, y)],
                   fill=tuple(round(g + (d - g) * t) for g, d in zip(TLO_GORA, TLO_DOL)))

    if reflektor:
        # Elipsa rozmyta na własnej masce, nie radial_gradient: ten drugi zanika do zera
        # dopiero w rogach swojego kwadratu, więc na bokach zostawia widoczną, prostą
        # krawędź — snop wygląda wtedy jak wklejony panel.
        x, y, r_x, r_y, sila = reflektor
        maska = Image.new("L", (szer, wys), 0)
        ImageDraw.Draw(maska).ellipse((x - r_x // 2, y - r_y // 2, x + r_x // 2, y + r_y // 2),
                                      fill=int(255 * sila))
        maska = maska.filter(ImageFilter.GaussianBlur(r_x * 0.45))
        plotno.paste(Image.new("RGB", (szer, wys), SWIATLO), (0, 0), maska)

    if cien_y:
        x = reflektor[0] if reflektor else szer // 2
        r_x, r_y = int(szer * 0.10), int(wys * 0.022)
        maska = Image.new("L", (szer, wys), 0)
        ImageDraw.Draw(maska).ellipse((x - r_x, cien_y - r_y, x + r_x, cien_y + r_y), fill=150)
        maska = maska.filter(ImageFilter.GaussianBlur(r_y))
        plotno.paste(Image.new("RGB", (szer, wys), (8, 9, 11)), (0, 0), maska)
    return plotno


def popiersie(render: Image.Image) -> Image.Image:
    """Kwadratowy kadr na głowę i tors — do ikony, gdzie cała sylwetka byłaby zbyt drobna."""
    bok = int(render.height * 0.52)
    lewo = (render.width - bok) // 2
    return render.crop((lewo, 0, lewo + bok, bok))


def postac(render: Image.Image, wysokosc: int) -> Image.Image:
    szer = round(render.width * wysokosc / render.height)
    return render.resize((szer, wysokosc), Image.LANCZOS)


def rozjasniona(warstwa: Image.Image) -> Image.Image:
    """Ta sama sylwetka rozjaśniona do bieli — moment założenia skina."""
    biel = Image.new("RGBA", warstwa.size, (255, 255, 255, 0))
    biel.putalpha(warstwa.getchannel("A"))
    return Image.blend(warstwa, biel, 0.7)


def klatki(plotno_tla: Image.Image, warstwy: list[Image.Image], pozycja,
           z_blyskiem: bool = True) -> tuple[list[Image.Image], list[int]]:
    """Każdy skin trzyma się chwilę, podmiana idzie przez jednoklatkowy błysk.

    Ikona jedzie bez błysku: w kilkudziesięciu pikselach i tak go nie widać, a klatek
    robi się dwa razy mniej — czyli mieści się w limicie 256 KiB.
    """
    obrazy, czasy = [], []
    for i, warstwa in enumerate(warstwy):
        # Pierwsza klatka bez błysku — GIF ma się otwierać czystą sylwetką „bez skina",
        # bo to ona jest miniaturką wszędzie tam, gdzie animacja jeszcze nie ruszyła.
        blysk = z_blyskiem and i > 0
        etapy = ([(rozjasniona(warstwa), MS_BLYSK)] if blysk else []) \
            + [(warstwa, MS_SKIN + (0 if blysk else MS_BLYSK))]
        for wersja, ms in etapy:
            kadr = plotno_tla.copy()
            kadr.paste(wersja, pozycja(wersja), wersja)
            obrazy.append(kadr)
            czasy.append(ms)
    return obrazy, czasy


def zapisz_gif(sciezka: Path, obrazy: list[Image.Image], czasy: list[int],
               kolory: int = 255) -> None:
    """Każda klatka dostaje własną paletę, bez ditheringu.

    Wspólna paleta na osiem różnych skinów nie starcza: 256 kolorów rozkłada się na
    wszystkie stroje naraz i cieniowanie rozłazi się w szum (z ditheringiem) albo
    w plamy (bez). GIF pozwala na paletę lokalną per klatka — tła i tak nie rusza,
    bo we wszystkich klatkach jest identyczne.
    """
    w_palecie = [o.quantize(colors=kolory, method=Image.MEDIANCUT, dither=Image.NONE)
                 for o in obrazy]
    w_palecie[0].save(sciezka, save_all=True, append_images=w_palecie[1:],
                      duration=czasy, loop=0, optimize=False)
    print(f"  {sciezka.relative_to(WYNIK.parent.parent)}  "
          f"{len(obrazy)} klatek, {sciezka.stat().st_size // 1024} KB")


def logo(warstwy_zrodlowe: list[Image.Image]) -> None:
    # 384 px i 128 kolorów, bo ikona projektu na Modrincie musi zmieścić się w 256 KiB
    # (i tak wyświetla się w kilkudziesięciu pikselach).
    bok = 384
    kadry = [popiersie(r) for r in warstwy_zrodlowe]
    wysokosc = int(bok * 0.92)
    warstwy = [postac(k, wysokosc) for k in kadry]
    # Bez snopa i bez cienia: przy takim zbliżeniu popiersie samo wypełnia kadr.
    plotno = tlo(bok, bok)
    pozycja = lambda w: ((bok - w.width) // 2, int(bok * 0.06))

    obrazy, czasy = klatki(plotno, warstwy, pozycja, z_blyskiem=False)
    zapisz_gif(WYNIK / "logo.gif", obrazy, czasy, kolory=128)
    obrazy[0].save(WYNIK / "logo.png")          # sylwetka bez skina = ikona statyczna
    print(f"  docs/media/logo.png  {(WYNIK / 'logo.png').stat().st_size // 1024} KB")


def hero(warstwy_zrodlowe: list[Image.Image]) -> None:
    szer, wys = 1280, 640
    wysokosc = int(wys * 0.80)
    warstwy = [postac(r, wysokosc) for r in warstwy_zrodlowe]
    lewa = int(szer * 0.23)
    stopy = int(wys * 0.94)
    plotno = tlo(szer, wys,
                 reflektor=(lewa, int(wys * 0.52), int(szer * 0.20), int(wys * 0.60), 0.42),
                 cien_y=stopy)

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

    pozycja = lambda w: (lewa - w.width // 2, stopy - w.height)
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
