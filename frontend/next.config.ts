import type { NextConfig } from 'next';
import { getDjangoBackendUrl } from './src/lib/backend-url';

const config: NextConfig = {
  allowedDevOrigins: ['127.0.0.1'],
  experimental: {
    agentUpgrade: 'security',
  },
  skipTrailingSlashRedirect: true,
  async redirects() {
    if (process.env.NODE_ENV !== 'development') return [];
    return [{
      source: '/:path*',
      has: [{ type: 'host', value: 'localhost' }],
      destination: 'http://127.0.0.1:3000/:path*',
      permanent: false,
    }];
  },
  async rewrites() {
    const backend = getDjangoBackendUrl();
    return [{ source: '/media/:path*', destination: `${backend}/media/:path*` }];
  },
};

export default config;
