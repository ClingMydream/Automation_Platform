import React, { useState } from "react";
import { Button, Checkbox, Input, Modal, Select, Space, message } from "antd";
export function StudioDataSets({ client, items, onChange, disabled }) {
  const [open, setOpen] = useState(false),
    [id, setId] = useState(null),
    [draft, setDraft] = useState(null),
    [busy, setBusy] = useState(false),
    [error, setError] = useState("");
  function edit(value) {
    setId(value);
    const row = items.find((d) => d.id === value);
    setDraft(
      structuredClone(
        row || {
          name: "",
          is_default: false,
          credentials: { account_a: {}, account_b: {}, smoke: {} },
        },
      ),
    );
    setError("");
  }
  function field(group, key, value) {
    setDraft((d) => ({
      ...d,
      credentials: {
        ...d.credentials,
        [group]: { ...d.credentials[group], [key]: value },
      },
    }));
  }
  async function save() {
    if (busy) return;
    if (!draft.name.trim()) {
      setError("请填写数据集名称");
      return;
    }
    setBusy(true);
    try {
      const body = {
        name: draft.name,
        is_default: draft.is_default,
        credentials: draft.credentials,
      };
      const result = id
        ? await client.put("/v1/ui-automation/data-sets/" + id, body)
        : await client.post("/v1/ui-automation/data-sets", body);
      onChange(
        id ? items.map((d) => (d.id === id ? result : d)) : [...items, result],
      );
      message.success("数据集已保存");
      setOpen(false);
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  }
  function remove() {
    Modal.confirm({
      title: "删除这个测试数据集？",
      content: "已有执行记录会保留。",
      okText: "删除",
      okButtonProps: { danger: true, 'aria-label':'确认删除数据集' },
      onOk: async () => {
        try {
          await client.delete("/v1/ui-automation/data-sets/" + id);
          onChange(items.filter((d) => d.id !== id));
          edit(null);
        } catch (e) {
          setError(e.message);
          message.error(e.message);
        }
      },
    });
  }
  return (
    <>
      <Button
        disabled={disabled}
        onClick={() => {
          edit(items[0]?.id || null);
          setOpen(true);
        }}
      >
        管理测试账号
      </Button>
      <Modal
        title="测试数据集"
        open={open}
        onCancel={() => !busy && setOpen(false)}
        footer={
          <Space>
            {id && (
              <Button aria-label="删除数据集" danger onClick={remove} disabled={busy}>
                删除
              </Button>
            )}
            <Button onClick={() => setOpen(false)} disabled={busy}>
              取消
            </Button>
            <Button type="primary" onClick={save} loading={busy}>
              保存数据集
            </Button>
          </Space>
        }
      >
        {draft && (
          <>
            <Space style={{ marginBottom: 20 }} wrap>
              <Select
                aria-label="编辑数据集"
                value={id}
                options={items.map((d) => ({ value: d.id, label: d.name }))}
                onChange={edit}
                style={{ minWidth: 200 }}
                disabled={busy}
              />
              <Button onClick={() => edit(null)} disabled={busy}>
                新增
              </Button>
            </Space>
            <label className="studio-field">
              名称
              <Input
                value={draft.name}
                onChange={(e) =>
                  setDraft((d) => ({ ...d, name: e.target.value }))
                }
              />
            </label>
            {["account_a", "account_b"].map((group, index) => (
              <div key={group}>
                <h4>
                  账号 {index ? "B · 专用好友测试账号" : "A · 主测试账号"}
                </h4>
                <Input
                  aria-label={"账号" + (index ? "B" : "A")}
                  value={draft.credentials[group]?.username || ""}
                  onChange={(e) => field(group, "username", e.target.value)}
                  placeholder="手机号 / 账号"
                />
                <Input.Password
                  aria-label={"密码" + (index ? "B" : "A")}
                  value={draft.credentials[group]?.password || ""}
                  onChange={(e) => field(group, "password", e.target.value)}
                  autoComplete="new-password"
                  style={{ margin: "10px 0 18px" }}
                />
              </div>
            ))}
            <label className="studio-field">
              好友搜索名称（可选）
              <Input
                value={draft.credentials.smoke?.friend_name || ""}
                onChange={(e) => field("smoke", "friend_name", e.target.value)}
              />
            </label>
            <Checkbox
              checked={draft.is_default}
              onChange={(e) =>
                setDraft((d) => ({ ...d, is_default: e.target.checked }))
              }
            >
              设为默认数据集
            </Checkbox>
            <p className="studio-footnote">
              已有密码显示为
              ******；保持此值即可保留原密码。仅使用专用测试账号。
              添加好友遇到已有关系时会先删除再申请；删除好友用例也会清除 A、B 间的聊天记录。请勿配置日常账号。
            </p>
            {error && <p role="alert">{error}</p>}
          </>
        )}
      </Modal>
    </>
  );
}
