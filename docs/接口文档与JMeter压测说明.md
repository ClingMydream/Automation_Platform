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


## 2026-07-06 补充：接口调试执行接口

接口调试接口用于在接口测试页内发起一次轻量执行，适合测试人员保存用例后立即验证请求、响应和断言是否正确。

| 方法 | 路径 | 说明 | JMeter 关注点 |
|---|---|---|---|
| POST | /api/api-cases/{case_id}/debug | 创建接口调试任务 | 低频操作，主要关注创建任务成功率 |
| GET | /api/api-cases/debug-runs/{run_id} | 查询接口调试结果 | 可用于轮询压测，关注 queued/running 到 passed/failed 的耗时 |

调试和正式执行的区别：

```text
调试：留在接口测试页，快速查看一次请求、响应和断言。
正式执行：进入执行记录和测试报告链路，用于沉淀历史和对外报告。
```

调试请求示例：

```http
POST /api/api-cases/1/debug
Authorization: Bearer <token>
```

调试结果轮询示例：

```http
GET /api/api-cases/debug-runs/100
Authorization: Bearer <token>
```

JMeter 建议：

```text
1. 不建议高并发压测调试接口，因为每次调试都会进入 worker 执行队列。
2. 如果要压测队列能力，先创建少量稳定接口用例，再按 run_id 轮询结果。
3. 重点统计从 POST debug 到 GET debug-runs 返回 passed/failed 的端到端耗时。
```


## 2026-07-07 补充：接口批量任务执行

测试任务现在可以批量执行接口用例。API 类型任务通过 `config.api_case_ids` 维护用例集合，启动任务后平台会创建执行批次，并将每个接口用例推送到 worker 队列执行。

| 方法 | 路径 | 说明 | JMeter 关注点 |
|---|---|---|---|
| POST | /api/v1/test-tasks | 创建 API 测试任务 | 低频写入，校验任务配置 JSON |
| PUT | /api/v1/test-tasks/{task_id} | 修改 API 测试任务 | 可变更 api_case_ids 和环境 |
| POST | /api/v1/test-tasks/{task_id}/run | 启动批量执行 | 重点关注创建批次成功率、队列堆积和任务完成耗时 |
| GET | /api/v1/execution-batches | 查询执行批次 | 可轮询批次状态、通过率、失败率 |
| GET | /api/v1/test-results | 查询结果明细 | 可统计接口结果响应时间和断言失败分布 |

创建 API 批量任务请求体示例：

```json
{
  "code": "TASK-API-SMOKE-001",
  "name": "接口冒烟批量任务",
  "task_type": "api",
  "project_id": 1,
  "environment_id": 1,
  "test_object_id": null,
  "trigger_type": "manual",
  "runner_type": "platform",
  "retry_count": 0,
  "schedule_cron": null,
  "owner": "tester",
  "is_active": true,
  "config": {
    "api_case_ids": [1, 2, 3]
  },
  "description": "批量执行核心接口用例"
}
```

启动任务请求体示例：

```json
{
  "trigger_type": "manual",
  "environment_id": 1,
  "summary": {
    "source": "web",
    "note": "冒烟验证"
  }
}
```

JMeter 建议：

```text
1. 用少量 API 用例验证批量执行链路，避免一次性制造大量 worker 任务。
2. POST /api/v1/test-tasks/{task_id}/run 后，轮询 /api/v1/execution-batches。
3. 批次 status 变为 passed 或 failed 后，再查询 /api/v1/test-results 分析明细。
4. 重点统计端到端耗时、失败率、断言失败分类和 worker 队列承载能力。
```


## 2026-07-07 补充：执行批次测试报告

测试报告现在支持批次报告。批次报告从 `execution_batches` 和 `test_results` 汇总，用于展示一次批量执行的整体结论和结果明细。

| 方法 | 路径 | 说明 | JMeter 关注点 |
|---|---|---|---|
| GET | /api/reports | 报告列表，包含单次执行报告和批次报告 | 高频列表查询、分页前数据量增长 |
| GET | /api/reports/batches/{batch_id} | 查询单个批次报告 | 批次结果多时的响应大小和响应时间 |
| GET | /api/reports/{run_id} | 查询单次执行报告 | 单用例报告详情查询 |

批次报告返回内容重点：

```text
report_kind: batch
batch: 批次号、任务 ID、触发方式、环境 ID
stats: 总数、通过数、失败数、跳过数
results: 每条结果的请求、响应、断言、指标和错误信息
```

JMeter 建议：

