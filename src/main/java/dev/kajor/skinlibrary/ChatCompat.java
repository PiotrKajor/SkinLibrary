package dev.kajor.skinlibrary;

import net.minecraft.network.chat.ClickEvent;
import net.minecraft.network.chat.Component;
import net.minecraft.network.chat.HoverEvent;
import net.minecraft.network.chat.Style;

/**
 * Klikalne i najeżdżalne fragmenty czatu na wersjach Minecrafta, które robią to różnie.
 *
 * <p>W 1.21.5 ClickEvent i HoverEvent zamieniły się z klasy z enumem Action na zestaw
 * rekordów. To jedyne miejsce w całym modzie, które w ogóle o tej różnicy wie — i jedyny
 * powód, dla którego jeden jar mógłby nie działać na całym zakresie 1.21.x.
 *
 * <p>Rozwiązanie: nowe API siedzi w osobnej klasie, ładowanej dopiero przy pierwszym
 * użyciu. Na starszym wydaniu jej załadowanie rzuca błąd, my go łapiemy i zwracamy styl
 * bez interakcji. Lista skinów wygląda wtedy skromniej, ale mod działa — zamiast wysypać
 * się przy starcie.
 */
final class ChatCompat {
    private static Boolean nowoczesne = null;   // null = jeszcze nie sprawdzone

    private ChatCompat() {}

    /** Styl uruchamiający komendę po kliknięciu; na starszych wersjach — styl bez zmian. */
    static Style runCommand(Style base, String command) {
        if (Boolean.FALSE.equals(nowoczesne)) return base;
        try {
            Style s = Modern.runCommand(base, command);
            nowoczesne = true;
            return s;
        } catch (Throwable t) {
            zapiszBrak(t);
            return base;
        }
    }

    /** Styl z dymkiem po najechaniu; na starszych wersjach — styl bez zmian. */
    static Style showText(Style base, Component text) {
        if (Boolean.FALSE.equals(nowoczesne)) return base;
        try {
            Style s = Modern.showText(base, text);
            nowoczesne = true;
            return s;
        } catch (Throwable t) {
            zapiszBrak(t);
            return base;
        }
    }

    private static void zapiszBrak(Throwable t) {
        if (nowoczesne == null) {
            SkinLibrary.LOG.info(
                    "Ta wersja Minecrafta ma starsze API czatu — lista skinów będzie bez klikania ({}).",
                    t.getClass().getSimpleName());
        }
        nowoczesne = false;
    }

    /**
     * API z 1.21.5+. MUSI być osobną klasą: dzięki temu odwołanie do ClickEvent.RunCommand
     * jest rozwiązywane dopiero przy jej ładowaniu, wewnątrz naszego try, a nie przy
     * weryfikacji metody wywołującej.
     *
     * ponytail: na starszych wydaniach po prostu odpuszczamy klikanie. Gdyby ktoś go
     * tam potrzebował, drogą jest refleksja po nazwach z MappingResolver Fabrica —
     * kilkadziesiąt linii, których dziś nie ma za co płacić.
     */
    private static final class Modern {
        static Style runCommand(Style base, String command) {
            return base.withClickEvent(new ClickEvent.RunCommand(command));
        }

        static Style showText(Style base, Component text) {
            return base.withHoverEvent(new HoverEvent.ShowText(text));
        }
    }
}
