"""Small, executable learning route tied to the real practice project."""
LESSONS = [
 {'id':'python-values','stage':'Python 基础','title':'列表、字典与 JSON','goal':'从商品列表中取出有库存商品的名称。','why':'接口响应通常是列表与字典组合，先理解结构再断言。','example':'import json\nproducts = json.loads(\'[ {"name":"手账本","stock":20} ]\')\nassert isinstance(products, list)\nprint([p["name"] for p in products if p["stock"] > 0])','exercise':'把示例改成只输出库存大于 5 的商品；解释列表与字典取值的区别。','answer':'列表用索引取元素，例如 products[0]；字典用键取值，例如 products[0]["stock"]。筛选条件改为 p["stock"] > 5。','suite':None},
 {'id':'python-functions','stage':'Python 基础','title':'函数与异常处理','goal':'编写金额计算函数，并拒绝不合法的数量。','why':'把校验与计算放进函数，自动化断言才容易复用。','example':'def total(price_cents, quantity):\n    if type(quantity) is not int or quantity <= 0:\n        raise ValueError("quantity must be positive integer")\n    return price_cents * quantity\nassert total(2900, 2) == 5800','exercise':'补充数量为 0、负数、True 时的测试。','answer':'用 try/except ValueError 或 pytest.raises(ValueError) 验证异常；type(x) is int 可以排除 bool。','suite':None},
 {'id':'http-contract','stage':'HTTP 与接口','title':'鉴权、状态码与响应结构','goal':'使用练习 Token 查询商品，并区分 401、403、409、422。','why':'请求成功、权限不足和业务冲突需要分别断言。','example':'import os, requests\nbase = os.environ["PRACTICE_API_URL"]\nresponse = requests.get(base + "/products", headers={"Authorization": "Bearer " + os.environ["PRACTICE_CUSTOMER_TOKEN"]}, timeout=(3, 10))\nresponse.raise_for_status()\nassert isinstance(response.json(), list)','exercise':'去掉 Token 后观察状态码；使用普通用户尝试创建商品。','answer':'未带有效练习会话为 401；普通用户维护商品为 403；库存不足为 409；数量非法为 422。','suite':'api'},
 {'id':'api-orders','stage':'接口自动化','title':'订单与库存断言','goal':'下单前后比较库存与订单金额。','why':'HTTP 201 不能单独证明业务正确，还要验证数据变化。','example':'before = {p["id"]: p["stock"] for p in products}\n# 创建数量为 2 的订单后\nassert order["total_cents"] == order["unit_price_cents"] * 2\n# 重新查询商品后\nassert after[order["product_id"]] == before[order["product_id"]] - 2','exercise':'取消订单后确认库存恢复；再次取消确认没有重复恢复。','answer':'连续两次取消返回 cancelled；库存只增加原订单数量一次。测试需比较取消前、首次取消后、重复取消后三个值。','suite':'api'},
 {'id':'api-idempotency','stage':'接口自动化','title':'幂等与并发库存','goal':'相同请求编号重复下单仍只生成一条订单。','why':'网络重试可能发生；并发请求必须由数据库保证不超卖。','example':'from concurrent.futures import ThreadPoolExecutor\nwith ThreadPoolExecutor(max_workers=4) as pool:\n    responses = list(pool.map(submit_order, range(4)))\nassert sum(r.status_code == 201 for r in responses) <= initial_stock','exercise':'比较相同 request_key 和不同 request_key 的结果。','answer':'相同编号且请求体相同返回同一订单；同编号不同请求体为409。不同编号并发下单的成功总量不能超过库存。','suite':'api'},
 {'id':'ui-workflow','stage':'UI 自动化','title':'商品到订单的页面链路','goal':'用可访问名称定位商品、下单和取消操作。','why':'以用户可见行为断言，减少依赖页面内部结构。','example':'page.get_by_role("tab", name="商品").click()\npage.get_by_role("button", name="下单", exact=True).first.click()\npage.get_by_role("dialog").get_by_role("button", name="确认下单").click()\npage.get_by_role("tab", name="订单").click()','exercise':'验证下单成功提示、订单金额、取消后的状态和库存。','answer':'完整用例应包含商品选择、提交、订单回看、取消及重新查询库存；错误时保留关键截图，不用 force 点击掩盖遮挡。','suite':'ui'},
 {'id':'performance-basics','stage':'性能测试','title':'吞吐、延迟与错误率','goal':'对个人练习环境执行小规模只读压测并解读报告。','why':'平均响应时间会隐藏尾部延迟；吞吐量要结合错误率判断。','example':'from locust import HttpUser, task, between\nclass Reader(HttpUser):\n    wait_time = between(0.2, 0.5)\n    @task\n    def products(self):\n        self.client.get("/products", name="商品查询")','exercise':'先以1用户运行，再以3用户运行；比较RPS、P95和错误率。','answer':'在相近环境条件下比较；P95 是95%请求不超过的延迟。错误率升高时不能把RPS上升当作性能改善。共享服务器的小规模结果不代表生产容量。','suite':'performance'},
]

