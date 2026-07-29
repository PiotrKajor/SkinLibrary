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

TLO = (22, 24, 28)                # płaskie tło pod kolor ciemnego motywu Modrintha
ZIELEN = (27, 217, 106)          # akcent Modrintha
SZARY = (150, 158, 170)
SWIATLO = (86, 104, 128)          # snop w tle, chłodny — postać ma się na czym odciąć

MS_SKIN = 850                     # ile trzyma się jeden skin
MS_BLYSK = 70                     # błysk w momencie podmiany


def rendery() -> tuple[list[Image.Image], Image.Image, Image.Image]:
    """Skiny do rotacji plus dwie sylwetki „bez skina": ze znakiem na głowie i na torsie.

    To dwa warianty tego samego stanu, więc nigdy nie lecą w jednej animacji. Ikona bierze
    tę ze znakiem na głowie — w kadrze na popiersie tylko ona jest czytelna. Banner bierze
    tę ze znakiem na torsie, bo pokazuje całą sylwetkę i tam znak widać bez problemu.
    """
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

    # Sylwetkę ze znakiem na głowie poznajemy po nazwie pliku („start"), bo wygładzone
    # krawędzie znaku dają jej kilkaset barw. Tę ze znakiem na torsie — po tym, że barw ma
    # kilka: cała jest jednolicie czarna.
    nazwane = [p for p in pliki if p.stem.lower().startswith("start")]
    glowa = nazwane[0] if nazwane else None
    plaskie = [p for p in pliki if p != glowa and barwy(obrazy[p]) < 5]
    tors = min(plaskie, key=lambda p: barwy(obrazy[p])) if plaskie else None
    if glowa is None:
        glowa = tors
    if tors is None:
        tors = glowa
    if glowa is None:
        sys.exit(f"BŁĄD: w {ZRODLA} nie ma żadnej sylwetki „bez skina\"")

    skiny = [p for p in pliki if p not in (glowa, tors)]
    przytnij = lambda p: obrazy[p].crop(kadr)
    return [przytnij(p) for p in skiny], przytnij(glowa), przytnij(tors)


def tlo(szer: int, wys: int, reflektor=None, cien_y: int = 0) -> Image.Image:
    """Płaskie ciemne tło, opcjonalny snop światła i cień pod stopami.

    Tło jest jednolite, nie gradientowe, z powodu palety: gradient to setki odcieni szarości,
    które w GIF-ie zjadają miejsce potrzebne skinom, a wtedy wspólna paleta przestaje starczać.

    Światło idzie ZA postać, nie na nią: aura obrysowująca sylwetkę wyglądała jak mgła,
    a rozjaśniona plama tła robi to samo — odcina czarną sylwetkę „bez skina" — i przy
    okazji osadza postać w kadrze zamiast doklejać jej świecącą obwódkę.
    """
    plotno = Image.new("RGB", (szer, wys), TLO)

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
        x = reflektor[0] if reflektor else int(szer * 0.23)
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
    """Jedna paleta na cały GIF, bez ditheringu.

    Paleta liczona per klatka wygląda lepiej na samych skinach, ale wszystko, co w kadrze
    stałe, dostaje wtedy w każdej klatce inne przybliżenie — zielony napis /skin chodził
    tak od (27,217,106) do (101,204,143) i widocznie migotał. Wspólna paleta trzyma stałe
    elementy w ryzach; miejsce na nią bierze się stąd, że tło jest płaskie.
    """
    pasek = Image.new("RGB", (obrazy[0].width, obrazy[0].height * len(obrazy)))
    for i, o in enumerate(obrazy):
        pasek.paste(o, (0, i * obrazy[0].height))
    paleta = pasek.quantize(colors=kolory, method=Image.MEDIANCUT)
    w_palecie = [o.quantize(palette=paleta, dither=Image.NONE) for o in obrazy]
    w_palecie[0].save(sciezka, save_all=True, append_images=w_palecie[1:],
                      duration=czasy, loop=0, optimize=False)
    print(f"  {sciezka.relative_to(WYNIK.parent.parent)}  "
          f"{len(obrazy)} klatek, {sciezka.stat().st_size // 1024} KB")


