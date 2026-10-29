import React, { useEffect, useRef, useState } from "react";
import {
  App,
  Alert,
  Button,
  Card,
  Checkbox,
  Descriptions,
  Empty,
  Form,
  Input,
  Select,
  Space,
  Steps,
  Tag,
  Timeline,
} from "antd";
import {
  ArrowLeft,
  Truck,
  CreditCard,
  RotateCcw,
  CheckCircle,
} from "lucide-react";
import {
  CommerceModal as Modal,
  CommerceTable,
  CommerceSearch,
} from "./CommerceUI.jsx";
import { MONEY, STATUS, COLOR } from "./commerceShared.js";
export function OrderList({ data, session, navigate, fulfillment = false }) {
  const [query, setQuery] = useState(""),
    [status, setStatus] = useState(fulfillment ? "paid" : "");
  const rows = data.orders.filter(
    (row) =>
      (!status || row.status === status) &&
      (!query ||
        (
          row.number +
          " " +
          row.items.map((i) => i.name + " " + i.sku).join(" ")
        )
          .toLowerCase()
          .includes(query.toLowerCase())),
  );
  return (
    <>
      <div
        className="commerce-filters"
        role="search"
        aria-label="订单筛选"
        data-testid="commerce-order-filters"
      >
        <CommerceSearch
          label="搜索订单"
          placeholder="订单编号、商品或 SKU"
          allowClear
          onSearch={setQuery}
        />
        <Select
          aria-label="订单状态筛选"
          value={status}
          onChange={setStatus}
          options={[
            { value: "", label: "全部状态" },
            ...Object.entries(STATUS).map(([value, label]) => ({
              value,
              label,
            })),
          ]}
        />
      </div>
      <Card>
        <CommerceTable
          scope="orders"
          label="订单列表"
          dataSource={rows}
          pagination={{ pageSize: 8, showSizeChanger: false }}
          scroll={{ x: 780 }}
          columns={[
            {
              title: "订单编号",
              dataIndex: "number",
              render: (value, row) => (
                <button
                  className="commerce-text-link"
                  onClick={() => navigate("order", row.id)}
                >
                  {value}
                </button>
              ),
            },
            {
              title: "商品",
              render: (_, r) => (
                <div>
                  {r.items.map((item) => (
                    <small className="commerce-subtext" key={item.id}>
                      {item.name} × {item.quantity}
                    </small>
                  ))}
                </div>
              ),
            },
            { title: "金额", dataIndex: "total_cents", render: MONEY },
            {
              title: "状态",
              dataIndex: "status",
              render: (s) => <Tag color={COLOR[s]}>{STATUS[s] || s}</Tag>,
            },
            ...(session.role !== "customer"
              ? [{ title: "客户", dataIndex: "username" }]
              : []),
            { title: "创建时间（UTC）", dataIndex: "created_at" },
            {
              title: "操作",
              render: (_, r) => (
                <Button onClick={() => navigate("order", r.id)}>
                  查看详情
                </Button>
              ),
            },
          ]}
          locale={{ emptyText: <Empty description="没有符合条件的订单" /> }}
        />
      </Card>
    </>
  );
}
export function OrderDetail({
  identifier,
  data,
  session,
  busy,
  execute,
  navigate,
}) {
  const [order, setOrder] = useState(null),
    [error, setError] = useState(""),
    [loading, setLoading] = useState(true),
    [action, setAction] = useState(""),
    [form] = Form.useForm();
  const { modal } = App.useApp();
  const generation = useRef(0),
    loadedId = useRef("");
  async function load() {
    const current = ++generation.current;
    if (loadedId.current !== identifier) {
      loadedId.current = identifier;
      setOrder(null);
    }
    setLoading(true);
    try {
      const result = await data.client.get("/commerce/orders/" + identifier);
      if (current === generation.current) {
        setOrder(result);
        setError("");
      }
    } catch (e) {
      if (current === generation.current) setError(e.message);
    } finally {
      if (current === generation.current) setLoading(false);
    }
  }
  useEffect(() => {
    load();
    return () => {
      generation.current++;
    };
  }, [identifier, data.orders]);
  async function run(path, body, message) {
    const result = await execute(
      () =>
        data.client.post("/commerce/orders/" + identifier + "/" + path, body),
      message,
    );
    if (result) {
      setOrder(result);
      setAction("");
    }
    return result;
  }
  function confirmCancel() {
    modal.confirm({
      title: "取消待付款订单？",
      content: "预占库存会完整释放，订单记录继续保留。",
      okText: "确认取消订单",
      onOk: () => run("cancel", {}, "订单已取消，库存已释放"),
    });
  }
  function show(kind) {
    form.resetFields();
    setAction(kind);
  }
  async function submit() {
    try {
      const values = await form.validateFields();
      if (action === "ship") await run("ship", values, "模拟发货成功");
      else if (action === "refund")
        await run("refund", values, "退款申请已提交");
      else
        await run(
          "refund-decision",
          {
            approve: action === "approve",
            return_received: !!values.return_received,
            note: values.note,
          },
          action === "approve" ? "模拟退款完成，库存已回补" : "退款申请已驳回",
        );
    } catch {}
  }
  if (error)
    return (
      <Alert
        type="error"
        title={error}
        action={<Button onClick={load}>重新读取订单</Button>}
      />
    );
  if (!order) return <Card loading={loading} />;
  const customer = session.role === "customer",
    operator = session.role === "admin" || session.role === "warehouse",
    admin = session.role === "admin";
  const stage = ["pending_payment", "paid", "shipped", "completed"].indexOf(
    order.status,
  );
  return (
    <>
      <div className="commerce-order-title">
        <Button
          icon={<ArrowLeft size={15} />}
          onClick={() => navigate(operator ? "fulfillment" : "orders")}
        >
          返回订单列表
        </Button>
        <Tag color={COLOR[order.status]}>{STATUS[order.status]}</Tag>
        <strong>{order.number}</strong>
      </div>
      <Card
        className="commerce-order-status"
        data-testid="commerce-order-status"
        data-state={order.status}
        aria-busy={loading}
      >
        <div>
          <span className="commerce-eyebrow">ORDER STATUS</span>
          <h2>{STATUS[order.status]}</h2>
          <p>
            {order.status === "pending_payment"
              ? "订单已创建，库存已预占。可以模拟付款或取消订单。"
              : order.status === "paid"
                ? "模拟付款完成，等待仓库发货。"
                : order.status === "shipped"
                  ? "已模拟发货，客户可以确认收货。"
                  : order.status === "refund_requested"
                    ? "退款申请等待管理员审核。"
                    : "每次状态变化都保留在下方时间线中。"}
          </p>
        </div>
        <Space wrap>
          {customer && order.status === "pending_payment" && (
            <Button
              type="primary"
              icon={<CreditCard size={16} />}
              loading={busy}
              onClick={() => run("pay", {}, "模拟付款成功")}
            >
              模拟付款
            </Button>
          )}
          {order.status === "pending_payment" && (
            <Button disabled={busy} onClick={confirmCancel}>
              取消订单
            </Button>
          )}
          {operator && order.status === "paid" && (
            <Button
              type="primary"
              icon={<Truck size={16} />}
              disabled={busy}
              onClick={() => show("ship")}
            >
              填写发货信息
            </Button>
          )}
          {customer && order.status === "shipped" && (
            <Button
              type="primary"
              icon={<CheckCircle size={16} />}
              loading={busy}
              onClick={() => run("receive", {}, "已确认收货")}
            >
              确认收货
            </Button>
          )}
          {customer && ["paid", "completed"].includes(order.status) && (
            <Button
              icon={<RotateCcw size={16} />}
              disabled={busy}
              onClick={() => show("refund")}
            >
              申请退款
            </Button>
          )}
          {admin && order.status === "refund_requested" && (
            <>
              <Button
                type="primary"
                disabled={busy}
                onClick={() => show("approve")}
              >
                审核通过退款
              </Button>
              <Button disabled={busy} onClick={() => show("reject")}>
                驳回退款
              </Button>
            </>
          )}
        </Space>
      </Card>
      {stage >= 0 && (
        <Card>
          <Steps
            current={stage}
            items={[
              { title: "提交订单" },
              { title: "模拟付款" },
              { title: "仓库发货" },
              { title: "确认收货" },
            ]}
          />
        </Card>
      )}
      <div className="commerce-detail-grid">
        <Card title="商品与费用">
          <CommerceTable
            scope="order-items"
            label="订单商品明细"
            identity="sku"
            dataSource={order.items}
            pagination={false}
            scroll={{ x: 500 }}
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
              { title: "单价", dataIndex: "unit_price_cents", render: MONEY },
              { title: "数量", dataIndex: "quantity" },
              { title: "小计", dataIndex: "total_cents", render: MONEY },
            ]}
          />
          <div className="commerce-money-lines">
            <p>
              商品小计 <strong>{MONEY(order.subtotal_cents)}</strong>
            </p>
            <p>
              运费 <strong>{MONEY(order.shipping_cents)}</strong>
            </p>
            <p>
              订单总额 <strong>{MONEY(order.total_cents)}</strong>
            </p>
          </div>
        </Card>
        <Card title="收货信息与备注">
          <Descriptions
            column={1}
            items={[
              {
                key: "name",
                label: "收件人",
                children: order.address.recipient,
              },
              {
                key: "phone",
                label: "联系电话",
                children: order.address.phone,
              },
              {
                key: "address",
                label: "地址快照",
                children: order.address.region + " · " + order.address.detail,
              },
              {
                key: "remark",
                label: "订单备注",
                children: order.remark || "无",
              },
              {
                key: "tracking",
                label: "模拟运单",
                children: order.tracking_number || "尚未发货",
              },
              {
                key: "refund",
                label: "退款原因",
                children: order.refund_reason || "无",
              },
            ]}
          />
        </Card>
      </div>
      <Card title="订单时间线" data-testid="commerce-order-timeline">
        <Timeline
          items={order.events.map((item) => ({
            key: item.id,
            children: (
              <div
                data-testid={"order-event-" + item.id}
                data-action={item.action}
              >
                <strong>{item.description}</strong>
                <small className="commerce-subtext">
                  {item.actor} · {item.created_at} UTC
                </small>
              </div>
            ),
          }))}
        />
      </Card>
      <Modal
        scope="order-action"
        title={
          action === "ship"
            ? "模拟发货"
            : action === "refund"
              ? "申请退款"
              : action === "approve"
                ? "审核通过退款"
                : "驳回退款申请"
        }
        open={!!action}
        onCancel={() => !busy && setAction("")}
        onOk={submit}
        confirmLoading={busy}
        okText={
          action === "ship"
            ? "确认发货"
            : action === "refund"
              ? "提交退款申请"
              : "提交审核"
        }
      >
        <Form
          name="commerce-order-action"
          data-testid="commerce-order-action-form"
          form={form}
          layout="vertical"
          onFinish={submit}
        >
          {action === "ship" ? (
            <>
              <p>只保存模拟物流信息，不调用真实物流服务。</p>
              <Form.Item
                label="模拟运单号"
                name="tracking_number"
                rules={[
                  {
                    required: true,
                    pattern: /^[A-Za-z0-9-]{8,40}$/,
                    message: "请输入8至40位字母、数字或短横线",
                  },
                ]}
              >
                <Input aria-label="模拟运单号" placeholder="DEMO20261029001" />
              </Form.Item>
            </>
          ) : action === "refund" ? (
            <Form.Item
              label="退款原因"
              name="reason"
              rules={[
                {
                  required: true,
                  min: 5,
                  whitespace: true,
                  message: "请填写至少5字退款原因",
                },
              ]}
            >
              <Input.TextArea aria-label="退款原因" rows={4} maxLength={500} />
            </Form.Item>
          ) : (
            <>
              <Form.Item
                label="审核说明"
                name="note"
                rules={[{ required: true, min: 2, whitespace: true }]}
              >
                <Input.TextArea
                  aria-label="审核说明"
                  rows={3}
                  maxLength={300}
                />
              </Form.Item>
              {action === "approve" && order.refund_from === "completed" && (
                <Form.Item
                  name="return_received"
                  valuePropName="checked"
                  rules={[
                    {
                      validator: (_, value) =>
                        value
                          ? Promise.resolve()
                          : Promise.reject(new Error("请确认退货已收到")),
                    },
                  ]}
                >
                  <Checkbox>已收到退货，可回补库存</Checkbox>
                </Form.Item>
              )}
            </>
          )}
        </Form>
      </Modal>
    </>
  );
}
