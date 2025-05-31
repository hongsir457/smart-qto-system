/** @type {import('next').NextConfig} */
const nextConfig = {
  transpilePackages: ['antd', '@ant-design/icons'],
  experimental: {
    esmExternals: 'loose',
  },
  webpack: (config, { isServer }) => {
    // 修复 antd ESM 模块导入问题
    config.resolve.fallback = {
      ...config.resolve.fallback,
    };
    
    // 为 antd 添加模块别名
    config.resolve.alias = {
      ...config.resolve.alias,
      'antd/es': 'antd/lib',
      'antd/es/style': 'antd/lib/style',
    };
    
    return config;
  },
  async rewrites() {
    return [
      {
        source: '/api/:path*',
        destination: 'http://localhost:8000/api/:path*',
      },
    ];
  },
}

module.exports = nextConfig; 