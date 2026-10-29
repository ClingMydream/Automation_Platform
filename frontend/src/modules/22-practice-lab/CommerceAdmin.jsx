import React, { useState } from "react";
import {
  Button,
  Card,
  Form,
  Input,
  InputNumber,
  Select,
  Space,
  Tag,
} from "antd";
import {
  Plus,
  Download,
  Boxes,
  ArrowUpRight,
  ShoppingBag,
  PackageCheck,
} from "lucide-react";
import {
  CommerceModal as Modal,
  CommerceTable,
  CommerceSearch,
} from "./CommerceUI.jsx";
import {
  MONEY,
  CATEGORIES,
  STATUS,
  COLOR,
  requestId,
  exportMovements,
} from "./commerceShared.js";
export function Overview({ data, session, navigate }) {
  const d = data.dashboard,
    customer = session.role === "customer";
  const cards = [
    ["订单总数", d.orders, ShoppingBag],
    ["已付款金额", MONEY(d.paid_cents), PackageCheck],
    ["在售商品", d.products, Boxes],
    ["低库存商品", d.low_stock, ArrowUpRight],
  ];
  return (
    <>
      <div className="commerce-overview-welcome">
        <span className="commerce-eyebrow">WORKFLOW / OVERVIEW</span>
        <h2>
          {customer
            ? "你的每一笔订单，都有迹可循。"
            : "从商品到履约，在一个工作台协作。"}
        </h2>
        <p>{d.scope} · 本系统为隔离练习环境，付款与物流均为模拟。</p>
        <Button
          type="primary"
          onClick={() => navigate(customer ? "store" : "fulfillment")}
        >
          {customer ? "去商城挑选" : "处理业务订单"}
        </Button>
      </div>
      <div className="commerce-stat-grid">
        {cards.map(([label, value, Icon]) => (
          <Card key={label}>
            <Icon size={20} />
            <span>{label}</span>
            <strong>{value}</strong>
          </Card>
        ))}
      </div>
      <Card title="订单处理进度">
        <div className="commerce-status-grid">
          {Object.entries(STATUS).map(([key, label]) => (
            <button
              key={key}
              onClick={() => navigate(customer ? "orders" : "fulfillment")}
            >
              <Tag color={COLOR[key]}>{label}</Tag>
              <strong>{d.statuses[key] || 0}</strong>
            </button>
          ))}
        </div>
      </Card>
      <Card title="业务练习建议">
        <ol className="commerce-workflow-list">
          {(customer
            ? [
                "浏览分类与商品详情，将多种商品加入购物车。",
                "新增地址，在结算页核对商品、运费和应付金额。",
                "模拟付款，切换仓库账号发货，再回到客户确认收货。",
                "申请退款，由管理员审核；观察库存与事件记录。",
              ]
            : [
                "维护商品信息，测试价格版本冲突与下架影响。",
                "完成入库并查看库存流水、预占数量和余额。",
                "处理已付款订单，检查发货前置条件。",
                "审核退款，核对退货收到后库存只回补一次。",
              ]
          ).map((text) => (
            <li key={text}>{text}</li>
          ))}
        </ol>
      </Card>
    </>
  );
}
export function ProductAdmin({ data, busy, execute }) {
  const [query, setQuery] = useState(""),
    [category, setCategory] = useState(""),
    [status, setStatus] = useState(""),
    [editing, setEditing] = useState(null),
    [open, setOpen] = useState(false),
    [form] = Form.useForm();
  const rows = data.products.filter(
    (row) =>
      (!query ||
        (row.name + " " + row.sku)
          .toLowerCase()
          .includes(query.toLowerCase())) &&
      (!category || row.category === category) &&
      (!status || row.status === status),
  );
  function edit(row) {
    setEditing(row);
    form.resetFields();
    form.setFieldsValue(
      row || { category: CATEGORIES[0], stock: 0, status: "active" },
    );
    setOpen(true);
  }
  async function save() {
    try {
      const v = await form.validateFields();
      const body = editing
        ? {
            name: v.name,
            category: v.category,
            description: v.description || "",
            price_cents: v.price_cents,
            status: v.status,
            version: editing.version,
          }
        : {
            sku: v.sku,
            name: v.name,
            category: v.category,
            description: v.description || "",
            price_cents: v.price_cents,
            stock: v.stock,
          };
      const result = await execute(
        () =>
          editing
            ? data.client.put("/commerce/products/" + editing.id, body)
            : data.client.post("/commerce/products", body),
        editing ? "商品信息已保存" : "商品已创建",
      );
      if (result) setOpen(false);
    } catch {}
  }
  return (
    <>
      <div className="commerce-section-toolbar">
        <div className="commerce-filters" role="search" aria-label="后台筛选">
          <CommerceSearch
            label="搜索后台商品"
            placeholder="商品名称或 SKU"
            allowClear
            onSearch={setQuery}
          />
          <Select
            aria-label="后台商品分类"
            value={category}
            onChange={setCategory}
            options={[
              { value: "", label: "全部分类" },
              ...CATEGORIES.map((value) => ({ value, label: value })),
            ]}
          />
          <Select
            aria-label="商品上架状态"
            value={status}
            onChange={setStatus}
            options={[
              { value: "", label: "全部状态" },
              { value: "active", label: "上架中" },
              { value: "inactive", label: "已下架" },
            ]}
          />
        </div>
        <Button
          type="primary"
          icon={<Plus size={16} />}
          onClick={() => edit(null)}
        >
          新增商品
        </Button>
      </div>
      <Card>
        <CommerceTable
          scope="products"
          label="商品管理列表"
          identity="sku"
          dataSource={rows}
          pagination={{ pageSize: 8, showSizeChanger: false }}
          scroll={{ x: 850 }}
          columns={[
            {
              title: "商品",
              dataIndex: "name",
              render: (v, r) => (
                <div>
                  <strong>{v}</strong>
                  <small className="commerce-subtext">{r.sku}</small>
                </div>
              ),
            },
            { title: "分类", dataIndex: "category" },
            {
              title: "价格",
              dataIndex: "price_cents",
              render: MONEY,
              sorter: (a, b) => a.price_cents - b.price_cents,
            },
            { title: "库存", dataIndex: "stock" },
            { title: "版本", dataIndex: "version" },
            {
              title: "状态",
              dataIndex: "status",
              render: (v) => (
                <Tag color={v === "active" ? "green" : "default"}>
                  {v === "active" ? "上架中" : "已下架"}
                </Tag>
              ),
            },
            {
              title: "操作",
              render: (_, r) => (
                <Button onClick={() => edit(r)}>编辑商品</Button>
              ),
            },
          ]}
        />
      </Card>
      <Modal
        scope="product-editor"
        title={editing ? "编辑商品" : "新增商品"}
        open={open}
        onCancel={() => !busy && setOpen(false)}
        onOk={save}
        confirmLoading={busy}
        okText="保存商品"
      >
        <Form
          name="commerce-product"
          data-testid="commerce-product-form"
          form={form}
          layout="vertical"
          onFinish={save}
        >
          <Form.Item
            name="sku"
            label="SKU"
            rules={[
              {
                required: true,
                pattern: /^[A-Za-z0-9_-]+$/,
                message: "只使用字母、数字、下划线与短横线",
              },
            ]}
          >
            <Input aria-label="SKU" disabled={!!editing} maxLength={80} />
          </Form.Item>
          <Form.Item
            name="name"
            label="商品名称"
            rules={[{ required: true, whitespace: true }]}
          >
            <Input aria-label="商品名称" maxLength={160} />
          </Form.Item>
          <Form.Item
            name="category"
            label="商品分类"
            rules={[{ required: true }]}
          >
            <Select
              aria-label="商品分类"
              options={CATEGORIES.map((value) => ({ value, label: value }))}
            />
          </Form.Item>
          <Form.Item
            name="price_cents"
            label="价格（分）"
            rules={[{ required: true }]}
          >
            <InputNumber
              aria-label="价格（分）"
              min={1}
              max={10000000}
              precision={0}
            />
          </Form.Item>
          {!editing && (
            <Form.Item
              name="stock"
              label="初始库存"
              rules={[{ required: true }]}
            >
              <InputNumber
                aria-label="初始库存"
                min={0}
                max={100000}
                precision={0}
              />
            </Form.Item>
          )}
          {editing && (
            <Form.Item name="status" label="上架状态">
              <Select
                aria-label="上架状态"
                options={[
                  { value: "active", label: "上架中" },
                  { value: "inactive", label: "已下架" },
                ]}
              />
            </Form.Item>
          )}
          <Form.Item name="description" label="商品描述">
            <Input.TextArea aria-label="商品描述" rows={3} maxLength={2000} />
          </Form.Item>
          <p className="commerce-muted">
            已有订单保留商品名称与价格快照；版本冲突时不会覆盖其他修改。
          </p>
        </Form>
      </Modal>
    </>
  );
}
export function Inventory({ data, busy, execute }) {
  const [query, setQuery] = useState(""),
    [low, setLow] = useState(false),
    [editing, setEditing] = useState(null),
    [form] = Form.useForm(),
    [key, setKey] = useState("");
  const rows = data.inventory.items.filter(
    (r) =>
      (!query ||
        (r.name + " " + r.sku).toLowerCase().includes(query.toLowerCase())) &&
      (!low || r.stock <= 3),
  );
  function edit(row) {
    setEditing(row);
    setKey(requestId());
    form.resetFields();
  }
  async function save() {
    try {
      const values = await form.validateFields();
      const result = await execute(
        () =>
          data.client.post("/commerce/inventory/" + editing.id + "/receipt", {
            ...values,
            version: editing.version,
            request_key: key,
          }),
        "入库成功，已生成库存流水",
      );
      if (result) setEditing(null);
    } catch {}
  }
  return (
    <>
      <div className="commerce-filters" role="search" aria-label="后台筛选">
        <CommerceSearch
          label="搜索库存商品"
          placeholder="商品名称或 SKU"
          allowClear
          onSearch={setQuery}
        />
        <Select
          aria-label="库存预警筛选"
          value={low ? "low" : "all"}
          onChange={(v) => setLow(v === "low")}
          options={[
            { value: "all", label: "全部库存" },
            { value: "low", label: "低库存（≤3）" },
          ]}
        />
      </div>
      <Card title="库存台账">
        <p className="commerce-muted">
          可用库存会在结算时扣减，取消与退款审核通过后释放；发货不再次扣减。
        </p>
        <CommerceTable
          scope="inventory"
          label="库存台账列表"
          identity="sku"
          dataSource={rows}
          scroll={{ x: 760 }}
          pagination={{ pageSize: 8, showSizeChanger: false }}
          columns={[
            {
              title: "商品",
              dataIndex: "name",
              render: (v, r) => (
                <div>
                  {v}
                  <small className="commerce-subtext">{r.sku}</small>
                </div>
              ),
            },
            {
              title: "可用库存",
              dataIndex: "stock",
              render: (v) => <Tag color={v <= 3 ? "orange" : "green"}>{v}</Tag>,
            },
            { title: "订单预占", dataIndex: "reserved" },
            { title: "账面在库", render: (_, r) => r.stock + r.reserved },
            { title: "版本", dataIndex: "version" },
            {
              title: "操作",
              render: (_, r) => (
                <Button onClick={() => edit(r)}>登记入库</Button>
              ),
            },
          ]}
        />
      </Card>
      <Card
        title="库存流水"
        extra={
          <Button
            icon={<Download size={15} />}
            onClick={() => exportMovements(data.inventory.movements)}
          >
            导出流水 CSV
          </Button>
        }
      >
        <CommerceTable
          scope="movements"
          label="库存流水列表"
          dataSource={data.inventory.movements}
          scroll={{ x: 920 }}
          pagination={{ pageSize: 8, showSizeChanger: false }}
          columns={[
            { title: "商品", dataIndex: "name" },
            {
              title: "变化",
              dataIndex: "delta",
              render: (v) => (
                <span
                  className={v > 0 ? "commerce-positive" : "commerce-negative"}
                >
                  {v > 0 ? "+" : ""}
                  {v}
                </span>
              ),
            },
            { title: "可用余额", dataIndex: "balance" },
            { title: "原因", dataIndex: "reason" },
            { title: "关联编号", dataIndex: "reference" },
            { title: "操作人", dataIndex: "actor" },
            { title: "时间（UTC）", dataIndex: "created_at" },
          ]}
        />
      </Card>
      <Modal
        scope="inventory-receipt"
        title="登记入库"
        open={!!editing}
        onCancel={() => !busy && setEditing(null)}
        onOk={save}
        okText="确认入库"
        confirmLoading={busy}
      >
        <p>
          {editing?.name} · 当前可用库存 {editing?.stock}
        </p>
        <Form
          name="commerce-receipt"
          data-testid="commerce-receipt-form"
          form={form}
          layout="vertical"
          onFinish={save}
        >
          <Form.Item
            label="入库数量"
            name="quantity"
            rules={[{ required: true }]}
          >
            <InputNumber
              aria-label="入库数量"
              min={1}
              max={10000}
              precision={0}
            />
          </Form.Item>
          <Form.Item
            label="入库原因"
            name="reason"
            rules={[{ required: true, min: 2, whitespace: true }]}
          >
            <Input.TextArea aria-label="入库原因" rows={3} maxLength={200} />
          </Form.Item>
        </Form>
      </Modal>
    </>
  );
}
export function Audit({ data }) {
  return (
    <Card title="操作审计">
      <CommerceTable
        scope="audit"
        label="操作审计列表"
        dataSource={data.audit}
        scroll={{ x: 760 }}
        pagination={{ pageSize: 12, showSizeChanger: false }}
        columns={[
          { title: "操作人", dataIndex: "actor" },
          { title: "动作", dataIndex: "action" },
          { title: "关联记录", dataIndex: "detail" },
          { title: "时间（UTC）", dataIndex: "created_at" },
        ]}
      />
    </Card>
  );
}
export function Legacy({ data, busy, execute }) {
  return (
    <Card title="历史兼容订单">
      <p className="commerce-muted">
        v1接口产生的历史记录保留在这里。新版交易使用购物车与完整履约状态。
      </p>
      <CommerceTable
        scope="legacy"
        label="历史订单列表"
        dataSource={data.legacy}
        scroll={{ x: 700 }}
        pagination={{ pageSize: 8, showSizeChanger: false }}
        columns={[
          { title: "编号", dataIndex: "id", render: (v) => v.slice(0, 12) },
          { title: "商品", dataIndex: "product_name" },
          { title: "数量", dataIndex: "quantity" },
          { title: "金额", dataIndex: "total_cents", render: MONEY },
          {
            title: "状态",
            dataIndex: "status",
            render: (v) => (v === "created" ? "已创建" : "已取消"),
          },
          {
            title: "操作",
            render: (_, r) =>
              r.status === "created" ? (
                <Button
                  disabled={busy}
                  onClick={() =>
                    execute(
                      () => data.client.post("/orders/" + r.id + "/cancel", {}),
                      "历史订单已取消",
                    )
                  }
                >
                  取消历史订单
                </Button>
              ) : null,
          },
        ]}
      />
    </Card>
  );
}
