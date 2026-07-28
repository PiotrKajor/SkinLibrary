package dev.kajor.skinlibrary;

import com.mojang.brigadier.CommandDispatcher;
import com.mojang.brigadier.arguments.IntegerArgumentType;
import com.mojang.brigadier.arguments.StringArgumentType;
import com.mojang.brigadier.builder.LiteralArgumentBuilder;
import com.mojang.brigadier.context.CommandContext;
import com.mojang.brigadier.suggestion.SuggestionProvider;
import net.minecraft.ChatFormatting;
import net.minecraft.commands.CommandSourceStack;
import net.minecraft.commands.Commands;
import net.minecraft.network.chat.Component;
import net.minecraft.network.chat.MutableComponent;
import net.minecraft.network.chat.Style;
import net.minecraft.server.MinecraftServer;
import net.minecraft.server.level.ServerPlayer;

import java.util.ArrayList;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.Set;
import java.util.UUID;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.ThreadLocalRandom;

/** Komendy gracza. Wszystkie teksty idą przez Lang, wszystkie limity — przez Config. */
public final class SkinCommand {
    private static final Map<UUID, Long> ostatniaZmiana = new ConcurrentHashMap<>();

    private SkinCommand() {}

    public static void register(CommandDispatcher<CommandSourceStack> dispatcher) {
        for (String alias : SkinLibrary.config().commandAliases) {
            dispatcher.register(drzewo(alias));
        }
    }

    private static final SuggestionProvider<CommandSourceStack> PODPOWIEDZ_NAZWY = (ctx, b) -> {
        String pisane = b.getRemainingLowerCase();
        for (Library.Entry e : SkinLibrary.library().entries()) {
            if (e.name().toLowerCase().startsWith(pisane)) b.suggest(e.name());
        }
        return b.buildFuture();
    };

    private static final SuggestionProvider<CommandSourceStack> PODPOWIEDZ_AUTORZY = (ctx, b) -> {
        String pisane = b.getRemainingLowerCase();
        Set<String> widziane = new LinkedHashSet<>();
        for (Library.Entry e : SkinLibrary.library().entries()) {
            if (e.author().toLowerCase().startsWith(pisane) && widziane.add(e.author().toLowerCase())) {
                b.suggest(e.author());
            }
        }
        return b.buildFuture();
    };

    private static LiteralArgumentBuilder<CommandSourceStack> drzewo(String alias) {
        LiteralArgumentBuilder<CommandSourceStack> root = Commands.literal(alias);
        if (SkinLibrary.config().requireOperator) {
            root.requires(src -> src.hasPermission(2));
        }

        root.executes(ctx -> lista(ctx, null, 1))
                .then(Commands.literal("list")
                        .executes(ctx -> lista(ctx, null, 1))
                        .then(Commands.argument("page", IntegerArgumentType.integer(1))
                                .executes(ctx -> lista(ctx, null, IntegerArgumentType.getInteger(ctx, "page"))))
                        .then(Commands.argument("author", StringArgumentType.word()).suggests(PODPOWIEDZ_AUTORZY)
                                .executes(ctx -> lista(ctx, StringArgumentType.getString(ctx, "author"), 1))
                                .then(Commands.argument("page", IntegerArgumentType.integer(1))
                                        .executes(ctx -> lista(ctx, StringArgumentType.getString(ctx, "author"),
                                                IntegerArgumentType.getInteger(ctx, "page"))))))
                .then(Commands.literal("random").executes(SkinCommand::losowy))
                .then(Commands.literal("reset").executes(SkinCommand::reset))
                .then(Commands.literal("reload")
                        .requires(src -> src.hasPermission(2))
                        .executes(SkinCommand::przeladuj));

        if (SkinLibrary.config().allowPlayerSkins) {
            root.then(Commands.literal("player")
                    .then(Commands.argument("name", StringArgumentType.word())
                            .executes(ctx -> zGracza(ctx, StringArgumentType.getString(ctx, "name")))));
        }
        if (SkinLibrary.config().allowUrlSkins) {
            root.then(Commands.literal("url")
                    .then(Commands.argument("address", StringArgumentType.greedyString())
                            .executes(ctx -> zUrl(ctx, StringArgumentType.getString(ctx, "address")))));
        }

        // Na końcu, żeby literały (list/random/reset/…) miały pierwszeństwo nad nazwą skina.
        root.then(Commands.argument("name", StringArgumentType.word()).suggests(PODPOWIEDZ_NAZWY)
                .executes(ctx -> zBiblioteki(ctx, StringArgumentType.getString(ctx, "name"))));
        return root;
    }

    // ── pomocnicze ─────────────────────────────────────────────────────────

