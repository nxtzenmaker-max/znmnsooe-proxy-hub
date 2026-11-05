const fs = require('fs');
const path = require('path');

module.exports = (req, res) => {
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Content-Type', 'text/plain; charset=utf-8');

  try {
    const pPath = path.join(process.cwd(), 'raw_proxies.json');
    const list = JSON.parse(fs.readFileSync(pPath, 'utf8'));
    const { protocol } = req.query;

    let pool = list;
    if (protocol) {
      const pLower = protocol.toLowerCase();
      pool = list.filter(p => p.toLowerCase().startsWith(`${pLower}://`));
    }

    return res.status(200).send(pool.join('\n'));
  } catch (e) {
    return res.status(500).send('Error loading proxies');
  }
};
