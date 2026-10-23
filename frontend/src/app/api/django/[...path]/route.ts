import { NextRequest } from 'next/server';
import { getDjangoBackendUrl } from '@/lib/backend-url';

async function forward(request: NextRequest, path: string[]) {
  const backend = getDjangoBackendUrl();
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
    signal: AbortSignal.timeout(8000),
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
  try {
    return await forward(request, path);
  } catch (error) {
    return backendError(error);
  }
}

export async function GET(request: NextRequest, context: RouteContext) {
  const { path } = await context.params;
  try {
    return await forward(request, path);
  } catch (error) {
    return backendError(error);
  }
}

function backendError(error: unknown) {
  const timedOut = error instanceof Error && error.name === 'TimeoutError';
  return Response.json(
    { detail: timedOut ? 'The service took too long to respond. Please try again.' : 'The service is temporarily unavailable. Please try again.' },
    { status: timedOut ? 504 : 503 },
  );
}
