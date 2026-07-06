# 接口文档与 JMeter 压测说明

## 2026-07-06 补充：环境管理和健康检查接口

环境管理用于保存测试环境 Base URL 和变量，接口测试、UI 测试、测试任务和 JMeter 压测都可以复用这些环境配置。

| 方法 | 路径 | 说明 | JMeter 关注点 |
|---|---|---|---|
| GET | /api/environments | 查询环境列表 | 页面初始化、参数化环境选择 |
| POST | /api/environments | 新增环境 | 低频写入，校验公网 URL 拦截 |
| PUT | /api/environments/{environment_id} | 修改环境 | 修改 Base URL 后再做健康检查 |
| DELETE | /api/environments/{environment_id} | 删除环境 | 只清理未被任务或结果引用的测试数据 |
| POST | /api/v1/environments/{environment_id}/health-check | 环境健康检查 | 关注响应时间、状态码和错误率 |

推荐压测前置流程：

```text
1. 调用 POST /api/auth/login 获取 token。
2. 调用 GET /api/environments 读取环境列表。
3. 对压测目标环境调用 POST /api/v1/environments/{environment_id}/health-check。
4. 只有健康检查返回 ok 或预期状态码时，再开始压测业务接口。
```


## 2026-07-06 补充：接口用例 environment_id 与相对路径

接口用例现在支持绑定测试环境。绑定环境后，`url` 字段可以填写相对路径，执行时由 worker 拼接环境的 `base_url`。

| 字段 | 类型 | 说明 | JMeter 关注点 |
|---|---|---|---|
| environment_id | number 或 null | 可选测试环境 ID | 建议参数化，方便同一批用例切换测试环境 |
| url | string | 完整公网 URL，或选择环境后的 `/path` 相对路径 | 压测时可把路径拆成 CSV 参数 |
| headers | object | 请求头 JSON | 可放 Authorization、Content-Type 等公共头 |
| body | string 或 null | 请求体文本 | 可用 CSV 参数替换 body 中的变量 |

创建接口用例请求体示例：

```json
{
  "project_id": 1,
  "environment_id": 1,
  "name": "查询用户列表",
  "method": "GET",
  "url": "/api/users",
  "headers": {
    "Authorization": "Bearer {{token}}"
  },
  "body": null,
  "assert_status": 200,
  "assert_text": "success",
  "assert_json_path": "$.data.0.id",
  "assert_json_value": "1"
}
```

JMeter 设计建议：

```text
1. 把 environment_id、url、method、assert_status 放入 CSV Data Set Config。
2. 用一个线程组压测 GET /api/api-cases 列表查询。
3. 用低并发线程组压测 POST /api/api-cases 创建用例，避免制造大量无用数据。
4. 如果要压测执行链路，使用 POST /api/runs 创建执行任务，再轮询 GET /api/runs/{id}。
5. 压测结束后清理测试用例，或使用独立压测项目避免污染真实项目。
```


## 2026-07-06 补充：问题定位接口

问题定位模块用于把失败结果转成可跟踪记录，适合 JMeter 或 CI 回传失败结果后继续做根因跟踪。

| 方法 | 路径 | 说明 | JMeter 关注点 |
|---|---|---|---|
| GET | /api/v1/problem-findings | 查询问题定位记录 | 列表查询响应时间、按状态过滤 |
| POST | /api/v1/problem-findings | 手工新增定位记录 | 低频写入，不建议高并发压测 |
| PUT | /api/v1/problem-findings/{finding_id} | 修改定位记录 | 模拟状态流转：待定位、定位中、已修复 |
| DELETE | /api/v1/problem-findings/{finding_id} | 删除定位记录 | 只用于测试数据清理 |
| POST | /api/v1/problem-findings/from-result/{result_id} | 从失败结果生成定位记录 | 先构造 failed/error 结果，再生成定位 |

推荐压测流程：

```text
1. 登录获取 Bearer Token。
2. 调用 /api/v1/test-results/batch 回传一批 failed/error 结果。
3. 调用 /api/v1/problem-findings/from-result/{result_id} 生成定位记录。
4. 调用 /api/v1/problem-findings 查询列表。
5. 调用 PUT /api/v1/problem-findings/{finding_id} 模拟处理状态流转。
```


本文档说明自动化测试平台当前后端接口如何查看、如何调用，以及后续做 JMeter 性能测试时应该怎么设计脚本。

## 1. Swagger 访问地址

公网 Swagger 页面：

```text
http://111.229.178.141/api/docs
```

公网 ReDoc 页面：

```text
http://111.229.178.141/api/redoc
```

OpenAPI JSON 地址：

```text
http://111.229.178.141/api/openapi.json
```

本地开发时，对应地址通常是：

```text
http://localhost/api/docs
http://localhost/api/openapi.json
```

