import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  output: "export",
  images: {
    unoptimized: true,
  },
  // Avoid wrong turbopack root when multiple lockfiles exist on the machine
  turbopack: {
    root: __dirname,
  },
};

export default nextConfig;