# Goals use the same case identifiers emitted by the fixed reference runner.
GUIDES = {
 'python-values': {'checks':[], 'steps':['复制示例到 values.py 并运行。','增加库存为0、5、6的商品，改写筛选条件。','记录输出与列表、字典取值的区别。'], 'deliverable':'筛选代码、实际输出，以及你对数据结构的解释。'},
 'python-functions': {'checks':[], 'steps':['运行金额计算函数。','分别传入0、负数和True，确认抛出异常。','记录你如何区分合法整数与布尔值。'], 'deliverable':'函数、三个异常输入及断言结果。'},
 'http-contract': {'checks':[{'name':'test_authentication_and_role','title':'鉴权与角色权限'}], 'steps':['登录个人练习商店，查看普通用户与管理员的区别。','在测试与报告运行接口参考工程。','对照401和403，写下权限判断依据。'], 'deliverable':'状态码观察、权限解释与对应执行记录。'},
 'api-orders': {'checks':[{'name':'test_order_cancel_and_idempotency','title':'下单、幂等、取消与库存恢复'}], 'steps':['在商店完成一次下单与取消，观察库存变化。','运行接口参考验证，定位订单与库存检查项。','记录金额、库存和重复取消的断言。'], 'deliverable':'下单前后与取消后的库存、订单金额及验证记录。'},
 'api-idempotency': {'checks':[{'name':'test_concurrent_inventory_never_negative','title':'并发库存不超卖'},{'name':'test_order_cancel_and_idempotency','title':'重复请求不重复扣减'}], 'steps':['比较相同与不同request_key。','运行接口参考验证，查看并发与幂等两个检查项。','解释为什么不能只根据HTTP状态判断业务正确。'], 'deliverable':'请求编号实验、并发结果与不超卖断言。'},
 'ui-workflow': {'checks':[{'name':'test_shop_order_cancel','title':'页面下单、取消与库存恢复'}], 'steps':['手动走通商品到订单的业务链路。','运行UI参考验证，查看关键截图与视频。','整理定位方式、断言与失败排查方法。'], 'deliverable':'完整页面链路、可访问定位与截图/视频观察。'},
 'performance-basics': {'checks':[], 'steps':['以1用户运行一次只读性能验证。','在相同环境以3用户运行，比较两次结果。','记录请求数、失败数、RPS与P95，说明样本限制。'], 'deliverable':'两次配置和指标对比，以及对尾部延迟的解释。'},
}
for index, lesson in enumerate(LESSONS):
 lesson.update(GUIDES[lesson['id']])
 lesson['next_lesson_id'] = LESSONS[index+1]['id'] if index+1<len(LESSONS) else None
 lesson['verification_scope'] = '平台固定参考工程；不代表你在本机改写的代码已经通过评测' if lesson['suite'] else '本地运行与心得由你确认，不自动判定掌握程度'
# Complete commands target downloadable files; do not show undefined order/page variables.
for lesson in LESSONS:
 if lesson['id']=='api-orders':lesson.update(example='python -m pytest tests/test_api.py -k order_cancel_and_idempotency -q',language='bash')
 if lesson['id']=='api-idempotency':lesson.update(example='python -m pytest tests/test_api.py -k "concurrent or idempotency" -q',language='bash')
 if lesson['id']=='ui-workflow':lesson.update(example='python -m pytest tests/test_ui.py -q',language='bash')
 if lesson['id']=='performance-basics':lesson.update(example='python -m locust -f locustfile.py --headless -u 1 -r 1 --run-time 10s --host "$PRACTICE_API_URL"',language='bash')

# The v2 project adds cart checkout and multi-role fulfilment to chapter verification.
for lesson in LESSONS:
 if lesson['id']=='api-orders':lesson['checks'].append({'name':'test_commerce_order_lifecycle','title':'完整交易、发货收货与退款'})
 if lesson['id']=='api-idempotency':lesson['checks'].append({'name':'test_commerce_concurrent_checkout','title':'购物车结算并发不超卖'})
 if lesson['id']=='ui-workflow':lesson['checks'].append({'name':'test_paid_order_fulfilment_and_return','title':'多角色页面履约与退货退款'})
