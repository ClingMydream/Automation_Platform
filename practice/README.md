# Cling Commerce Lab · 完整业务练习工程

个人工作台内的订单与库存练习子项目。客户商城与运营后台都有实际前端页面，操作调用真实 FastAPI 接口，并持久化到本人独立 SQLite。付款、物流和退款是本地模拟。

## 入口与角色

平台 → 实践实验室 → 练习商店 → 打开独立业务页面。独立入口 `/practice-app` 仍需平台登录态以确定个人数据空间。Swagger `/api/practice/docs`，OpenAPI `/api/practice/openapi.json`。

| 练习账号 | 权限 |
| --- | --- |
| learner | 商城、详情、购物车、结算、自己的订单、地址 |
| buyer_two | 另一客户，用于越权与并发验证 |
| lab_admin | 概览、商品、库存、订单履约、退款审核、审计 |
| warehouse | 概览、库存入库、发货；不能维护商品或审批退款 |

固定练习密码均为 `Practice123!`，不是平台密码。练习 Token 有效一小时，重置后失效。自动化使用 `_auto_customer` 和 `_auto_customer_two` 专用客户，避免清空手动练习账号的购物车。

## 页面与业务

- 商城：关键词、分类、库存筛选、价格排序、分页、缺货状态、详情与数量。
- 购物车：多商品、数量修改后明确保存、移除、金额明细；未保存数量不能结算。
- 地址：增删改查、默认地址、格式校验、版本冲突；订单保存地址快照。
- 结算：服务端核价、事务扣库存、请求幂等；结果未知时保留编号供核对。
- 订单：搜索筛选、详情、价格快照、事件时间线；客户不能读取其他客户订单。
- 商品管理：新增、编辑、上架/下架、版本校验；不硬删除商品。
- 库存：预占、可用库存、账面在库、版本校验入库、流水与 CSV 下载。
- 售后：未发货退款或收货后退货，管理员通过/驳回；收货后必须确认收到退货才回补库存。

```text
商城 → 购物车 → 地址与结算 → 待付款
  ├─ 取消 → 库存释放（仅一次）
  └─ 模拟付款 → 待发货 → 仓库发货 → 客户收货 → 已完成
       └─ 申请退款 / 收货后申请退货 → 管理员审核
            ├─ 通过 → 模拟退款、库存回补（仅一次）
            └─ 驳回 → 回到申请前状态
```

金额用整数分。商品小计满19900分免运费，否则500分模拟运费。客户端不决定实际金额。结算校验购物车版本、报价摘要与地址版本；任一商品缺货会回滚整个订单及所有库存变化。下架商品不能再次购买。

## 数据、升级与固定数据

每个平台账号对应一个独立 SQLite，与平台 MySQL 和 Emote 隔离。保留 v1 `users/products/orders/audit/meta`；新增 `addresses/shopping_carts/cart_items/commerce_orders/commerce_order_items/order_events/inventory_movements`。商品表兼容增加分类、描述与状态。

旧库首次访问时用 SQLite backup API 创建 `.pre-v2.sqlite3` 一致性备份，再增量升级；不删除旧订单，不覆盖原有价格/库存，不改变原 generation。v1接口继续可用，记录在“历史兼容订单”。新表通过业务事务保证对旧商品/用户引用，订单明细与事件使用数据库外键，以兼容旧代码回滚。主动重置才清理本人业务练习数据；平台笔记、学习内容与测试报告保留。

固定12种商品、4个分类，含正常、低库存与缺货商品。原 NOTE-001手账本2900分/20件、LAMP-002阅读灯12900分/5件、BAG-003通勤包8900分/0件保留。客户有固定练习地址；19900000000仅为格式占位，不保证未分配，系统不发送短信、不拨打电话。

## 接口与定位

所有业务使用练习 Token，不能混用平台 Token。以下相对 `/api/practice/v1`：

| 路径 | 用途 |
| --- | --- |
| `/commerce/catalog`、`/commerce/products/{id}` | 商城、详情 |
| `/commerce/products`、`/commerce/products/{id}` | 管理员新增、修改 |
| `/commerce/cart`、`/commerce/cart/items`、`/commerce/cart/items/{id}` | 查询、设置数量、移除 |
| `/commerce/addresses`、`/commerce/addresses/{id}` | 地址增删改查 |
| `/commerce/checkout` | 携带地址版本、购物车版本、报价摘要、提交编号的幂等结算 |
| `/commerce/orders`、`/commerce/orders/{id}` | 订单列表、详情 |
| `/commerce/orders/{id}/{action}` | action为pay/cancel/ship/receive/refund/refund-decision |
| `/commerce/inventory`、`/commerce/inventory/{id}/receipt` | 台账与入库 |
| `/commerce/dashboard` | 角色业务概览 |
| `/products`、`/orders`、`/audit` | v1兼容接口 |

管理接口沿用 `/api/v1/practice-lab`：登录、重置、工程下载、运行、报告。表单/导航有可访问名称，商品卡 `data-testid="product-SKU"`。优先用 get_by_role / get_by_label，避免依赖 CSS。

## 运行参考工程

安装 requirements.txt，本地浏览器测试需 Chromium。平台执行器已包含浏览器。通过环境变量配置，勿提交 Token：

```text
PRACTICE_API_URL=https://你的域名/api/practice/v1
PRACTICE_UI_URL=https://你的域名/practice-app
PRACTICE_ADMIN_TOKEN=练习管理员Token
PRACTICE_CUSTOMER_TOKEN=专用客户Token
PRACTICE_WAREHOUSE_TOKEN=仓库Token
PRACTICE_OTHER_CUSTOMER_TOKEN=另一专用客户Token
CHROMIUM_PATH=Chromium可执行文件路径
```

```bash
python -m pytest tests/test_reference_python.py tests/test_api.py -q
python -m pytest tests/test_ui.py -q
python -m locust -f locustfile.py --headless -u 1 -r 1 --run-time 10s --host "$PRACTICE_API_URL"
```

Windows使用 `$env:变量名` 配置环境，host改为 `$env:PRACTICE_API_URL`。

API工程12项，覆盖Python基础、鉴权、v1兼容、参数、金额、幂等、并发防超卖、购物车、完整履约退货、版本冲突与角色控制。
UI工程4项：客户下单取消与刷新；客户付款→仓库发货→客户收货退货→管理员退款；管理员实际新增商品、入库与下载。以及页面层级、弹窗清理、稳定行定位、刷新和多尺寸检查。客户链路保留录像和关键截图。

工程创建 AUTO/UI 前缀商品并保留订单/审计，只清理专用自动化客户购物车，不清理 learner 手动购物车。请只指向练习环境。Locust仅查询商城，平台限制最多5用户、30秒；结果不能推断生产容量。

## 学习路径与边界

手动走通四角色 → requests接口链路 → pytest参数化/fixture → 权限/幂等/并发 → Playwright跨角色UI → Locust只读压测 → 将结果与自己的改写代码记录到学习笔记。

本期不含真实支付物流、优惠券、促销、供应商采购和分布式库存。订单与库存流水列表最多返回最近300条，适合个人练习，不承担生产经营。

前端结构及定位版本：React + Ant Design Layout/Form/Table/Modal；页面、表格、记录行与弹窗有稳定 data-testid。示例见 tests/test_ui.py 的 test_stable_ui_hierarchy_and_locators。独立页层级与详细规范随平台文档提供：docs/练习子项目前端结构与UI定位规范.md。
