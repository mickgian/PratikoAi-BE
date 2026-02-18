import type { NextConfig } from 'next';

const nextConfig: NextConfig = {
  reactStrictMode: false, // 👈 stop double-invoke in dev
  output: 'standalone', // Required for Docker deployment (self-contained Node server)
  images: {
    domains: ['images.unsplash.com'],
  },

  // Production optimizations
  serverExternalPackages: ['katex'],

  // Bundle analyzer (only in development)
  /* eslint-disable @typescript-eslint/no-require-imports, @typescript-eslint/no-explicit-any */
  ...(process.env.ANALYZE === 'true' && {
    webpack: (config: any) => {
      config.plugins.push(
        new (require('@next/bundle-analyzer')({
          enabled: true,
        }))()
      );
      return config;
    },
  }),
  /* eslint-enable @typescript-eslint/no-require-imports, @typescript-eslint/no-explicit-any */

  // Performance optimizations (swcMinify is now default in Next.js 15)

  // Compression
  compress: true,

  // Enable static optimization
  trailingSlash: false,

  // Power optimizations for production
  poweredByHeader: false,

  // Security headers
  async headers() {
    return [
      {
        source: '/(.*)',
        headers: [
          {
            key: 'X-Content-Type-Options',
            value: 'nosniff',
          },
          {
            key: 'X-Frame-Options',
            value: 'DENY',
          },
          {
            key: 'X-XSS-Protection',
            value: '1; mode=block',
          },
          {
            key: 'Referrer-Policy',
            value: 'strict-origin-when-cross-origin',
          },
        ],
      },
    ];
  },
};

export default nextConfig;
