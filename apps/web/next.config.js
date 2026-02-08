/** @type {import('next').NextConfig} */
const nextConfig = {
  env: {
    // Vercel provides these at build time
    NEXT_PUBLIC_COMMIT_SHA: process.env.VERCEL_GIT_COMMIT_SHA || 'dev',
    NEXT_PUBLIC_COMMIT_MESSAGE: process.env.VERCEL_GIT_COMMIT_MESSAGE || 'local',
  },
};

module.exports = nextConfig;
