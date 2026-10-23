const DEVELOPMENT_BACKEND = 'http://127.0.0.1:8000';

/** Resolve the private Django origin; production must never silently call localhost. */
export function getDjangoBackendUrl(): string {
  const configured = process.env.DJANGO_URL?.trim();
  if (!configured) {
    if (process.env.NODE_ENV !== 'production') return DEVELOPMENT_BACKEND;
    throw new Error('DJANGO_URL must be configured for the production frontend.');
  }

  let parsed: URL;
  try {
    parsed = new URL(configured);
  } catch {
    throw new Error('DJANGO_URL must be an absolute HTTP or HTTPS URL.');
  }

  if (!['http:', 'https:'].includes(parsed.protocol) || parsed.username || parsed.password || parsed.search || parsed.hash || (parsed.pathname !== '/' && parsed.pathname !== '')) {
    throw new Error('DJANGO_URL must be a backend origin without credentials, path, query, or fragment.');
  }
  const deployedProduction = process.env.DJANGO_ENV?.toLowerCase() === 'production'
    || Boolean(process.env.RAILWAY_ENVIRONMENT)
    || process.env.VERCEL_ENV?.toLowerCase() === 'production';
  if (deployedProduction && ['localhost', '127.0.0.1', '::1', '[::1]', '0.0.0.0'].includes(parsed.hostname.toLowerCase())) {
    throw new Error('DJANGO_URL must point to the deployed backend in production, not localhost.');
  }

  return parsed.origin;
}
