package dev.kajor.skinlibrary;

import com.google.gson.JsonObject;
import com.google.gson.JsonParser;

import java.io.InputStream;
import java.io.InputStreamReader;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.HashMap;
import java.util.Map;

/**
 * Tłumaczenia po stronie serwera.
 *
 * <p>Dlaczego nie zwykłe Component.translatable: to mod serwerowy, a klucze tłumaczy
 * klient. Gracz bez tego moda zobaczyłby surowe "skinlibrary.msg.applied" zamiast zdania.
 * Dlatego składamy gotowy tekst tutaj i wysyłamy go jako zwykły literał.
 *
 * <p>Plik z tłumaczeniem można podłożyć w config/skinlibrary/lang/&lt;kod&gt;.json — wtedy
 * nadpisze wbudowany. Nowy język nie wymaga więc przebudowy moda.
 */
public final class Lang {
    private static final String WBUDOWANE = "/assets/skinlibrary/lang/%s.json";
    private static final String ZAPASOWY = "en_us";

    private static final Map<String, String> teksty = new HashMap<>();
    private static final Map<String, String> zapasowe = new HashMap<>();

    private Lang() {}

    static void load(String kod, Path katalogConfigu) {
        teksty.clear();
        zapasowe.clear();
        wczytajZJara(ZAPASOWY, zapasowe);

        Path wlasny = katalogConfigu.resolve("lang").resolve(kod + ".json");
        if (Files.isReadable(wlasny)) {
            try (var r = Files.newBufferedReader(wlasny, StandardCharsets.UTF_8)) {
                doMapy(JsonParser.parseReader(r).getAsJsonObject(), teksty);
                SkinLibrary.LOG.info("Wczytano własne tłumaczenie: {}", wlasny);
                return;
            } catch (Exception e) {
                SkinLibrary.LOG.warn("Nie udało się wczytać {} — używam wbudowanego. {}", wlasny, e.toString());
            }
        }
        wczytajZJara(kod, teksty);
    }

    private static void wczytajZJara(String kod, Map<String, String> cel) {
        String sciezka = String.format(WBUDOWANE, kod);
        try (InputStream in = Lang.class.getResourceAsStream(sciezka)) {
            if (in == null) {
                SkinLibrary.LOG.warn("Brak wbudowanego tłumaczenia {}", sciezka);
                return;
            }
            doMapy(JsonParser.parseReader(new InputStreamReader(in, StandardCharsets.UTF_8)).getAsJsonObject(), cel);
        } catch (Exception e) {
            SkinLibrary.LOG.warn("Błąd czytania {}: {}", sciezka, e.toString());
        }
    }

    private static void doMapy(JsonObject json, Map<String, String> cel) {
        json.entrySet().forEach(e -> cel.put(e.getKey(), e.getValue().getAsString()));
    }

    /**
     * Tekst dla klucza; {@code {0}}, {@code {1}}… są podmieniane na kolejne argumenty.
     *
     * <p>Podmiana jest ręczna, a nie przez MessageFormat, bo ten traktuje apostrof jako
     * znak sterujący — a w polskich i francuskich tłumaczeniach apostrofy wypadają
     * naturalnie i cicho zjadałyby nawiasy klamrowe.
     */
    public static String get(String klucz, Object... args) {
        String wzor = teksty.getOrDefault(klucz, zapasowe.getOrDefault(klucz, klucz));
        for (int i = 0; i < args.length; i++) {
            wzor = wzor.replace("{" + i + "}", String.valueOf(args[i]));
        }
        return wzor;
    }
}
