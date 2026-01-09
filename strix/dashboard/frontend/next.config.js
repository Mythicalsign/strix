const path = require('path')

/** @type {import('next').NextConfig} */
const nextConfig = {
  output: 'export',
  distDir: 'out',
  images: {
    unoptimized: true,
  },
  trailingSlash: true,
  webpack: (config) => {
    // Add path alias resolution for @/ imports
    config.resolve.alias = {
      ...config.resolve.alias,
      '@': path.resolve(__dirname, './'),
    }
    return config
  },
}

module.exports = nextConfig