    private static ServerPlayer gracz(CommandContext<CommandSourceStack> ctx) {
        try {
            return ctx.getSource().getPlayerOrException();
        } catch (Exception e) {
            ctx.getSource().sendFailure(tekst("msg.players_only", ChatFormatting.RED));
            return null;
        }
    }

    private static MutableComponent tekst(String klucz, ChatFormatting kolor, Object... args) {
        return Component.literal(Lang.get(klucz, args)).withStyle(kolor);
    }

    private static void powiedz(MinecraftServer server, ServerPlayer gracz, MutableComponent tresc) {
        server.execute(() -> gracz.sendSystemMessage(tresc));
    }

    /** Czy gracz nie zmienia skina za często. Zwraca 0, gdy wolno, albo pozostałe sekundy. */
    private static long odczekaj(ServerPlayer gracz) {
        int limit = SkinLibrary.config().cooldownSeconds;
        if (limit <= 0) return 0;
        long teraz = System.currentTimeMillis();
        long ostatnio = ostatniaZmiana.getOrDefault(gracz.getUUID(), 0L);
        long minelo = (teraz - ostatnio) / 1000;
        return minelo >= limit ? 0 : limit - minelo;
    }

    /** Wspólne dla wszystkich źródeł: pobierz teksturę w tle, załóż na wątku serwera. */
    private static void zaloz(ServerPlayer gracz, MinecraftServer server,
                             java.util.function.Supplier<Optional<Tailor.Texture>> pobierz,
                             String kluczSukcesu, Object... args) {
        long zostalo = odczekaj(gracz);
        if (zostalo > 0) {
            gracz.sendSystemMessage(tekst("msg.cooldown", ChatFormatting.YELLOW, zostalo));
            return;
        }
        ostatniaZmiana.put(gracz.getUUID(), System.currentTimeMillis());

        new Thread(() -> {
            Optional<Tailor.Texture> tekstura;
            try {
                tekstura = pobierz.get();
            } catch (Exception e) {
                SkinLibrary.LOG.warn("Pobieranie skina nie powiodło się: {}", e.toString());
                tekstura = Optional.empty();
            }
            if (tekstura.isEmpty()) {
                // Nieudana próba nie ma blokować kolejnej — zwalniamy licznik.
                ostatniaZmiana.remove(gracz.getUUID());
                powiedz(server, gracz, tekst("msg.fetch_failed", ChatFormatting.RED));
                return;
            }
            final Tailor.Texture t = tekstura.get();
            server.execute(() -> gracz.sendSystemMessage(Tailor.apply(gracz, t)
                    ? tekst(kluczSukcesu, ChatFormatting.GREEN, args)
                    : tekst("msg.no_tailor", ChatFormatting.RED)));
        }, "skinlibrary-apply").start();
    }

    // ── komendy ────────────────────────────────────────────────────────────

    private static int zBiblioteki(CommandContext<CommandSourceStack> ctx, String nazwa) {
        ServerPlayer gracz = gracz(ctx);
        if (gracz == null || gracz.getServer() == null) return 0;
        Optional<Library.Entry> wpis = SkinLibrary.library().find(nazwa);
        if (wpis.isEmpty()) {
            gracz.sendSystemMessage(tekst("msg.unknown_skin", ChatFormatting.RED, nazwa));
            return 0;
        }
        zaloz(gracz, gracz.getServer(),
                () -> SkinLibrary.library().texture(wpis.get()), "msg.applied", wpis.get().name());
        return 1;
    }

    private static int zGracza(CommandContext<CommandSourceStack> ctx, String nick) {
        ServerPlayer gracz = gracz(ctx);
        if (gracz == null || gracz.getServer() == null) return 0;
        zaloz(gracz, gracz.getServer(), () -> Tailor.fromPlayerName(nick), "msg.applied", nick);
        return 1;
    }

    private static int zUrl(CommandContext<CommandSourceStack> ctx, String adres) {
        ServerPlayer gracz = gracz(ctx);
        if (gracz == null || gracz.getServer() == null) return 0;
        if (!adres.startsWith("http://") && !adres.startsWith("https://")) {
            gracz.sendSystemMessage(tekst("msg.bad_url", ChatFormatting.RED));
            return 0;
        }
        zaloz(gracz, gracz.getServer(),
                () -> Tailor.fromUrl(adres, SkinLibrary.config().slimByDefault), "msg.applied_url");
        return 1;
    }

