import http from 'node:http';
import { createHash } from 'node:crypto';
import { createReadStream, existsSync, readFileSync, statSync } from 'node:fs';
import { extname, join, normalize, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const RELEASE = process.env.KSEE_RELEASE || '3.36.0-web.20260916';
const PORT = Number(process.env.PORT || 3000);
const REQUIRE_MONGO = process.env.REQUIRE_MONGO === 'true';
const MONGO_URL = process.env.MONGO_URL || '';
const MONGO_DB_NAME = process.env.MONGO_DB_NAME || 'ksee_final';
const DIST_DIR = resolve(fileURLToPath(new URL('../dist/', import.meta.url)));
const INDEX_PATH = join(DIST_DIR, 'index.html');

if (!existsSync(INDEX_PATH)) throw new Error(`Missing built frontend: ${INDEX_PATH}`);
const indexHtml = readFileSync(INDEX_PATH);
const indexSha256 = createHash('sha256').update(indexHtml).digest('hex');

let mongoClient = null;
let database = { configured: Boolean(MONGO_URL), connected: false, error: null };

async function connectMongo() {
  if (!MONGO_URL) {
    if (REQUIRE_MONGO) throw new Error('MONGO_URL is required when REQUIRE_MONGO=true');
    return;
  }
  try {
    const { MongoClient } = await import('mongodb');
    mongoClient = new MongoClient(MONGO_URL, { serverSelectionTimeoutMS: 5000 });
    await mongoClient.connect();
    const db = mongoClient.db(MONGO_DB_NAME);
    await db.command({ ping: 1 });
    await db.collection('deployments').updateOne(
      { _id: 'ksee-final-shell' },
      { $set: { release: RELEASE, indexSha256, bootedAt: new Date(), service: 'ksee-final-shell' } },
      { upsert: true },
    );
    database = { configured: true, connected: true, error: null };
  } catch (error) {
    database = { configured: true, connected: false, error: error instanceof Error ? error.message : String(error) };
    if (REQUIRE_MONGO) throw error;
  }
}

const securityHeaders = {
  'x-content-type-options': 'nosniff',
  'referrer-policy': 'strict-origin-when-cross-origin',
  'x-frame-options': 'SAMEORIGIN',
  'permissions-policy': 'camera=(), microphone=(), geolocation=()',
  'cross-origin-opener-policy': 'same-origin',
  'strict-transport-security': 'max-age=31536000; includeSubDomains',
  'content-security-policy': "default-src 'self' data: blob:; img-src 'self' data: blob:; style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; script-src 'self'; connect-src 'self'; font-src 'self' data: https://fonts.gstatic.com; object-src 'none'; base-uri 'self'; frame-ancestors 'self'",
};

const contentTypes = {
  '.css': 'text/css; charset=utf-8', '.js': 'text/javascript; charset=utf-8', '.mjs': 'text/javascript; charset=utf-8',
  '.json': 'application/json; charset=utf-8', '.svg': 'image/svg+xml', '.png': 'image/png', '.jpg': 'image/jpeg',
  '.jpeg': 'image/jpeg', '.webp': 'image/webp', '.ico': 'image/x-icon', '.woff2': 'font/woff2', '.txt': 'text/plain; charset=utf-8',
};

function sendJson(res, status, body) {
  res.writeHead(status, { ...securityHeaders, 'content-type': 'application/json; charset=utf-8', 'cache-control': 'no-store' });
  res.end(JSON.stringify(body));
}

function safeStaticPath(urlPath) {
  const decoded = decodeURIComponent((urlPath || '/').split('?')[0]);
  const cleaned = normalize(decoded).replace(/^(\.\.[/\\])+/, '').replace(/^[/\\]+/, '');
  const candidate = resolve(DIST_DIR, cleaned);
  return candidate.startsWith(`${DIST_DIR}/`) || candidate === DIST_DIR ? candidate : null;
}

await connectMongo();

const server = http.createServer((req, res) => {
  const healthy = !REQUIRE_MONGO || database.connected;
  if (req.url === '/healthz') {
    return sendJson(res, healthy ? 200 : 503, {
      ok: healthy,
      app: 'KSEE FINAL · CACE Studio',
      release: RELEASE,
      indexSha256,
      database: { configured: database.configured, connected: database.connected },
    });
  }
  if (req.url === '/api/status') {
    return sendJson(res, healthy ? 200 : 503, {
      ok: healthy,
      app: 'KSEE FINAL · CACE Studio',
      release: RELEASE,
      database: { configured: database.configured, connected: database.connected },
      evidenceNotice: 'Web runtime health does not confer formal proof qualification; proof status is exact-head and claim-specific.',
    });
  }

  const candidate = safeStaticPath(req.url);
  const filePath = candidate && existsSync(candidate) && statSync(candidate).isFile() ? candidate : INDEX_PATH;
  const isAsset = filePath !== INDEX_PATH;
  res.writeHead(200, {
    ...securityHeaders,
    'content-type': filePath === INDEX_PATH ? 'text/html; charset=utf-8' : (contentTypes[extname(filePath)] || 'application/octet-stream'),
    'cache-control': isAsset ? 'public, max-age=31536000, immutable' : 'no-cache',
  });
  createReadStream(filePath).pipe(res);
});

server.listen(PORT, '0.0.0.0', () => {
  console.log(`KSEE FINAL ${RELEASE} listening on ${PORT}; mongo=${database.connected ? 'connected' : 'not-connected'}`);
});

async function shutdown(signal) {
  console.log(`Received ${signal}; shutting down`);
  server.close(async () => {
    try { await mongoClient?.close(); } finally { process.exit(0); }
  });
  setTimeout(() => process.exit(1), 10000).unref();
}
process.on('SIGTERM', () => shutdown('SIGTERM'));
process.on('SIGINT', () => shutdown('SIGINT'));
