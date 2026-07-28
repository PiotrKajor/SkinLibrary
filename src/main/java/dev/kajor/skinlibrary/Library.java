package dev.kajor.skinlibrary;

import com.google.gson.Gson;
import com.google.gson.GsonBuilder;
import com.google.gson.JsonArray;
import com.google.gson.JsonObject;
import com.google.gson.JsonParser;

import java.io.InputStreamReader;
import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.time.Duration;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.stream.Stream;

/**
 * Biblioteka skinów: co jest do wyboru i skąd wziąć teksturę.
 *
 * <p>Wpisy pochodzą z trzech źródeł, w tej kolejności ważności: plików PNG wrzuconych do
 * katalogu skins/, pliku skins.json i — jeśli ktoś go skonfiguruje — zdalnego katalogu HTTP.
 * Domyślnie działa samo wrzucenie PNG do katalogu; reszta jest dla tych, którzy jej chcą.
 */
public final class Library {
    private static final Gson GSON = new GsonBuilder().setPrettyPrinting().create();
    private static final HttpClient HTTP = HttpClient.newBuilder()
            .connectTimeout(Duration.ofSeconds(5)).build();

    /** Skąd bierze się tekstura danego wpisu. */
    public enum Source { FILE, PLAYER, URL, TEXTURE }

    public record Entry(String name, Source source, String target, String author, boolean slim) {}

    private final Path katalog;
    private final Config cfg;
    private final Map<String, Wpis> cache = new HashMap<>();
    private volatile List<Entry> wpisy = List.of();

    /** Zapamiętana tekstura wraz ze znacznikiem, po którym poznamy, że jest nieaktualna. */
    private record Wpis(String value, String signature, long stempel) {}

    Library(Path katalog, Config cfg) {
        this.katalog = katalog;
        this.cfg = cfg;
    }

    public List<Entry> entries() {
        return wpisy;
    }

    public Optional<Entry> find(String nazwa) {
        return wpisy.stream().filter(e -> e.name().equalsIgnoreCase(nazwa)).findFirst();
    }

    // ── ładowanie listy ────────────────────────────────────────────────────

    /** Przeładowuje listę wpisów. Wołane przy starcie i przez /skin reload. */
    public void reload() {
        List<Entry> zebrane = new ArrayList<>();
        zPlikow(zebrane);
        zJsona(zebrane);
        zSieci(zebrane);
        zebrane.sort(Comparator.comparing((Entry e) -> e.author().toLowerCase())
                .thenComparing(e -> e.name().toLowerCase()));
        wpisy = List.copyOf(zebrane);
        SkinLibrary.LOG.info("Biblioteka skinów: {} pozycji.", wpisy.size());
    }

    private void zPlikow(List<Entry> cel) {
        Path skins = katalog.resolve("skins");
        try {
            Files.createDirectories(skins);
        } catch (Exception e) {
            SkinLibrary.LOG.warn("Nie mogę utworzyć {}: {}", skins, e.toString());
            return;
        }
        try (Stream<Path> s = Files.list(skins)) {
            s.filter(p -> p.getFileName().toString().toLowerCase().endsWith(".png"))
                    .forEach(p -> {
                        String nazwa = p.getFileName().toString();
                        nazwa = nazwa.substring(0, nazwa.length() - 4);
                        cel.add(new Entry(nazwa, Source.FILE, p.toAbsolutePath().toString(),
                                "local", cfg.slimByDefault));
                    });
        } catch (Exception e) {
            SkinLibrary.LOG.warn("Nie mogę przejrzeć {}: {}", skins, e.toString());
        }
    }

    private void zJsona(List<Entry> cel) {
        Path plik = katalog.resolve("skins.json");
        if (!Files.isReadable(plik)) return;
        try (var r = Files.newBufferedReader(plik, StandardCharsets.UTF_8)) {
            JsonObject root = JsonParser.parseReader(r).getAsJsonObject();
            for (var e : root.entrySet()) {
                JsonObject o = e.getValue().getAsJsonObject();
                String autor = tekst(o, "author", "library");
                boolean slim = o.has("slim") ? o.get("slim").getAsBoolean() : cfg.slimByDefault;
                if (o.has("player")) {
                    cel.add(new Entry(e.getKey(), Source.PLAYER, o.get("player").getAsString(), autor, slim));
                } else if (o.has("url")) {
                    cel.add(new Entry(e.getKey(), Source.URL, o.get("url").getAsString(), autor, slim));
                } else if (o.has("value")) {
                    // gotowa tekstura: value i podpis rozdzielone \n, bo Entry trzyma jeden String
                    cel.add(new Entry(e.getKey(), Source.TEXTURE,
                            o.get("value").getAsString() + "\n" + tekst(o, "signature", ""), autor, slim));
                } else if (o.has("file")) {
                    cel.add(new Entry(e.getKey(), Source.FILE,
                            katalog.resolve("skins").resolve(o.get("file").getAsString())
                                    .toAbsolutePath().toString(), autor, slim));
                }
            }
        } catch (Exception e) {
            SkinLibrary.LOG.error("Błąd w skins.json: {}", e.toString());
        }
    }

