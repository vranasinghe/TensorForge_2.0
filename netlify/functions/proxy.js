'use strict';

const crypto = require('crypto');

const ALLOWED = /^(health|import|predict(?:\/batch)?|batch\/jobs(?:\/[a-f0-9-]+(?:\/results)?)?)$/;
const PROXY_LIMIT = 6 * 1024 * 1024;

function timingSafeEqualString(left, right) {
  const a = Buffer.from(String(left));
  const b = Buffer.from(String(right));
  const size = Math.max(a.length, b.length, 1);
  const paddedA = Buffer.alloc(size);
  const paddedB = Buffer.alloc(size);
  a.copy(paddedA);
  b.copy(paddedB);
  return crypto.timingSafeEqual(paddedA, paddedB) && a.length === b.length;
}

function json(statusCode, payload, extraHeaders) {
  return {
    statusCode,
    headers: Object.assign({ 'Content-Type': 'application/json' }, extraHeaders || {}),
    body: JSON.stringify(payload),
  };
}

function unauthorized() {
  return json(401, { error: { code: 'unauthorized', message: 'Private demo credentials required.' } }, {
    'WWW-Authenticate': 'Basic realm="RideEat demo"',
  });
}

function header(event, name) {
  const headers = event.headers || {};
  const wanted = name.toLowerCase();
  const key = Object.keys(headers).find((item) => item.toLowerCase() === wanted);
  return key ? headers[key] : '';
}

function authorized(event) {
  const user = process.env.DEMO_USERNAME || '';
  const pass = process.env.DEMO_PASSWORD || '';
  if (!user || !pass) {
    return false;
  }
  const match = /^Basic\s+(\S+)/i.exec(header(event, 'authorization'));
  if (!match) {
    return false;
  }
  let decoded;
  try {
    decoded = Buffer.from(match[1], 'base64').toString('utf8');
  } catch (_error) {
    return false;
  }
  const idx = decoded.indexOf(':');
  if (idx < 0) {
    return false;
  }
  return timingSafeEqualString(decoded.slice(0, idx), user) && timingSafeEqualString(decoded.slice(idx + 1), pass);
}

function apiPath(event) {
  const raw = event.path || '';
  return raw
    .replace(/^\/\.netlify\/functions\/proxy\/?/, '')
    .replace(/^\/api\/?/, '')
    .replace(/\/$/, '');
}

function requestBody(event) {
  if (event.body == null || event.body === '') {
    return Buffer.alloc(0);
  }
  return event.isBase64Encoded ? Buffer.from(event.body, 'base64') : Buffer.from(event.body);
}

function parseCsv(text) {
  const source = String(text).replace(/^\uFEFF/, '');
  const rows = [];
  let row = [];
  let field = '';
  let inQuotes = false;
  for (let i = 0; i < source.length; i += 1) {
    const char = source[i];
    if (inQuotes) {
      if (char === '"') {
        if (source[i + 1] === '"') {
          field += '"';
          i += 1;
        } else {
          inQuotes = false;
        }
      } else {
        field += char;
      }
      continue;
    }
    if (char === '"') {
      inQuotes = true;
      continue;
    }
    if (char === ',') {
      row.push(field);
      field = '';
      continue;
    }
    if (char === '\n' || char === '\r') {
      if (char === '\r' && source[i + 1] === '\n') {
        i += 1;
      }
      row.push(field);
      field = '';
      if (row.some((value) => value !== '')) {
        rows.push(row);
      }
      row = [];
      continue;
    }
    field += char;
  }
  if (field !== '' || row.length) {
    row.push(field);
    if (row.some((value) => value !== '')) {
      rows.push(row);
    }
  }
  return rows;
}

function importTickets(raw) {
  const rows = parseCsv(raw);
  if (!rows.length) {
    throw new Error('CSV has no tickets.');
  }
  const headers = rows[0].map((name) => name.trim());
  const needed = ['ticket_id', 'channel', 'text'];
  if (!needed.every((name) => headers.includes(name))) {
    throw new Error('CSV needs ticket_id, channel and text columns.');
  }
  const tickets = [];
  for (const values of rows.slice(1)) {
    const record = {};
    headers.forEach((name, index) => {
      record[name] = values[index] == null ? '' : values[index];
    });
    tickets.push({
      ticket_id: record.ticket_id,
      channel: record.channel,
      text: record.text,
      subject: record.subject || '',
    });
    if (tickets.length > 5000) {
      throw new Error('CSV must contain at most 5,000 tickets.');
    }
  }
  if (!tickets.length) {
    throw new Error('CSV has no tickets.');
  }
  return tickets;
}

