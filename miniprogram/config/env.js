/**
 * 开发与生产 API 配置。
 * 真机调试和发布版必须使用已备案的 HTTPS 域名，并在微信公众平台配置为合法 request 域名。
 */
const ENV = 'development';

const configs = {
  development: {
    // 在微信开发者工具中可临时勾选“不校验合法域名”进行本地联调。
    // docker-compose 将主站的 /api 请求反向代理到 FastAPI 后端。
    apiBaseUrl: 'http://127.0.0.1/api',
  },
  production: {
    // 发布前替换为已部署平台的 HTTPS 地址，例如 https://platform.example.com/api
    apiBaseUrl: 'https://YOUR-PLATFORM-DOMAIN.example/api',
  },
};

module.exports = configs[ENV];