    private static int losowy(CommandContext<CommandSourceStack> ctx) {
        ServerPlayer gracz = gracz(ctx);
        if (gracz == null || gracz.getServer() == null) return 0;
        List<Library.Entry> wszystkie = SkinLibrary.library().entries();
        if (wszystkie.isEmpty()) {
            gracz.sendSystemMessage(tekst("msg.empty_library", ChatFormatting.GRAY));
            return 0;
        }
        Library.Entry wpis = wszystkie.get(ThreadLocalRandom.current().nextInt(wszystkie.size()));
        zaloz(gracz, gracz.getServer(),
                () -> SkinLibrary.library().texture(wpis), "msg.applied", wpis.name());
        return 1;
    }

    private static int reset(CommandContext<CommandSourceStack> ctx) {
        ServerPlayer gracz = gracz(ctx);
        if (gracz == null || gracz.getServer() == null) return 0;
        // Skin własnego konta bierzemy po nicku — ta sama droga, co /skin player.
        zaloz(gracz, gracz.getServer(),
                () -> Tailor.fromPlayerName(gracz.getGameProfile().getName()), "msg.reset");
        return 1;
    }

    private static int przeladuj(CommandContext<CommandSourceStack> ctx) {
        SkinLibrary.library().reload();
        ctx.getSource().sendSuccess(() -> tekst("msg.reloaded", ChatFormatting.GREEN,
                SkinLibrary.library().entries().size()), true);
        return 1;
    }

    // ── lista ──────────────────────────────────────────────────────────────

    private static int lista(CommandContext<CommandSourceStack> ctx, String autor, int strona) {
        ServerPlayer gracz = gracz(ctx);
        if (gracz == null) return 0;

        List<Library.Entry> wybrane = new ArrayList<>();
        for (Library.Entry e : SkinLibrary.library().entries()) {
            if (autor == null || e.author().equalsIgnoreCase(autor)) wybrane.add(e);
        }
        if (wybrane.isEmpty()) {
            gracz.sendSystemMessage(tekst(autor != null ? "msg.no_skins_by" : "msg.empty_library",
                    ChatFormatting.GRAY, autor));
            return 0;
        }

        int rozmiar = SkinLibrary.config().pageSize;
        int stron = Math.max(1, (wybrane.size() + rozmiar - 1) / rozmiar);
        int p = Math.min(Math.max(strona, 1), stron);
        int od = (p - 1) * rozmiar;
        int doo = Math.min(od + rozmiar, wybrane.size());

        gracz.sendSystemMessage(Component.literal(
                        Lang.get("msg.header", p, stron, wybrane.size()))
                .withStyle(ChatFormatting.AQUA, ChatFormatting.BOLD));

        String poprzedniAutor = null;
        for (int i = od; i < doo; i++) {
            Library.Entry e = wybrane.get(i);
            if (autor == null && !e.author().equals(poprzedniAutor)) {
                poprzedniAutor = e.author();
                gracz.sendSystemMessage(Component.literal("» " + poprzedniAutor).withStyle(ChatFormatting.YELLOW));
            }
            gracz.sendSystemMessage(Component.literal("   ▸ " + e.name()).withStyle(st -> {
                Style s = st.withColor(ChatFormatting.GREEN);
                s = ChatCompat.runCommand(s, "/" + SkinLibrary.config().commandAliases[0] + " " + e.name());
                return ChatCompat.showText(s, Component.literal(Lang.get("msg.click_to_wear", e.name())));
            }));
        }

        MutableComponent nawigacja = Component.empty();
        if (p > 1) nawigacja.append(przycisk(Lang.get("msg.prev"), komendaListy(autor, p - 1)));
        if (p > 1 && p < stron) nawigacja.append(Component.literal("    "));
        if (p < stron) nawigacja.append(przycisk(Lang.get("msg.next"), komendaListy(autor, p + 1)));
        if (p > 1 || p < stron) gracz.sendSystemMessage(nawigacja);

        String alias = "/" + SkinLibrary.config().commandAliases[0];
        gracz.sendSystemMessage(Component.empty()
                .append(przycisk(Lang.get("msg.random"), alias + " random"))
                .append(Component.literal("  "))
                .append(przycisk(Lang.get("msg.own_skin"), alias + " reset")));
        return 1;
    }

    private static String komendaListy(String autor, int strona) {
        String alias = "/" + SkinLibrary.config().commandAliases[0];
        return autor == null ? alias + " list " + strona : alias + " list " + autor + " " + strona;
    }

    private static MutableComponent przycisk(String napis, String komenda) {
        return Component.literal("[" + napis + "]").withStyle(st -> {
            Style s = st.withColor(ChatFormatting.GOLD);
            s = ChatCompat.runCommand(s, komenda);
            return ChatCompat.showText(s, Component.literal(komenda));
        });
    }
}
