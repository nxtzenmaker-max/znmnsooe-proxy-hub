const fs = require('fs');
const path = require('path');

let statsCache = null;

module.exports = (req, res) => {
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'GET, OPTIONS');
  if (req.method === 'OPTIONS') return res.status(200).end();

  if (!statsCache) {
    try {
      const pPath = path.join(process.cwd(), 'raw_proxies.json');
      const list = JSON.parse(fs.readFileSync(pPath, 'utf8'));
      const protocols = {};
      list.forEach(p => {
        const proto = p.split('://')[0];
        protocols[proto] = (protocols[proto] || 0) + 1;
      });
      statsCache = {
        total: list.length,
        protocols
      };
    } catch (e) {
      statsCache = { total: 0, protocols: {} };
    }
  }

  res.setHeader('Content-Type', 'application/json');
  return res.status(200).json({
    status: 'online',
    service: 'ZnMnsooePay Rotating Proxy Network',
    domain: 'znmnsooepay.store',
    engine: "RJN's AI Balancer",
    total_proxies: statsCache.total,
    protocols: statsCache.protocols,
    features: [
      'Automatic rotation per request',
      'Protocol filtering (socks5, http, https, socks4)',
      '1-Click list export',
      'Instant failover'
    ]
  });
};
