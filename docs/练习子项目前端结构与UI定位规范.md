# 练习子项目前端结构与 UI 自动化定位约定

## 技术与结构

沿用平台现有 React + Ant Design 和统一主题，不新增第二套框架。独立页使用 Layout/Header/Sider/Content/Footer；业务使用 Form/Table/Modal/Button/Select 等 Ant Design 组件。保留哈希路由和现有分享入口。

```text
commerce-app（Layout，data-ui-version=1，data-role）
├── commerce-header
├── commerce-sidebar
│   └── commerce-navigation → commerce-nav-{page}
├── commerce-content（独立页 main，内嵌页 region）
│   ├── commerce-page-header → 唯一 h1
│   └── commerce-page-{page}（以 h1 命名的 region）
│       ├── 搜索筛选区域（search landmark）
│       └── 列表/表格 → SKU或业务ID对应的行 → 操作
└── commerce-footer

Modal 保留 Ant Design Portal，在 document 中通过 dialog 的名称定位。
弹窗内有 commerce-{scope}-dialog / form / submit 标识。
```

页面代码已格式化，按 PracticeApp、CommerceShop、CommerceOrders、CommerceAdmin 分开。CommerceUI 集中维护表格/弹窗/搜索通用行为；commerceLocator.js 管理记录行标识与定位版本。响应布局只改变样式，不复制一套手机端导航/操作节点。

## 定位优先级

1. `get_by_role` + 有意义的准确名称（按钮、导航、对话框、标题）。
2. `get_by_label` 定位表单；表单固定 name，输入保留显式 aria-label。
3. `get_by_test_id` 定位业务容器、动态记录与状态。
4. 先限定区域/记录，再找内部操作。不要使用动态样式类、nth-child、整页第几个按钮或坐标。

英文 test ID 是公共约定，文案和布局调整时应继续保留。动态身份必须来自 SKU/记录ID，不能来自显示顺序、昵称或数组下标。`entityTestId` 会 encodeURIComponent 动态值；现有 `product-SKU` 卡片标识继续兼容（SKU限字母数字下划线短横线）。

## 主要固定标识

| 区域 | test ID / 范围 |
| --- | --- |
| 登录 | commerce-login、commerce-login-form、commerce-login-submit |
| 应用与导航 | commerce-app、commerce-navigation、commerce-nav-store/cart/orders/addresses/catalog/inventory/fulfillment/audit/overview/legacy |
| 页面 | commerce-page-store/cart/checkout/orders/order/addresses/catalog/inventory/fulfillment/audit/overview/legacy |
| 商城 | commerce-catalog-filters、commerce-product-list、product-{SKU}、commerce-catalog-pagination |
| 购物车 | commerce-cart-table → cart-row-{SKU} |
| 结算 | commerce-checkout-table → checkout-row-{SKU}、commerce-checkout-addresses → checkout-address-{ID}、commerce-checkout-submit |
| 地址卡片 | address-{ID} |
| 订单 | commerce-orders-table → orders-row-{ID}、commerce-order-status、commerce-order-timeline → order-event-{ID} |
| 订单明细 | commerce-order-items-table → order-items-row-{SKU} |
| 后台商品 | commerce-products-table → products-row-{SKU} |
| 库存 | commerce-inventory-table → inventory-row-{SKU} |
| 库存流水/审计/历史 | commerce-movements/audit/legacy-table → movements/audit/legacy-row-{ID} |
| 公共操作 | commerce-refresh、commerce-logout、commerce-brand |

弹窗 scope：product-detail、address-editor、product-editor、inventory-receipt、order-action。对应 `commerce-{scope}-dialog`，提交按钮 `commerce-{scope}-submit`，取消按钮 `commerce-{scope}-cancel`。详情弹窗没有提交按钮；关闭用 dialog 内 Close 按钮或 Escape。表单固定 name 为 commerce-login/address/product/receipt/order-action；对应 test ID 加 `-form`。

## 等待与状态

- `commerce-content[aria-busy=false]`：顶层读取或写入结束。
- `commerce-page-{page}[data-ready=true]`：本页顶层数据就绪；data-busy表示写入中。
- `commerce-product-list[aria-busy=false]`：商城搜索请求结束。
- `commerce-order-status[data-state=paid]` 等：订单接口返回的真实业务状态，另有 aria-busy。
- 操作后的业务断言和 API/库存断言仍必要，不能把“按钮点到了”当作通过。
- 弹窗关闭后销毁内容，避免隐藏表单/重复字段干扰定位。保留 Ant 的焦点管理、键盘和 Portal。
- 不用固定 sleep 或 force=True 掩盖加载与遮挡；等待元素、状态或对应响应。

## Playwright Python 示例

```python
from playwright.sync_api import expect

app = page.get_by_test_id('commerce-app')
expect(app).to_have_attribute('data-ui-version', '1')
nav = app.get_by_test_id('commerce-navigation')
nav.get_by_test_id('commerce-nav-cart').click()

cart = page.get_by_test_id('commerce-page-cart')
expect(cart).to_have_attribute('data-ready', 'true')
row = cart.get_by_test_id('commerce-cart-table').get_by_test_id('cart-row-NOTE-001')
row.get_by_role('spinbutton', name='购物车数量：NOTE-001', exact=True).fill('2')
row.get_by_role('button', name='更新数量', exact=True).click()
expect(page.get_by_test_id('commerce-content')).to_have_attribute('aria-busy', 'false')
expect(row.get_by_role('spinbutton', name='购物车数量：NOTE-001', exact=True)).to_have_value('2')

# Portal 在页面级查找，不应在业务 page 容器里找弹窗。
dialog = page.get_by_role('dialog', name='新增商品', exact=True)
dialog.get_by_test_id('commerce-product-form').get_by_label('SKU', exact=True).fill('AUTO-001')
# 填完其他必填字段，再提交。
dialog.get_by_test_id('commerce-product-editor-submit').click()
```

参考工程 `practice/tests/test_ui.py` 的 `test_stable_ui_hierarchy_and_locators` 提供可执行示例，实际验证层级、弹窗清理、刷新、响应布局、标识唯一性。建议后续将常用业务动作收拢进 Page Object，保持定位集中维护。

## 本轮验收

真实 UI 工程4项：下单取消、跨角色履约退款、后台商品入库导出、层级与稳定定位；前端单元12项、构建及85组独立页布局回归。应用提交765a9b4已于2026-10-29部署。远端隔离验收：API #12共12项通过，UI #13共4项通过（含test_stable_ui_hierarchy_and_locators），性能 #14通过；无未处理页面异常。验收账号已停用，临时凭据已清理，8个服务健康。备份在 /opt/cling-backups/765a9b4-20261029T093716Z。

首轮发现 Ant Layout 的内容宽度默认规则与原网格冲突，已明确修正内容宽度并重跑。定位约定只约束公开业务容器，不承诺第三方组件内部 DOM 永不变化。

结果证据：output/commerce-structure-20261029/remote-results.json；定位检查截图remote-locators.png；商城截图remote-shop.png。旧验收辅助脚本汇总文案仍写UI3项，已核对实际tests数组为4项且全部通过，以明细为准。
