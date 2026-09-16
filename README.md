# Cling 微信小程序

这是现有 Cling 平台的移动端入口。平台 Web 端继续承担用户、权限、系统配置等管理职责；小程序面向日常查看与轻量操作。

当前版本是独立 OA 审批入口：微信授权登录、请假/报销/采购申请、申请查询和管理员审批。平台 Web 端负责小程序账号与审批数据管理；不再使用平台账号密码登录。

## 本地启动

1. 安装并打开[微信开发者工具](https://developers.weixin.qq.com/miniprogram/dev/devtools/download.html)。
2. 选择“导入项目”，目录选本项目根目录；AppID 可先选择“测试号”或填写自己的小程序 AppID。
3. 打开 `miniprogram/config/env.js`：开发者工具联调可使用本机 API；真机调试应改用可访问的 HTTPS 测试环境。
4. 在开发者工具中编译。后台服务本地启动命令为 `docker compose up -d --build`。

执行 `npm run check` 可检查项目必要文件；它不代替开发者工具的编译和真机测试。

## 微信小程序创建与发布指引

1. 进入[微信公众平台](https://mp.weixin.qq.com/)，注册“小程序”账号，选择主体类型并完成主体认证。个人主体的能力与企业主体不同；如需支付、主体认证、业务域名等能力，按平台当期要求办理。
2. 在“开发管理 → 开发设置”获取 AppID，填入 `project.config.json` 的 `appid`。AppSecret 不要放到小程序代码或 Git 仓库。
3. 部署本平台到一个可公开访问的 HTTPS 域名，在“开发管理 → 开发设置 → 服务器域名”中登记该域名为合法 request 域名。开发者工具里可暂时关闭域名校验，但真机和审核版本必须配置合法 HTTPS 域名。
4. 在开发者工具中使用 AppID 导入本项目，配置“开发成员”，完成编译、预览和真机调试。
5. 开发完成后上传代码，在公众平台提交体验版、提交审核，审核通过后发布。发布前更新隐私说明、用户协议和数据收集说明，并核实实际调用的接口域名。

## 与现有管理端的接口边界

本版本为了跑通联调，临时复用 `POST /api/auth/login` 和 `GET /api/auth/me`。生产版不应让小程序用户长期使用后台管理员密码。

建议下一阶段在 FastAPI 中增加小程序专用认证：小程序调用 `wx.login()` 获取一次性 code，服务端以 AppSecret 换取 OpenID，按 OpenID 创建或匹配用户，再签发短期 access token。AppSecret 只保存在服务端环境变量。之后再按优先级接入学习进度、文件快传、消息等面向移动端的接口。

## 目录

```
miniprogram/
  config/env.js       API 地址配置
  services/           平台接口封装
  utils/              登录状态与网络请求
  pages/              登录、工作台、个人中心
project.config.json   微信开发者工具项目配置
```
