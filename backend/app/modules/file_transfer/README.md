# file_transfer

文件快传接口位于 `backend/app/modules/file_transfer/router.py`。

后台上传、二维码分享和手机端回传共用临时令牌；公开访问只能使用令牌对应的受限下载或回传地址，管理操作仍需登录与菜单权限。
