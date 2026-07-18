# Backend modules

后端只保留 `auth`、`health`、`data_generator`、`file_transfer`、`image_tools`、`integrations` 和 `users`。

新增工具时保持独立路由、schema 和 service，避免引入任务调度、执行器或结果中心依赖。