## 2. 接口认证方式

除健康检查和文件快传的公开扫码接口外，大多数接口都需要登录。

登录接口：

```text
POST /api/auth/login
```

请求体示例：

```json
{
  "username": "admin",
  "password": "请填写服务器 .env 中配置的 ADMIN_PASSWORD"
}
```

返回示例：

```json
{
  "access_token": "eyJ...",
  "token_type": "bearer"
}
```

后续接口请求头需要带上：

```text
Authorization: Bearer 登录接口返回的 access_token
```

## 3. 接口分组

| 分组 | 主要用途 | 是否需要登录 | JMeter 关注点 |
|---|---|---|---|
| 健康检查 | 判断后端是否存活 | 否 | 基础连通性、网络延迟 |
| 认证 | 登录、退出、当前用户 | 登录接口不需要 | token 提取、登录成功率 |
| 用户管理 | 管理用户和菜单权限 | 管理员 | 低频接口，不建议高并发写入 |
| 项目与环境 | 项目、环境配置 | 是 | 列表查询、创建项目、创建环境 |
| 测试对象 | 维护平台要测什么 | 是 | 对象查询、对象创建、标签和模块过滤 |
| 测试能力 | 场景、Mock、性能、Runner | 是 | 性能场景配置、Runner 状态查询 |
| 测试任务 | 维护任务和执行批次 | 是 | 创建批次、CI/API 触发、状态查询 |
| 结果中心 | 统一沉淀结果和附件 | 是 | 批量回传、结果查询、附件上传 |
| 质量分析 | 通过率、失败分布和趋势 | 是 | 汇总接口的响应时间和计算成本 |
| 测试数据 | 变量集、账号、数据池 | 是 | 参数化数据读取和低频维护 |
| 接口测试 | 接口用例增删改查 | 是 | 用例列表、用例创建、目标 URL 安全拦截 |
| UI测试 | UI 用例增删改查 | 是 | 步骤 JSON 保存、目标 URL 安全拦截 |
| 文件快传 | 临时文件上传、扫码下载 | 部分公开 | 上传大小、下载带宽、磁盘占用 |
| 图片工具 | 图片生成和处理 | 是 | CPU、内存、图片大小 |
| 执行记录 | 创建任务、查询结果 | 是 | 创建任务吞吐、轮询间隔、队列积压 |
| 测试报告 | 查询报告 | 是 | 报告列表和详情查询响应时间 |
| 集成开放 | Webhook 和外部系统配置 | 是 | 配置查询，避免压测真实通知地址 |

## 4. 核心接口清单