    private void zSieci(List<Entry> cel) {
        if (cfg.libraryUrl == null || cfg.libraryUrl.isBlank()) return;
        try {
            HttpRequest req = HttpRequest.newBuilder(URI.create(cfg.libraryUrl))
                    .timeout(Duration.ofSeconds(8)).GET().build();
            HttpResponse<String> resp = HTTP.send(req, HttpResponse.BodyHandlers.ofString());
            if (resp.statusCode() != 200) throw new RuntimeException("HTTP " + resp.statusCode());
            JsonArray arr = JsonParser.parseString(resp.body()).getAsJsonObject().getAsJsonArray("skins");
            for (int i = 0; i < arr.size(); i++) {
                JsonObject s = arr.get(i).getAsJsonObject();
                String nazwa = s.get("name").getAsString();
                String autor = tekst(s, "uploaded_by", tekst(s, "author", "remote"));
                if (s.has("value") && !s.get("value").isJsonNull()) {
                    cel.add(new Entry(nazwa, Source.TEXTURE,
                            s.get("value").getAsString() + "\n" + tekst(s, "signature", ""),
                            autor, cfg.slimByDefault));
                } else if (s.has("url")) {
                    cel.add(new Entry(nazwa, Source.URL, s.get("url").getAsString(), autor, cfg.slimByDefault));
                }
            }
        } catch (Exception e) {
            SkinLibrary.LOG.warn("Zdalny katalog {} niedostępny: {}", cfg.libraryUrl, e.toString());
        }
    }

    private static String tekst(JsonObject o, String klucz, String domyslny) {
        return o.has(klucz) && !o.get(klucz).isJsonNull() ? o.get(klucz).getAsString() : domyslny;
    }

    // ── tekstury ───────────────────────────────────────────────────────────

    /**
     * Tekstura dla wpisu. Wynik jest zapamiętywany, bo dla plików i adresów URL oznacza
     * wysyłkę na MineSkin — powtarzanie jej przy każdym /skin byłoby wolne i niegrzeczne
     * wobec cudzego serwisu.
     *
     * <p>Wołać z wątku pobocznego: robi żądania sieciowe.
     */
    public Optional<Tailor.Texture> texture(Entry wpis) {
        if (wpis.source() == Source.TEXTURE) {
            String[] cz = wpis.target().split("\n", 2);
            return Optional.of(new Tailor.Texture(cz[0], cz.length > 1 ? cz[1] : null));
        }

        long stempel = stempel(wpis);
        Wpis zapamietany = cache.get(klucz(wpis));
        if (zapamietany != null && zapamietany.stempel() == stempel) {
            return Optional.of(new Tailor.Texture(zapamietany.value(), zapamietany.signature()));
        }

        Optional<Tailor.Texture> tekstura = switch (wpis.source()) {
            case PLAYER -> Tailor.fromPlayerName(wpis.target());
            case URL -> Tailor.fromUrl(wpis.target(), wpis.slim());
            case FILE -> Tailor.fromFile(Path.of(wpis.target()), wpis.slim());
            case TEXTURE -> Optional.empty();   // obsłużone wyżej
        };

        tekstura.ifPresent(t -> {
            synchronized (cache) {
                cache.put(klucz(wpis), new Wpis(t.value(), t.signature(), stempel));
            }
            zapiszCache();
        });
        return tekstura;
    }

    private static String klucz(Entry wpis) {
        return wpis.source() + ":" + wpis.target();
    }

    /**
     * Znacznik unieważniający zapamiętaną teksturę. Dla pliku to czas modyfikacji — podmiana
     * PNG-a pod tą samą nazwą ma dać nowy skin, a nie stary z pamięci.
     */
    private static long stempel(Entry wpis) {
        if (wpis.source() != Source.FILE) return 0L;
        try {
            return Files.getLastModifiedTime(Path.of(wpis.target())).toMillis();
        } catch (Exception e) {
            return 0L;
        }
    }

    // ── trwałość pamięci podręcznej ────────────────────────────────────────

    void wczytajCache() {
        Path plik = katalog.resolve("cache.json");
        if (!Files.isReadable(plik)) return;
        try (var r = Files.newBufferedReader(plik, StandardCharsets.UTF_8)) {
            JsonObject root = JsonParser.parseReader(r).getAsJsonObject();
            for (var e : root.entrySet()) {
                JsonObject o = e.getValue().getAsJsonObject();
                cache.put(e.getKey(), new Wpis(o.get("value").getAsString(),
                        tekst(o, "signature", null), o.get("stamp").getAsLong()));
            }
        } catch (Exception e) {
            SkinLibrary.LOG.warn("Nie mogę wczytać cache.json: {}", e.toString());
        }
    }

    private void zapiszCache() {
        Path plik = katalog.resolve("cache.json");
        try {
            JsonObject root = new JsonObject();
            synchronized (cache) {
                cache.forEach((k, w) -> {
                    JsonObject o = new JsonObject();
                    o.addProperty("value", w.value());
                    if (w.signature() != null) o.addProperty("signature", w.signature());
                    o.addProperty("stamp", w.stempel());
                    root.add(k, o);
                });
            }
            Files.writeString(plik, GSON.toJson(root), StandardCharsets.UTF_8);
        } catch (Exception e) {
            SkinLibrary.LOG.warn("Nie mogę zapisać cache.json: {}", e.toString());
        }
    }
}
