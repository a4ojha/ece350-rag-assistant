import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Empty turbopack config to silence warning (react-pdf works without webpack config in turbopack)
  turbopack: {},
};

export default nextConfig;
