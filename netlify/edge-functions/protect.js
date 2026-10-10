function deny() {
  return new Response(JSON.stringify({
    error: { code: 'unauthorized', message: 'Private demo credentials required.' },
  }), {
    status: 401,
    headers: {
      'WWW-Authenticate': 'Basic realm="RideEat demo"',
      'Content-Type': 'application/json',
      'Cache-Control': 'no-store',
    },
  });
}

function safeEqual(left, right) {
  const encoder = new TextEncoder();
  const a = encoder.encode(String(left));
  const b = encoder.encode(String(right));
  const size = Math.max(a.length, b.length, 1);
  let diff = a.length === b.length ? 0 : 1;
  for (let i = 0; i < size; i += 1) {
    diff |= (a[i] || 0) ^ (b[i] || 0);
  }
  return diff === 0;
}

function env(name) {
  if (typeof Netlify !== 'undefined' && Netlify.env && typeof Netlify.env.get === 'function') {
    return Netlify.env.get(name) || '';
  }
  return Deno.env.get(name) || '';
}

export default async (request, context) => {
  const user = env('DEMO_USERNAME');
  const pass = env('DEMO_PASSWORD');
  if (!user || !pass) {
    return deny();
  }
  const header = request.headers.get('authorization') || '';
  const match = /^Basic\s+(\S+)/i.exec(header);
  if (!match) {
    return deny();
  }
  let decoded = '';
  try {
    decoded = atob(match[1]);
  } catch (_error) {
    return deny();
  }
  const idx = decoded.indexOf(':');
  if (idx < 0 || !safeEqual(decoded.slice(0, idx), user) || !safeEqual(decoded.slice(idx + 1), pass)) {
    return deny();
  }
  return context.next();
};
