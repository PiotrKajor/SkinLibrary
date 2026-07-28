package dev.kajor.skinlibrary;

import net.fabricmc.api.ModInitializer;
import net.fabricmc.fabric.api.command.v2.CommandRegistrationCallback;
import net.fabricmc.loader.api.FabricLoader;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.nio.file.Path;

public class SkinLibrary implements ModInitializer {
    public static final String ID = "skinlibrary";
    public static final Logger LOG = LoggerFactory.getLogger("SkinLibrary");

    private static Config config;
    private static Library library;

    public static Config config() {
        return config;
    }

    public static Library library() {
        return library;
    }

    @Override
    public void onInitialize() {
        Path katalog = FabricLoader.getInstance().getConfigDir().resolve(ID);

        config = Config.load(katalog);
        Lang.load(config.language, katalog);

        library = new Library(katalog, config);
        library.wczytajCache();
        library.reload();

        if (!Tailor.available()) {
            // Zależność jest zadeklarowana w fabric.mod.json, więc tu trafiamy tylko
            // przy wymuszonym starcie. Lepiej powiedzieć to wprost w logu, niż zostawić
            // gracza z komendą, która milczy.
            LOG.error("Nie widzę FabricTailora — komendy zadziałają, ale nie zmienią skina. "
                    + "Pobierz go z https://modrinth.com/mod/fabrictailor");
        }

        CommandRegistrationCallback.EVENT.register((dispatcher, registry, env) ->
                SkinCommand.register(dispatcher));

        LOG.info("SkinLibrary gotowa ({} skinów).", library.entries().size());
    }
}
