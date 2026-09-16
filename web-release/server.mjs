import http from "node:http";
import { brotliDecompressSync } from "node:zlib";
import { readdirSync, readFileSync } from "node:fs";
import { join } from "node:path";
import { fileURLToPath } from "node:url";

const dir = fileURLToPath(new URL("./payload/", import.meta.url));
const encoded = readdirSync(dir).filter((name) => name.endsWith(".part")).sort().map((name) => readFileSync(join(dir, name), "utf8")).join("");
const html = brotliDecompressSync(Buffer.from(encoded, "base64"));
const port = Number(process.env.PORT || 3000);

const server = http.createServer((req, res) => {
  if (req.url === "/healthz") {
    res.writeHead(200, { "content-type": "application/json; charset=utf-8", "cache-control": "no-store" });
    return res.end(JSON.stringify({ ok: true, app: "KSEE FINAL · CACE Studio" }));
  }
  res.writeHead(200, {
    "content-type": "text/html; charset=utf-8",
    "cache-control": "public, max-age=300",
    "x-content-type-options": "nosniff",
    "referrer-policy": "strict-origin-when-cross-origin",
    "content-security-policy": "default-src 'self' data: blob:; img-src 'self' data: blob:; style-src 'self' 'unsafe-inline'; script-src 'self' 'unsafe-inline'; connect-src 'self'; font-src 'self' data:; object-src 'none'; base-uri 'self'; frame-ancestors 'self'"
  });
  res.end(html);
});

server.listen(port, "0.0.0.0", () => {
  console.log(`KSEE FINAL web release listening on ${port}`);
});
