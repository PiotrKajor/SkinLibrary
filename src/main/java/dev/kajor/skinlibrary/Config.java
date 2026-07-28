package dev.kajor.skinlibrary;

import com.google.gson.Gson;
import com.google.gson.GsonBuilder;
import com.google.gson.JsonObject;
import com.google.gson.JsonParser;

import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;

/**
 * Ustawienia moda. Wszystko, co kiedykolwiek mogłoby być wpisane na sztywno w kodzie,
 * jest tutaj — z domyślnymi wartościami dobranymi tak, żeby świeżo wrzucony jar działał
 * bez zaglądania do configu.
 */
public final class Config {
    private static final Gson GSON = new GsonBuilder().setPrettyPrinting().create();

    /** Język komunikatów; plik z tłumaczeniem można też podłożyć w lang/. */
    public String language = "en_us";

    /** Czy wolno zakładać skin dowolnego konta Minecraft: /skin player &lt;nick&gt;. */
    public boolean allowPlayerSkins = true;

    /** Czy wolno zakładać skin z adresu URL: /skin url &lt;adres&gt;. */
    public boolean allowUrlSkins = true;

    /** Odstęp między zmianami skina przez jednego gracza (sekundy); 0 wyłącza. */
    public int cooldownSeconds = 5;

    /** Czy komendy wymagają uprawnień operatora. Domyślnie nie — to mod dla graczy. */
    public boolean requireOperator = false;

    /** Ile pozycji na stronie listy. */
    public int pageSize = 8;

    /** Czy skiny z plików traktować jako smukłe (Alex) zamiast klasycznych (Steve). */
    public boolean slimByDefault = false;

    /**
     * Opcjonalny katalog skinów po HTTP, zwracający {@code {"skins":[{"name":…}]}}.
     * Puste = biblioteka wyłącznie z plików lokalnych. Istnieje po to, żeby dało się
     * podpiąć własny serwis WWW, ale nikt nie musi go stawiać.
     */
    public String libraryUrl = "";

    /** Główne polecenie i jego skróty. Zmienialne, bo /skin bywa zajęte przez inny mod. */
    public String[] commandAliases = {"skin", "skins"};

    static Config load(Path katalog) {
        Path plik = katalog.resolve("config.json");
        Config cfg = new Config();
        if (Files.isReadable(plik)) {
            try (var r = Files.newBufferedReader(plik, StandardCharsets.UTF_8)) {
                JsonObject json = JsonParser.parseReader(r).getAsJsonObject();
                cfg = GSON.fromJson(json, Config.class);
                // Świeże pole w nowej wersji moda nie może wyzerować się do null/0
                // tylko dlatego, że stary plik go nie zawierał.
                cfg.uzupelnijBraki(json);
            } catch (Exception e) {
                SkinLibrary.LOG.error("Błąd w config.json — używam ustawień domyślnych. {}", e.toString());
                cfg = new Config();
            }
        }
        cfg.zapisz(plik);
        return cfg;
    }

    private void uzupelnijBraki(JsonObject json) {
        Config d = new Config();
        if (language == null) language = d.language;
        if (commandAliases == null || commandAliases.length == 0) commandAliases = d.commandAliases;
        if (libraryUrl == null) libraryUrl = d.libraryUrl;
        if (!json.has("pageSize") || pageSize <= 0) pageSize = d.pageSize;
        if (cooldownSeconds < 0) cooldownSeconds = d.cooldownSeconds;
    }

    private void zapisz(Path plik) {
        try {
            Files.createDirectories(plik.getParent());
            Files.writeString(plik, GSON.toJson(this), StandardCharsets.UTF_8);
        } catch (Exception e) {
            SkinLibrary.LOG.warn("Nie udało się zapisać {}: {}", plik, e.toString());
        }
    }
}
