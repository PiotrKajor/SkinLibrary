package dev.kajor.skinlibrary;

import net.minecraft.server.level.ServerPlayer;

import java.lang.reflect.Method;
import java.nio.file.Path;
import java.util.Optional;

/**
 * Cały styk z FabricTailorem — wyłącznie przez refleksję.
 *
 * <p>Powód: FabricTailor jest jedynym sposobem podmiany skina po stronie serwera, ale
 * kompilowanie się z nim przywiązałoby jara do konkretnej jego wersji i do konkretnego
 * wydania Minecrafta. Przez refleksję ten sam plik działa z każdą wersją, która wciąż
 * ma te metody, a gdy ich nie ma — mod mówi to graczowi zamiast się wywalić.
 *
 * <p>Cała robota jest tu, w jednym miejscu, żeby reszta moda nie wiedziała o istnieniu
 * refleksji ani o FabricTailorze.
 */
public final class Tailor {
    private static final String FETCHER = "org.samo_lego.fabrictailor.util.SkinFetcher";

    private Tailor() {}

    /** Tekstura skina: to, co Mojang podpisuje i czego oczekuje klient. */
    public record Texture(String value, String signature) {}

    private static Class<?> fetcher() throws ClassNotFoundException {
        return Class.forName(FETCHER);
    }

    /** Czy FabricTailor jest na serwerze. Bez niego mod nie ma czym zmieniać skinów. */
    public static boolean available() {
        try {
            fetcher();
            return true;
        } catch (Throwable t) {
            return false;
        }
    }

    // ── pobieranie tekstur ─────────────────────────────────────────────────
    // FabricTailor ma już gotowe pobieranie z Mojanga i wysyłkę na MineSkin.
    // Wołamy jego kod zamiast pisać własny: mniej kodu u nas, a użytkownik nie
    // musi zdobywać własnego klucza do MineSkina.

    /** Skin konta Minecraft o podanym nicku. */
    public static Optional<Texture> fromPlayerName(String name) {
        return invokeFetcher("fetchSkinByName", new Class<?>[]{String.class}, name);
    }

    /** Skin z pliku PNG (64x64 lub 64x32); wysyłany na MineSkin przez FabricTailor. */
    public static Optional<Texture> fromFile(Path png, boolean slim) {
        return invokeFetcher("setSkinFromFile",
                new Class<?>[]{String.class, boolean.class}, png.toAbsolutePath().toString(), slim);
    }

    /** Skin ze zdalnego PNG-a. */
    public static Optional<Texture> fromUrl(String url, boolean slim) {
        return invokeFetcher("fetchSkinByUrl", new Class<?>[]{String.class, boolean.class}, url, slim);
    }

    private static Optional<Texture> invokeFetcher(String method, Class<?>[] types, Object... args) {
        try {
            Method m = fetcher().getMethod(method, types);
            Object result = m.invoke(null, args);
            // Do FabricTailora 2.5.0 (ostatni na 1.21.1) SkinFetcher zwracał surowe
            // Property, od 2.6.0 zwraca Optional<Property>. Bez obsługi obu kształtów
            // ten sam jar cicho nie zakładałby skinów na 1.21.x poniżej 1.21.2.
            if (result instanceof Optional<?> opt) result = opt.orElse(null);
            return result == null ? Optional.empty() : readProperty(result);
        } catch (Throwable t) {
            SkinLibrary.LOG.warn("FabricTailor: {} nieosiągalne ({})", method, t.toString());
            return Optional.empty();
        }
    }

    /**
     * Wyciąga value i signature z com.mojang.authlib Property.
     *
     * <p>W nowszych wersjach authlib Property jest rekordem (value()), w starszych
     * zwykłą klasą (getValue()). Próbujemy obu, bo to jedyna różnica między nimi,
     * a ona sama decyduje, czy jar działa na starszym wydaniu Minecrafta.
     */
    private static Optional<Texture> readProperty(Object property) {
        String value = readString(property, "value", "getValue");
        String signature = readString(property, "signature", "getSignature");
        return value == null ? Optional.empty() : Optional.of(new Texture(value, signature));
    }

    private static String readString(Object target, String... names) {
        for (String name : names) {
            try {
                Object v = target.getClass().getMethod(name).invoke(target);
                if (v != null) return v.toString();
            } catch (Throwable ignored) {
                // próbujemy następnej nazwy — brak metody to normalny przypadek
            }
        }
        return null;
    }

    // ── zakładanie skina ───────────────────────────────────────────────────

    /**
     * Zakłada teksturę graczowi. Nazwa z prefiksem jest tą obowiązującą; wariant bez
     * prefiksu jest w FabricTailorze oznaczony jako przestarzały, więc trzymamy go
     * tylko jako awaryjny dla starszych instalacji.
     */
    public static boolean apply(ServerPlayer player, Texture texture) {
        for (String name : new String[]{"fabrictailor_setSkin", "setSkin"}) {
            try {
                Method m = player.getClass().getMethod(name, String.class, String.class, boolean.class);
                m.invoke(player, texture.value(), texture.signature(), true);
                return true;
            } catch (Throwable ignored) {
                // następna nazwa
            }
        }
        SkinLibrary.LOG.warn("Nie udało się założyć skina — czy FabricTailor jest zainstalowany?");
        return false;
    }
}
