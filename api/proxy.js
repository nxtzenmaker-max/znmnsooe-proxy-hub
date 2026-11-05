const fs = require('fs');
const path = require('path');

let proxiesCache = null;

function getProxies() {
  if (!proxiesCache) {
    try {
      const pPath = path.join(process.cwd(), 'raw_proxies.json');
      const content = fs.readFileSync(pPath, 'utf8');
      proxiesCache = JSON.parse(content);
    } catch (e) {
      proxiesCache = [];
    }
  }
  return proxiesCache;
}

module.exports = (req, res) => {
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'GET, OPTIONS');
  if (req.method === 'OPTIONS') return res.status(200).end();

  const proxies = getProxies();
  if (!proxies || proxies.length === 0) {
    return res.status(503).json({ error: 'No proxies available' });
  }

  const { protocol, format } = req.query;
  let pool = proxies;
  if (protocol) {
    const pLower = protocol.toLowerCase();
    pool = proxies.filter(p => p.toLowerCase().startsWith(`${pLower}://`));
  }

  if (pool.length === 0) {
    return res.status(404).json({ error: `No proxies found for protocol: ${protocol}` });
  }

  const picked = pool[Math.floor(Math.random() * pool.length)];
  const proto = picked.split('://')[0];
  const hostPort = picked.split('://')[1] || '';
  const [ip, port] = hostPort.split(':');

  if (format === 'text') {
    res.setHeader('Content-Type', 'text/plain');
    return res.status(200).send(picked);
  }

  res.setHeader('Content-Type', 'application/json');
  return res.status(200).json({
    proxy: picked,
    protocol: proto,
    ip: ip,
    port: port,
    domain: 'znmnsooepay.store',
    total_in_pool: proxies.length
  });
};
