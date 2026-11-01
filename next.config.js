const path = require('path');

/** @type {import('next').NextConfig} */
const nextConfig = {
  // Keep the PDF worker/native dependencies available in Vercel's Node runtime.
  serverExternalPackages: ['pdf-parse'],
  outputFileTracingRoot: path.join(__dirname),
  // Bound static-page worker fanout on small development/build machines.
  experimental: {
    cpus: 1,
  },
};

module.exports = nextConfig;