def logo(skiny: list[Image.Image], sylwetka: Image.Image) -> None:
    # 384 px i 128 kolorów, bo ikona projektu na Modrincie musi zmieścić się w 256 KiB
    # (i tak wyświetla się w kilkudziesięciu pikselach).
    bok = 384
    kadry = [popiersie(r) for r in [sylwetka] + skiny]
    wysokosc = int(bok * 0.92)
    warstwy = [postac(k, wysokosc) for k in kadry]
    # Bez snopa i bez cienia: przy takim zbliżeniu popiersie samo wypełnia kadr.
    plotno = tlo(bok, bok)
    pozycja = lambda w: ((bok - w.width) // 2, int(bok * 0.06))

    obrazy, czasy = klatki(plotno, warstwy, pozycja, z_blyskiem=False)
    zapisz_gif(WYNIK / "logo.gif", obrazy, czasy, kolory=128)
    obrazy[0].save(WYNIK / "logo.png")          # sylwetka bez skina = ikona statyczna
    print(f"  docs/media/logo.png  {(WYNIK / 'logo.png').stat().st_size // 1024} KB")


def hero(skiny: list[Image.Image], sylwetka: Image.Image) -> None:
    szer, wys = 1280, 640
    wysokosc = int(wys * 0.80)
    warstwy = [postac(r, wysokosc) for r in [sylwetka] + skiny]
    lewa = int(szer * 0.23)
    stopy = int(wys * 0.94)
    # Bez snopa: przy jednej palecie na cały GIF miękki gradient rozkłada się na kilkanaście
    # odcieni i widać koncentryczne obwódki. Płaskie tło nie ma jak się prążkować, a ciemna
    # sylwetka i tak się od niego odcina.
    plotno = tlo(szer, wys, cien_y=stopy)

    rysuj = ImageDraw.Draw(plotno)
    tytul = ImageFont.truetype(str(FONTY / "Poppins-ExtraBold.ttf"), 92)
    podtytul = ImageFont.truetype(str(FONTY / "Poppins-Medium.ttf"), 32)
    mono = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf", 34)

    x = int(szer * 0.42)
    # Wiersze rozsunięte: Poppins ExtraBold w 92 px ma wydłużenia dolne, które przy
    # ciaśniejszym odstępie wchodziły w podtytuł.
    rysuj.text((x, 196), "SkinLibrary", font=tytul, fill=(255, 255, 255))
    rysuj.text((x, 330), "Change your skin without leaving the server",
               font=podtytul, fill=SZARY)

    # Pigułka z komendą — to pierwsza rzecz, której szuka się w opisie moda.
    napis = "/skin"
    w_tekstu = rysuj.textlength(napis, font=mono)
    rysuj.rounded_rectangle((x, 404, x + w_tekstu + 52, 476), radius=14, fill=(33, 37, 44))
    rysuj.text((x + 26, 417), napis, font=mono, fill=ZIELEN)

    pozycja = lambda w: (lewa - w.width // 2, stopy - w.height)
    obrazy, czasy = klatki(plotno, warstwy, pozycja, z_blyskiem=False)
    zapisz_gif(WYNIK / "hero.gif", obrazy, czasy)


def poradnik() -> None:
    """Nagranie z gry → docs/media/browser.gif, w rozmiarze do przyjęcia dla galerii.

    Surowe nagranie ma 50 klatek na sekundę i 7 MB; do pokazania listy skinów wystarczy
    połowa tego i węższy kadr. Tu wspólna paleta jest lepsza niż lokalna (odwrotnie niż
    w logo): scena jest cały czas ta sama, więc jedna paleta wychodzi mniejsza.
    """
    nagrania = sorted(ZRODLA.glob("*/*.gif"))
    if not nagrania:
        print("  (brak nagrania z gry — pomijam browser.gif)")
        return

    zrodlo = Image.open(nagrania[0])
    szerokosc = 960
    klatki_wy, czasy = [], []
    for i in range(zrodlo.n_frames):
        if i % 2:                       # co druga klatka: 50 fps → 25 fps
            continue
        zrodlo.seek(i)
        k = zrodlo.convert("RGB")
        klatki_wy.append(k.resize((szerokosc, round(k.height * szerokosc / k.width)),
                                  Image.LANCZOS))
        czasy.append(2 * zrodlo.info.get("duration", 40))

    pasek = Image.new("RGB", (szerokosc, klatki_wy[0].height * len(klatki_wy)))
    for i, k in enumerate(klatki_wy):
        pasek.paste(k, (0, i * klatki_wy[0].height))
    paleta = pasek.quantize(colors=200, method=Image.MEDIANCUT)

    w_palecie = [k.quantize(palette=paleta, dither=Image.NONE) for k in klatki_wy]
    for k in w_palecie:
        # Nagranie niesie ze sobą wpis o przezroczystości; po kwantyzacji wskazuje on
        # na krotkę zamiast indeksu i zapis GIF-a się o to wywraca.
        k.info.pop("transparency", None)
    cel = WYNIK / "browser.gif"
    w_palecie[0].save(cel, save_all=True, append_images=w_palecie[1:],
                      duration=czasy, loop=0, optimize=True)
    print(f"  docs/media/browser.gif  {len(w_palecie)} klatek, {cel.stat().st_size // 1024} KB")


def main() -> None:
    WYNIK.mkdir(parents=True, exist_ok=True)
    skiny, sylwetka_glowa, sylwetka_tors = rendery()
    print(f"{len(skiny)} skinów z {ZRODLA} + dwie sylwetki bez skina")
    logo(skiny, sylwetka_glowa)
    hero(skiny, sylwetka_tors)
    poradnik()


if __name__ == "__main__":
    main()