| 方法 | 路径 | 说明 | 常见压测场景 |
|---|---|---|---|
| GET | /api/health | 后端健康检查 | 每秒少量请求确认服务可用 |
| POST | /api/auth/login | 登录并获取 token | setUp Thread Group 登录一次 |
| POST | /api/auth/logout | 退出登录 | 功能验证即可 |
| GET | /api/auth/me | 当前用户信息和菜单权限 | 登录后页面初始化 |
| GET | /api/menu-options | 可配置菜单权限 | 管理员页面初始化 |
| GET | /api/users | 用户列表 | 管理员查询 |
| POST | /api/users | 新增用户 | 低频写入，不建议高并发 |
| PUT | /api/users/{user_id} | 修改用户 | 低频写入 |
| DELETE | /api/users/{user_id} | 删除用户 | 低频写入 |
| GET | /api/projects | 项目列表 | 高频页面查询 |
| POST | /api/projects | 新增项目 | 参数化创建测试数据 |
| PUT | /api/projects/{project_id} | 修改项目 | 低频写入 |
| DELETE | /api/projects/{project_id} | 删除项目 | 谨慎压测，会删除关联数据 |
| GET | /api/environments | 环境列表 | 页面初始化 |
| POST | /api/environments | 新增环境 | 校验公网 URL 拦截 |
| GET | /api/v1/test-objects | 测试对象列表 | 高频查询，可按类型、项目、启用状态过滤 |
| POST | /api/v1/test-objects | 新增测试对象 | 参数化创建接口、页面、脚本、设备等对象 |
| PUT | /api/v1/test-objects/{object_id} | 修改测试对象 | 低频写入 |
| DELETE | /api/v1/test-objects/{object_id} | 删除测试对象 | 第一批不影响旧用例，仍需谨慎清理测试数据 |
| GET | /api/v1/api-scenarios | API 场景列表 | 场景编排查询 |
| POST | /api/v1/api-scenarios | 新增 API 场景 | 低频维护 |
| GET | /api/v1/mock-rules | Mock 规则列表 | Mock 配置查询 |
| POST | /api/v1/mock-rules | 新增 Mock 规则 | 低频维护 |
| GET | /api/v1/performance-scenarios | 性能场景列表 | JMeter 场景配置来源 |
| POST | /api/v1/performance-scenarios | 新增性能场景 | 参数化并发、时长、阈值 |
| GET | /api/v1/runners | Runner 列表 | 执行机状态查询 |
| POST | /api/v1/runners/{runner_id}/heartbeat | Runner 心跳 | 执行机心跳压测 |
| GET | /api/v1/test-tasks | 测试任务列表 | 高频查询 |
| POST | /api/v1/test-tasks | 新增测试任务 | 参数化任务编号、类型和配置 |
| POST | /api/v1/test-tasks/{task_id}/run | 创建执行批次 | 观察批次创建吞吐 |
| GET | /api/v1/test-tasks/{task_id}/status | 查询任务最近状态 | CI/JMeter 轮询 |
| GET | /api/v1/execution-batches | 执行批次列表 | 结果中心页面查询 |
| GET | /api/v1/test-results | 测试结果列表 | 结果中心页面查询 |
| POST | /api/v1/test-tasks/{task_id}/results/batch | 任务结果批量回传 | JMeter/CI 结果回传核心接口 |
| POST | /api/v1/test-results/batch | 独立结果批量回传 | 外部脚本不绑定任务时使用 |
| POST | /api/v1/attachments | 上传结果附件 | 小文件验证，避免大并发上传 |
| GET | /api/v1/quality/summary | 质量总览 | 汇总计算接口 |
| GET | /api/v1/reports/quality-trend | 质量趋势 | 趋势查询 |
| GET | /api/v1/test-datasets | 测试数据列表 | 参数化数据读取 |
| POST | /api/v1/test-datasets | 新增测试数据 | 低频维护 |
| GET | /api/v1/integrations/webhooks | 集成配置列表 | 配置查询 |
| POST | /api/v1/integrations/webhooks | 新增集成配置 | 不建议压测真实通知地址 |
| GET | /api/api-cases | 接口用例列表 | 高频查询 |
| POST | /api/api-cases | 新增接口用例 | 参数化 URL、方法、断言 |
| PUT | /api/api-cases/{case_id} | 修改接口用例 | 低频写入 |
| DELETE | /api/api-cases/{case_id} | 删除接口用例 | 会删除执行历史，谨慎使用 |
| GET | /api/ui-cases | UI 用例列表 | 高频查询 |
| POST | /api/ui-cases | 新增 UI 用例 | 参数化步骤 JSON |
| PUT | /api/ui-cases/{case_id} | 修改 UI 用例 | 低频写入 |
| DELETE | /api/ui-cases/{case_id} | 删除 UI 用例 | 会删除执行历史，谨慎使用 |
| GET | /api/file-transfers | 文件快传列表 | 页面查询 |
| POST | /api/file-transfers | 上传临时文件 | 小文件上传吞吐和磁盘观察 |
| DELETE | /api/file-transfers/{transfer_id} | 删除临时文件 | 清理测试数据 |
| GET | /api/file-transfers/public/{token} | 公开文件信息 | 手机扫码页面查询 |
| GET | /api/file-transfers/public/{token}/download | 公开下载文件 | 下载带宽和响应时间 |
| GET | /api/file-transfers/public/{token}/preview | 公开预览图片/视频 | 浏览器预览验证 |
| POST | /api/file-transfers/public/{token}/upload | 手机端回传文件 | 小文件上传验证 |
| GET | /api/image-tools/formats | 图片格式列表 | 页面初始化 |
| POST | /api/image-tools/generate | 生成图片 | CPU、内存、响应大小 |
| POST | /api/image-tools/process | 处理上传图片 | CPU、内存、上传大小 |
| GET | /api/runs | 执行记录列表 | 高频查询 |
| POST | /api/runs | 创建执行任务 | 队列吞吐、worker 消费速度 |
| GET | /api/runs/{run_id} | 查询执行结果 | 轮询间隔和完成耗时 |
| GET | /api/reports | 测试报告列表 | 高频查询 |
| GET | /api/reports/{run_id} | 测试报告详情 | 单报告响应时间 |

## 5. JMeter 脚本建议

### 5.1 线程组设计

建议先拆成 4 类压测脚本：

1. 基础查询压测：登录、查询项目、查询用例、查询执行记录、查询报告。
2. 用例管理压测：创建项目、创建接口用例、创建 UI 用例、删除测试数据。
3. 执行任务压测：创建执行任务、按 run_id 轮询状态、查询报告。
4. 文件和图片压测：上传小文件、下载文件、生成图片、处理图片。

不要一开始就把所有接口混在一个线程组里。先单接口跑通，再组合成真实用户流程。

### 5.2 登录和 token 提取

在 JMeter 中建议这样做：

1. 新建 setUp Thread Group。
2. 添加 HTTP Request：`POST /api/auth/login`。
3. 添加 JSON Extractor：

