import { serve } from "bun";

// moneyflow REST server (see moneyflow/moneyflow/rest)
const REST_BASE = process.env.MONEYFLOW_REST_URL ?? "http://127.0.0.1:8000";
const PORT = Number(process.env.PORT ?? 3000);
const HOST = process.env.HOST ?? "127.0.0.1";
const PUBLIC_DIR = `${import.meta.dir}/public`;

const MIME: Record<string, string> = {
  ".html": "text/html; charset=utf-8",
  ".css": "text/css; charset=utf-8",
  ".js": "text/javascript; charset=utf-8",
  ".json": "application/json; charset=utf-8",
  ".svg": "image/svg+xml",
  ".png": "image/png",
  ".ico": "image/x-icon",
  ".woff2": "font/woff2",
};

const server = serve({
  hostname: HOST,
  port: PORT,

  async fetch(req) {
    const url = new URL(req.url);

    // ---- API proxy: /api/* -> moneyflow REST server ------------------------
    if (url.pathname.startsWith("/api/")) {
      const target = `${REST_BASE}${url.pathname.slice("/api".length)}${url.search}`;
      try {
        const upstream = await fetch(target, {
          method: req.method,
          headers: req.headers,
          body: req.method === "GET" || req.method === "HEAD" ? undefined : req.body,
        });
        const body = await upstream.arrayBuffer();
        return new Response(body, {
          status: upstream.status,
          headers: {
            "Content-Type": upstream.headers.get("Content-Type") ?? "application/json",
            "Cache-Control": "no-store",
          },
        });
      } catch (err) {
        return Response.json(
          {
            status: "error",
            message:
              "Could not reach the moneyflow REST server. Start it with: " +
              "uv run python -m moneyflow.rest (from the moneyflow repo).",
            detail: String(err),
          },
          { status: 502 },
        );
      }
    }

    // ---- Static files --------------------------------------------------------
    let pathname = url.pathname === "/" ? "/index.html" : url.pathname;
    pathname = decodeURIComponent(pathname).split("?")[0];

    // Prevent path traversal
    if (!pathname.startsWith("/")) pathname = "/" + pathname;

    const file = Bun.file(`${PUBLIC_DIR}${pathname}`);
    if (await file.exists()) {
      const ext = pathname.slice(pathname.lastIndexOf(".")).toLowerCase();
      return new Response(file, {
        headers: { "Content-Type": MIME[ext] ?? "application/octet-stream" },
      });
    }

    return new Response("Not Found", { status: 404 });
  },
});

console.log(`moneyflow dashboard: http://${HOST}:${server.port}`);
console.log(`proxying /api -> ${REST_BASE}`);