async function proxyBackend(event, path, body) {
  const backend = (process.env.BACKEND_URL || '').replace(/\/$/, '');
  const key = process.env.API_KEY || '';
  if (!key) {
    return json(503, { error: { message: 'Demo backend credential is not configured.' } });
  }
  if (!backend) {
    return json(503, { error: { message: 'Demo backend URL is not configured.' } });
  }
  const query = event.rawQuery ? `?${event.rawQuery}` : '';
  const headers = {
    'X-API-Key': key,
    'Content-Type': header(event, 'content-type') || 'application/json',
  };
  const requestId = header(event, 'x-request-id');
  if (requestId) {
    headers['X-Request-ID'] = requestId;
  }
  const method = event.httpMethod || 'GET';
  let response;
  try {
    response = await fetch(`${backend}/${path}${query}`, {
      method,
      headers,
      body: ['GET', 'HEAD', 'DELETE'].includes(method) ? undefined : body,
      redirect: 'manual',
    });
  } catch (_error) {
    return json(502, { error: { message: 'Backend unavailable. Check that the API is running.' } });
  }
  const forwarded = {};
  for (const name of ['content-type', 'retry-after', 'location']) {
    const value = response.headers.get(name);
    if (value) {
      forwarded[name] = value;
    }
  }
  const payload = Buffer.from(await response.arrayBuffer());
  return {
    statusCode: response.status,
    headers: forwarded,
    body: payload.toString('base64'),
    isBase64Encoded: true,
  };
}

exports.handler = async (event) => {
  if (!authorized(event)) {
    return unauthorized();
  }
  const path = apiPath(event);
  if (!ALLOWED.test(path)) {
    return json(404, { error: { message: 'Unknown demo operation.' } });
  }
  const body = requestBody(event);
  if (body.length > PROXY_LIMIT) {
    return json(413, { error: { message: 'Payload exceeds the Netlify demo proxy limit of 6 MB. Call the Render API directly for larger batches.' } });
  }
  if (path === 'import') {
    try {
      return json(200, { tickets: importTickets(body.toString('utf8')) });
    } catch (error) {
      return json(422, { error: { message: error.message } });
    }
  }
  return proxyBackend(event, path, body);
};

function selfTest() {
  const failures = [];
  const check = (name, ok) => {
    if (!ok) {
      failures.push(name);
    }
  };
  check('health allowed', ALLOWED.test('health'));
  check('predict allowed', ALLOWED.test('predict'));
  check('predict batch allowed', ALLOWED.test('predict/batch'));
  check('job status allowed', ALLOWED.test('batch/jobs/01234567-89ab-cdef-0123-456789abcdef'));
  check('job results allowed', ALLOWED.test('batch/jobs/01234567-89ab-cdef-0123-456789abcdef/results'));
  check('import allowed', ALLOWED.test('import'));
  check('escape rejected', !ALLOWED.test('../escape'));
  check('unknown rejected', !ALLOWED.test('admin'));
  check('path rewrite function', apiPath({ path: '/.netlify/functions/proxy/predict/batch' }) === 'predict/batch');
  check('path rewrite api', apiPath({ path: '/api/health' }) === 'health');
  const tickets = importTickets('ticket_id,channel,subject,text\na,chat,,"Tamil தமிழ்\nsecond line"\n');
  check('csv ticket count', tickets.length === 1);
  check('csv multiline text', tickets[0].text === 'Tamil தமிழ்\nsecond line');
  check('csv subject empty', tickets[0].subject === '');
  try {
    importTickets('bad,columns\n');
    check('csv bad headers', false);
  } catch (error) {
    check('csv bad headers', /ticket_id/.test(error.message));
  }
  if (failures.length) {
    console.error(`proxy self-test failed: ${failures.join(', ')}`);
    process.exit(1);
  }
  console.log('proxy self-test passed');
}

if (require.main === module && process.argv.includes('--self-test')) {
  selfTest();
}

exports.apiPath = apiPath;
exports.importTickets = importTickets;
exports.ALLOWED = ALLOWED;