```text
1. 先启动 API 批量任务并等待批次完成。
2. 对 /api/reports 做列表查询压测，观察报告列表随历史数据增长的响应时间。
3. 对 /api/reports/batches/{batch_id} 做详情查询压测，重点观察大批次结果的响应大小。
4. 报告查询属于读接口，可比写入接口设置更高并发，但仍要避免把数据库 CPU 打满。
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
| GET | /api/v1/attachments | 查询结果或批次附件 | 校验附件证据是否沉淀成功 |
| POST | /api/v1/attachments | 上传结果附件 | 小文件验证，避免大并发上传 |
| POST | /api/v1/attachments/external | Token 上传外部附件 | JMeter/CI 上传 HTML 报告、日志、HAR |
| GET | /api/v1/attachments/{attachment_id}/download | 下载附件 | 校验报告文件是否可取回 |
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

### 5.7 定时任务调度验证

平台 worker 已支持轻量定时调度。定时调度适合小规模周期回归，不适合代替大规模压测执行机。

支持范围：

```text
task_type=api
runner_type=platform
任务处于启用状态
config.api_case_ids 中存在可执行接口用例
```

cron 写法：

```text
*/10 * * * *    每 10 分钟执行一次
0 * * * *       每小时第 0 分钟执行一次
30 9 * * 1-5    工作日 09:30 执行
```

调度验证方式：

```text
1. 打开“测试任务”，创建 API 任务并选择接口用例集合。
2. 执行来源保持 platform。
3. 定时 cron 填 */10 * * * *。
4. 保存后保持任务启用。
5. 到点后打开“结果中心”，查看 trigger_type=schedule 的执行批次。
6. 打开“测试报告”确认批次报告是否生成。
```

服务器开关：

```text
SCHEDULER_ENABLED=true
SCHEDULER_POLL_SECONDS=30
```

如果只想通过 Jenkins、GitHub Actions 或 JMeter 外部触发，可以把 `SCHEDULER_ENABLED=false` 后重启 worker。

### 5.8 建议观察指标

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

## 8. CI/API 触发与失败重试接口

### 8.1 外部触发测试任务

用途：

```text
给 Jenkins、GitHub Actions、GitLab CI、JMeter 或其他外部系统触发平台任务使用。
```

接口：

```text
POST /api/v1/test-tasks/by-code/{task_code}/trigger
Header: X-Automation-Token: 服务器 .env 中的 EXTERNAL_TRIGGER_TOKEN
```

请求示例：

```json
{
  "trigger_type": "ci",
  "environment_id": 1,
  "summary": {
    "build_no": "20260707.1",
    "branch": "main",
    "commit": "abcdef"
  }
}
```

说明：

```text
task_code 是测试任务里的“任务编号”。
trigger_type 建议填写 ci 或 api。
EXTERNAL_TRIGGER_TOKEN 不要写进 GitHub，也不要直接写进 JMeter 脚本仓库。
```

### 8.2 重试失败批次

用途：

```text
当一次接口批量任务有失败用例时，只重跑失败的 API 用例，不重复跑全部用例。
```

接口：

```text
POST /api/v1/execution-batches/{batch_id}/retry
Authorization: Bearer 登录 token
```

请求示例：

```json
{
  "trigger_type": "manual",
  "summary": {
    "reason": "fix后回归失败用例"
  }
}
```

JMeter 建议：

```text
1. 先触发任务。
2. 轮询批次或报告接口，确认批次状态。
3. 如果状态为 failed，再调用 retry 接口。
4. 不要无限循环重试，建议最多 1 到 2 次。
```

### 8.3 外部脚本按任务编号回传结果

用途：

```text
给 Jenkins、GitHub Actions、GitLab CI、JMeter、pytest、Playwright 等无人值守脚本回传结果。
不需要平台登录 token，只需要服务器 .env 中的 EXTERNAL_TRIGGER_TOKEN。
```

接口：

```text
POST /api/v1/test-tasks/by-code/{task_code}/results/batch
Header: X-Automation-Token: 服务器 .env 中的 EXTERNAL_TRIGGER_TOKEN
```

请求示例：

```json
{
  "trigger_type": "ci",
  "environment_id": 1,
  "summary": {
    "tool": "pytest",
    "build_no": "20260707.2"
  },
  "results": [
    {
      "result_type": "api",
      "status": "passed",
      "duration_ms": 320,
      "case_type": "api",
      "case_id": 1,
      "assertions": [
        { "name": "status_code", "passed": true, "expected": 200, "actual": 200 }
      ],
      "logs": "external pytest result"
    }
  ]
}
```

### 8.4 外部脚本回传独立结果

用途：

```text
当外部脚本还没有绑定平台测试任务时，可以先回传独立结果，后续再逐步绑定任务。
```

接口：

```text
POST /api/v1/test-results/external/batch
Header: X-Automation-Token: 服务器 .env 中的 EXTERNAL_TRIGGER_TOKEN
```

## 9. 质量分析接口与压测后判断

### 9.1 质量总览

接口：

```text
GET /api/v1/quality/summary
```

返回重点字段：

```text
pass_rate              通过率
fail_rate              失败率
error_rate             错误率
stability_score        稳定性评分
avg_duration_ms        平均耗时
p95_duration_ms        P95 耗时
p99_duration_ms        P99 耗时
release_risk           发布风险：low / medium / high
release_risk_reasons   风险原因
top_failed_cases       高频失败用例
failure_category_items 失败原因分布
```

### 9.2 质量趋势

接口：

```text
GET /api/v1/reports/quality-trend
```

用途：

```text
压测或自动化回归后，观察最近批次的通过率、失败率、耗时和风险变化。
如果连续多个批次 release_risk 为 high，说明质量风险不是偶发，需要定位失败原因或环境稳定性。
```

### 9.3 JMeter 结果回传建议

JMeter 压测结束后，可以通过结果回传接口写入性能指标：

```json
{
  "trigger_type": "ci",
  "summary": {
    "tool": "jmeter",
    "scene": "login-load-test"
  },
  "results": [
    {
      "result_type": "performance",
      "status": "passed",
      "duration_ms": 60000,
      "metrics": {
        "avg_ms": 320,
        "p95_ms": 900,
        "p99_ms": 1300,
        "error_rate": 0.02,
        "tps": 120,
        "samples": 7200,
        "concurrency": 50
      },
      "logs": "JMeter summary report path or brief conclusion"
    }
  ]
}
```

这样质量分析页会把性能结果纳入结果类型分布、稳定性和风险判断。

### 9.4 性能结果总览

接口：

```text
GET /api/v1/performance-results/summary
```

用途：

```text
JMeter、PTS、Locust 或自研脚本回传 result_type=performance 后，可以通过该接口查看性能结果汇总。
结果中心页面也会调用该接口，展示平均响应、P95、P99、TPS、错误率、样本数和风险提示。
```

平台推荐 metrics 字段：

```text
avg_ms       平均响应时间，单位毫秒
p95_ms       P95 响应时间，单位毫秒
p99_ms       P99 响应时间，单位毫秒
tps          每秒请求数或吞吐量
error_rate   错误率，建议用百分比；0.02 这种小数会按 2% 归一化
samples      样本数
concurrency  并发数
```

为了兼容不同压测工具，平台也支持这些别名：

```text
avg / avg_response_time / average_response_time
p95 / percentile_95 / pct95
p99 / percentile_99 / pct99
throughput / rps / requests_per_second
error_rate_percent / errors_percent / failure_rate
sample_count / count / total / requests
threads / users / virtual_users / vus
```

压测后查看方式：

```text
1. 回传性能结果。
2. 打开平台“结果中心”，查看“性能结果概览”和“性能结果”表格。
3. 打开“测试报告”，进入对应批次报告查看性能摘要。
4. 导出 HTML 批次报告时，性能摘要会一起写入报告。
```

### 9.5 JMeter 报告附件上传

当 JMeter 生成 HTML 报告、`.jtl` 结果文件、HAR 或日志后，可以把这些文件作为证据上传到结果中心。

登录用户上传：

```text
POST /api/v1/attachments
Authorization: Bearer <登录 token>
Content-Type: multipart/form-data
```

外部脚本上传：

```text
POST /api/v1/attachments/external
Header: X-Automation-Token: 服务器 .env 中的 EXTERNAL_TRIGGER_TOKEN
Content-Type: multipart/form-data
```

FormData 字段：

```text
file             必填，附件文件
result_id        可选，绑定到某条测试结果
batch_id         可选，绑定到某个执行批次
attachment_type  建议填 performance_report、log、har、screenshot、recording、other
```

查询附件：

```text
GET /api/v1/attachments?result_id=结果ID
GET /api/v1/attachments?batch_id=批次ID
```

下载附件：

```text
GET /api/v1/attachments/{attachment_id}/download
```

安全注意：

```text
附件上传有大小限制，配置项是服务器 .env 中的 RESULT_ATTACHMENT_MAX_MB。
不要把包含密码、token、身份证号、手机号等敏感信息的日志上传到平台。
JMeter 压测不要并发大量上传大文件，建议压测结束后只上传最终报告。
```

## 10. Webhook 通知接口

### 10.1 配置 Webhook

接口：

```text
GET/POST/PUT/DELETE /api/v1/integrations/webhooks
POST /api/v1/integrations/webhooks/{webhook_id}/test
```

订阅事件：

```text
batch_finished  批次完成
task_failed     任务失败
quality_risk    质量风险
```

说明：

```text
订阅事件留空表示接收全部事件。
点击“测试”会发送 webhook_test，用于验证地址是否可达。
Webhook 地址必须是公网 HTTP/HTTPS，平台会阻断 localhost、内网 IP 和云元数据地址。
```

### 10.2 通用 Webhook 收到的 JSON

```json
{
  "event": "batch_finished",
  "integration_type": "webhook",
  "sent_at": "2026-07-07T12:00:00+00:00",
  "data": {
    "batch_id": 1,
    "batch_no": "BT-20260707120000-abcd1234",
    "task_id": 2,
    "status": "failed",
    "total_count": 3,
    "passed_count": 2,
    "failed_count": 1,
    "skipped_count": 0,
    "duration_ms": 1200,
    "report_url": "http://111.229.178.141/api/reports/batches/1"
  }
}
```

### 10.3 钉钉 / 企微 / 飞书

```text
integration_type 填 dingtalk 或 wechat 时，平台发送 text 消息。
integration_type 填 feishu 时，平台发送飞书 text 消息。
如果机器人需要签名，建议把密钥放在服务器环境变量里，并在 secret_name 填变量名。
```
