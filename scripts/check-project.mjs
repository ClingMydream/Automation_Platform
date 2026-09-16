import { existsSync, readFileSync } from 'node:fs';

const required = [
  'project.config.json', 'miniprogram/app.js', 'miniprogram/app.json',
  'miniprogram/config/env.js', 'miniprogram/utils/request.js',
  'miniprogram/pages/login/index.js', 'miniprogram/pages/home/index.js',
  'miniprogram/pages/profile/index.js',
];
const missing = required.filter((file) => !existsSync(file));
if (missing.length) throw new Error(`缺少文件：${missing.join(', ')}`);
const config = JSON.parse(readFileSync('project.config.json', 'utf8'));
if (config.miniprogramRoot !== 'miniprogram/') throw new Error('miniprogramRoot 配置错误。');
console.log(`检查通过：${required.length} 个小程序关键文件已就绪。`);
