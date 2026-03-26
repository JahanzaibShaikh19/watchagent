/** @type {import('next').NextConfig} */
const nextConfig = {
    reactStrictMode: true,
    poweredByHeader: false,
    compress: true,
    output: "standalone",
    images: {
        formats: ["image/avif", "image/webp"],
    },
};

module.exports = nextConfig;