import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  output: 'export',
  trailingSlash: true,
  distDir: 'out',
  images: {
    loader: 'custom',
    loaderFile: './utils/image-loader.js',
  },
};

export default nextConfig;