```text
Names of created variables: token
JSON Path expressions: $.access_token
Match No.: 1
```

4. 在线程组中添加 HTTP Header Manager：

```text
Authorization: Bearer ${token}
Content-Type: application/json
Accept: application/json
```

如果每个并发用户都要模拟独立登录，可以把登录请求放到普通 Thread Group 的最前面；如果只是压测业务接口吞吐，可以 setUp 登录一次后复用 token。

### 5.3 参数化数据

建议使用 CSV Data Set Config 管理参数，避免所有线程写同一条数据。

示例 CSV 字段：

```text
project_name,case_name,target_url,method,assert_status
压测项目001,接口用例001,https://httpbin.org/get,GET,200
压测项目002,接口用例002,https://httpbin.org/status/200,GET,200
```

接口用例创建请求体示例：

```json
{
  "project_id": ${project_id},
  "name": "${case_name}",
  "method": "${method}",
  "url": "${target_url}",
  "headers": {
    "Accept": "application/json"
  },
  "body": null,
  "assert_status": ${assert_status},
  "assert_text": null,
  "assert_json_path": null,
  "assert_json_value": null
}
```

UI 用例创建请求体示例：

```json
{
  "project_id": ${project_id},
  "name": "UI 首页打开压测用例",
  "steps": [
    {
      "action": "goto",
      "target": null,
      "value": "https://example.com",
      "timeout_ms": 5000
    },
    {
      "action": "assert_text",
      "target": "Example Domain",
      "value": null,
      "timeout_ms": 5000
    },
    {
      "action": "screenshot",
      "target": null,
      "value": null,
      "timeout_ms": 5000
    }
  ]
}
```

### 5.4 断言建议

每个 JMeter 请求至少加这些断言：

| 类型 | 建议 |
|---|---|
| Response Assertion | 校验状态码为 200、201 或业务预期状态 |
| JSON Assertion | 校验关键字段存在，例如 `access_token`、`id`、`status` |
| Duration Assertion | 给核心查询接口设置合理响应时间上限 |
| Size Assertion | 文件下载和图片生成接口可校验响应体大小 |

### 5.5 执行任务接口的压测方式

执行任务是异步流程：

1. `POST /api/runs` 创建任务。
2. 从响应中提取 `id`。
3. 每隔 2 到 5 秒调用 `GET /api/runs/{run_id}`。
4. 当 `status` 变成 `passed`、`failed` 或 `error` 后停止轮询。
5. 调用 `GET /api/reports/{run_id}` 查询报告。

不要把轮询间隔设置得太短，否则压测结果会被“查询状态”接口淹没，不能真实反映 worker 执行能力。

### 5.6 文件和图片接口的风险控制

文件快传和图片处理会消耗磁盘、CPU、内存和带宽。压测时建议：

```text
单文件大小：先从 100KB 到 1MB 开始
并发用户：先从 5 到 20 开始
压测时长：先 3 到 5 分钟
清理策略：压测后调用删除接口或等待过期清理
```

不要直接使用大视频、大图片做高并发上传，容易把服务器磁盘或公网带宽打满。

### 5.7 建议观察指标

JMeter 侧：

```text
平均响应时间
P90 / P95 / P99 响应时间
错误率
吞吐量 TPS
每秒接收/发送字节数
```

服务器侧：

```bash
cd /opt/automation-platform
docker compose ps
docker stats
docker compose logs -f backend
docker compose logs -f worker
```

数据库和队列侧重点：

```text
MySQL CPU / 内存 / 慢查询
Redis 内存和队列堆积
worker 是否消费不过来
文件目录是否持续增长
```

## 6. 从 Swagger 到 JMeter 的落地步骤

1. 打开 `http://111.229.178.141/api/docs`。
2. 先用 `POST /api/auth/login` 试调登录。
3. 点击 Swagger 页面右上角 Authorize，填入 `Bearer token值`。
4. 用 Swagger 逐个确认接口请求体格式。
5. 在 JMeter 中按同样的路径、方法、请求体创建 HTTP Request。
6. 给登录接口加 JSON Extractor，给业务接口加 Header Manager。
7. 单接口调通后，再组合成完整业务链路。
8. 正式压测前先备份数据库，避免误删项目、用例和报告。

## 7. 安全注意事项

- 不要把服务器密码、平台管理员密码、GitHub 密码写进 JMeter 脚本并上传到仓库。
- 压测目标 URL 必须是自己拥有或被允许压测的系统。
- 平台已经阻断 localhost、内网 IP、云元数据地址等敏感目标，但仍然不要尝试绕过安全限制。
- 文件上传压测要控制大小和并发，避免影响服务器稳定性。
- 生产数据压测前必须确认删除接口不会误删真实项目和用例。
