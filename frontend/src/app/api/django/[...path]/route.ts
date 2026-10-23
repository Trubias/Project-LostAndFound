import { NextRequest } from 'next/server';

const backend = process.env.DJANGO_URL ?? 'http://127.0.0.1:8000';

async function forward(request: NextRequest, path: string[]) {
  const target = `${backend}/${path.join('/')}/${request.nextUrl.search}`;
  const headers = new Headers(request.headers);
  headers.delete('connection');
  // Keep Django's configured host for ALLOWED_HOSTS validation and pass the
  // browser's public origin so CSRF_TRUSTED_ORIGINS can validate the frontend.
  headers.delete('host');
  const frontendOrigin = request.headers.get('origin')
    ?? `${request.nextUrl.protocol}//${request.headers.get('host') ?? request.nextUrl.host}`;
  headers.set('origin', frontendOrigin);
  // Password-reset emails must contain a link back to the public Next.js page.
  // The frontend host is already validated by Django's ALLOWED_HOSTS setting.
  if (path[0] === 'password-reset') headers.set('host', request.nextUrl.host);
  const response = await fetch(target, {
    method: request.method,
    headers,
    body: request.method === 'GET' || request.method === 'HEAD' ? undefined : await request.arrayBuffer(),
    redirect: 'manual',
  });

  const outHeaders = new Headers();
  for (const name of ['content-type', 'content-disposition', 'location', 'cache-control']) {
    const value = response.headers.get(name);
    if (value) outHeaders.set(name, value);
  }
  for (const cookie of response.headers.getSetCookie()) outHeaders.append('set-cookie', cookie);
  return new Response(response.body, { status: response.status, headers: outHeaders });
}

type RouteContext = { params: Promise<{ path: string[] }> };
export async function POST(request: NextRequest, context: RouteContext) {
  const { path } = await context.params;
  return forward(request, path);
}

export async function GET(request: NextRequest, context: RouteContext) {
  const { path } = await context.params;
  return forward(request, path);
}
