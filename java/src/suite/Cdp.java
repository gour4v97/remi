package suite;

import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.WebSocket;
import java.nio.charset.StandardCharsets;
import java.time.Duration;
import java.util.ArrayList;
import java.util.List;
import java.util.concurrent.CompletableFuture;
import java.util.concurrent.CompletionStage;
import java.util.concurrent.TimeUnit;

/** Chrome DevTools Protocol client (Edge/Chrome) on java.net.http. */
public final class Cdp {
    private Cdp() {}

    private static final HttpClient HTTP = HttpClient.newBuilder()
            .connectTimeout(Duration.ofSeconds(3)).build();

    public record Tab(String id, String title, String url, String wsUrl) {}

    public static boolean isUp(int port) {
        try {
            var resp = HTTP.send(req(port, "/json/version", "GET", null),
                    java.net.http.HttpResponse.BodyHandlers.ofString(StandardCharsets.UTF_8));
            return resp.statusCode() == 200;
        } catch (Exception e) {
            return false;
        }
    }

    public static String findBrowserExe() {
        String[] candidates = {
                "C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe",
                "C:\\Program Files\\Microsoft\\Edge\\Application\\msedge.exe",
                "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe",
                "C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe",
                System.getenv("LOCALAPPDATA") + "\\Google\\Chrome\\Application\\chrome.exe",
        };
        for (String c : candidates) {
            if (java.nio.file.Files.exists(java.nio.file.Path.of(c))) return c;
        }
        return null;
    }

    public static boolean launch(String exe, int port, String profileDir, int waitS) {
        try {
            List<String> args = new ArrayList<>(List.of(exe, "--remote-debugging-port=" + port));
            if (profileDir != null) {
                java.nio.file.Files.createDirectories(java.nio.file.Path.of(profileDir));
                args.add("--user-data-dir=" + profileDir);
                args.add("--no-first-run");
                args.add("--no-default-browser-check");
            } else {
                args.add("--restore-last-session");
            }
            new ProcessBuilder(args).start();
        } catch (Exception e) {
            return false;
        }
        long deadline = System.currentTimeMillis() + waitS * 1000L;
        while (System.currentTimeMillis() < deadline) {
            if (isUp(port)) return true;
            try {
                Thread.sleep(300);
            } catch (InterruptedException e) {
                return false;
            }
        }
        return false;
    }

    public static List<Tab> tabs(int port) throws Exception {
        String body = HTTP.send(req(port, "/json", "GET", null), java.net.http.HttpResponse.BodyHandlers.ofString(StandardCharsets.UTF_8)).body();
        List<Tab> out = new ArrayList<>();
        // minimal JSON array walk (no library): find objects with type=page + webSocketDebuggerUrl
        for (String obj : body.split("\\{")) {
            if (!obj.contains("\"type\": \"page\"") && !obj.contains("\"type\":\"page\"")) continue;
            String ws = extractStr(obj, "webSocketDebuggerUrl");
            if (ws == null || !ws.contains("/devtools/page/")) continue;
            out.add(new Tab(extractStr(obj, "id"), extractStr(obj, "title"),
                    extractStr(obj, "url"), ws));
        }
        return out;
    }

    public static void newTab(int port, String url) throws Exception {
        HTTP.send(req(port, "/json/new?" + java.net.URLEncoder.encode(url, StandardCharsets.UTF_8),
                "PUT", null), java.net.http.HttpResponse.BodyHandlers.discarding());
    }

    public static void activateTab(int port, String id) throws Exception {
        HTTP.send(req(port, "/json/activate/" + id, "GET", null), java.net.http.HttpResponse.BodyHandlers.discarding());
    }

    public static void closeTab(int port, String id) throws Exception {
        HTTP.send(req(port, "/json/close/" + id, "GET", null), java.net.http.HttpResponse.BodyHandlers.discarding());
    }

    /** Runtime.evaluate over WebSocket in the most recently active page; returns result.value. */
    public static String evalJs(int port, String js) throws Exception {
        List<Tab> pages = tabs(port);
        if (pages.isEmpty()) return null;
        CompletableFuture<String> done = new CompletableFuture<>();
        StringBuilder acc = new StringBuilder();
        WebSocket ws = HttpClient.newHttpClient().newWebSocketBuilder()
                .connectTimeout(Duration.ofSeconds(6))
                .buildAsync(URI.create(pages.get(0).wsUrl()), new WebSocket.Listener() {
                    @Override
                    public CompletionStage<?> onText(WebSocket webSocket, CharSequence data, boolean last) {
                        acc.append(data);
                        if (last) {
                            String text = acc.toString();
                            acc.setLength(0);
                            if (text.contains("\"id\":1")) done.complete(text);
                        }
                        webSocket.request(1);
                        return null;
                    }
                }).join();

        String payload = "{\"id\":1,\"method\":\"Runtime.evaluate\",\"params\":{"
                + "\"expression\":\"" + History.escape(js) + "\",\"returnByValue\":true,\"awaitPromise\":true}}";
        try {
            ws.sendText(payload, true).get(6, TimeUnit.SECONDS);
            String resp = done.get(6, TimeUnit.SECONDS);
            String value = extractStr(resp, "value");
            if (value != null) return value;
            if (resp.contains("\"description\"")) return extractStr(resp, "description");
            return "ok";
        } finally {
            ws.sendClose(WebSocket.NORMAL_CLOSURE, "bye");
        }
    }

    private static HttpRequest req(int port, String path, String method, String body) {
        var b = HttpRequest.newBuilder(URI.create("http://127.0.0.1:" + port + path));
        b.header("Content-Type", "application/json");
        return b.method(method, body == null
                ? HttpRequest.BodyPublishers.noBody()
                : HttpRequest.BodyPublishers.ofString(body)).build();
    }

    static String extractStr(String json, String key) {
        var m = java.util.regex.Pattern.compile("\"" + key + "\"\\s*:\\s*\"((?:[^\"\\\\]|\\\\.)*)\"")
                .matcher(json);
        return m.find() ? m.group(1).replace("\\/", "/").replace("\\\\", "\\") : null;
    }

}
