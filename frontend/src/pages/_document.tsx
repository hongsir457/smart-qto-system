import { Html, Head, Main, NextScript } from 'next/document'

export default function Document() {
  return (
    <Html lang="zh-CN">
      <Head>
        {/* Favicon配置 */}
        <link rel="icon" href="/favicon.svg" type="image/svg+xml" />
        <link rel="alternate icon" href="/favicon.ico" />
        <link rel="apple-touch-icon" href="/apple-touch-icon.png" />
        
        {/* Meta信息 */}
        <meta name="description" content="智能工程量计算系统 - 基于AI的工程量清单自动化计算平台" />
        <meta name="keywords" content="工程量计算,智能计算,AI,建筑工程,工程量清单" />
        <meta name="author" content="智能工程量计算系统" />
        
        {/* PWA相关 */}
        <meta name="theme-color" content="#1890ff" />
        <meta name="msapplication-TileColor" content="#1890ff" />
        
        {/* 预加载关键资源 */}
        <link rel="preconnect" href="http://localhost:8000" />
        
        {/* 字体优化 */}
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
      </Head>
      <body>
        <Main />
        <NextScript />
      </body>
    </Html>
  )
} 