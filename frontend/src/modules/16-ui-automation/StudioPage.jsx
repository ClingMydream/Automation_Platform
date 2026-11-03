import React, { useEffect, useLayoutEffect, useRef, useState } from "react";
import {
  Alert,
  Button,
  Checkbox,
  ConfigProvider,
  Empty,
  Input,
  Modal,
  Progress,
  Select,
  Space,
  Spin,
  Tag,
  message,
} from "antd";
import {
  Play,
  RefreshCw,
  ChevronRight,
  Check,
  Image,
  Film,
  ArrowUp,
  ArrowDown,
  Plus,
  Trash2,
  Settings2,
} from "lucide-react";
import "./studio.css";
import { StudioDataSets } from "./StudioDataSets.jsx";
const API = "/v1/ui-automation";
const BRANCH = "dev-20260930-1.9.2";
const ACTION_LABELS = {
  login: "账号登录",
  home: "进入首页",
  create_post: "发布私密动态",
  verify_post: "核对本次动态",
  own_post: "定位本人的测试动态",
  delete_post: "删除本次动态",
  like: "点赞本人动态",
  comment: "评论本人动态",
  favorite: "收藏本人动态",
  friend: "添加好友（已有则先删除）",
  delete_friend: "删除测试好友",
  chat: "向小秘书发送消息",
  daily_task: "签到与浇水",
  profile: "修改头像与签名",
  click: "点击元素",
  fill: "输入内容",
  press: "键盘操作",
  assert_visible: "检查元素可见",
  assert_text: "检查元素文本",
  open: "打开应用内页面",
};
const labels = {
  passed: "通过",
  failed: "失败",
  running: "执行中",
  queued: "排队中",
  interrupted: "未完成",
  blocked: "前置条件未满足",
};

function Evidence({ client, item }) {
  const [url, setUrl] = useState(""),
    [error, setError] = useState("");
  useEffect(() => {
    let alive = true,
      objectUrl;
    setUrl("");
    setError("");
    if (item)
      client
        .download(item.url)
        .then(({ blob }) => {
          objectUrl = URL.createObjectURL(blob);
          if (alive) setUrl(objectUrl);
          else URL.revokeObjectURL(objectUrl);
        })
        .catch((e) => {
          if (alive) setError(e.message);
        });
    return () => {
      alive = false;
      if (objectUrl) URL.revokeObjectURL(objectUrl);
    };
  }, [item?.id]);
  if (error)
    return <Alert type="error" title="证据读取失败" description={error} />;
  if (!item) return <Empty description="执行后展示关键截图、失败截图与录屏" />;
  if (!url) return <Spin />;
  return (
    <div>
      {item.kind === "video" ? (
        <video src={url} controls playsInline />
      ) : (
        <img src={url} alt={item.name} />
      )}
      <a className="studio-download" href={url} download={item.name}>
        {item.kind === "video" ? "保存录屏" : "保存截图"}
      </a>
    </div>
  );
}

export function ArtifactViewer({ client, artifact }) {
  return (
    <div className="studio-media">
      <Evidence client={client} item={artifact} />
    </div>
  );
}

export function UiAutomationPage({ client, onClose }) {
  const [data, setData] = useState({ cases: [], runs: [], actions: [] }),
    [datasets, setDatasets] = useState([]),
    [dataset, setDataset] = useState(null);
  const [active, setActive] = useState(null),
    [draft, setDraft] = useState(null),
    [selected, setSelected] = useState([]),
    [query, setQuery] = useState("");
  const [run, setRun] = useState(null),
    [artifactId, setArtifactId] = useState(null),
    [error, setError] = useState(""),
    [busy, setBusy] = useState(false),
    [saving, setSaving] = useState(false),
    [loading, setLoading] = useState(true);
  const [target, setTarget] = useState(""),
    [viewport, setViewport] = useState("mobile"),
    [config, setConfig] = useState(false),
    [mode, setMode] = useState("cases");
  const lock = useRef(false),
    poll = useRef(null),
    workspace = useRef(null);
  useLayoutEffect(() => {
    const element = workspace.current;
    if (!element) return;
    const measure = () => {
      const top = element.getBoundingClientRect().top + window.scrollY;
      const height = Math.max(420, window.innerHeight - top - 16);
      element.style.setProperty("--studio-height", height + "px");
    };
    measure();
    window.addEventListener("resize", measure);
    const observer = new ResizeObserver(measure);
    observer.observe(element.parentElement);
    return () => {
      window.removeEventListener("resize", measure);
      observer.disconnect();
    };
  }, []);
  async function load() {
    setError("");
    setLoading(true);
    try {
      const [d, sets] = await Promise.all([
        client.get(API + "/studio"),
        client.get(API + "/data-sets"),
      ]);
      setData(d);
      setDatasets(sets);
      setDataset((v) => v || sets.find((s) => s.is_default)?.id || sets[0]?.id);
      setActive((v) => v || d.cases[0]?.id);
      setSelected((v) => (v.length ? v : d.cases.map((c) => c.id)));
      if (!run && d.runs[0]) setRun(d.runs[0]);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }
  useEffect(() => {
    load();
    return () => clearTimeout(poll.current);
  }, []);
  useEffect(() => {
    setDraft(structuredClone(data.cases.find((c) => c.id === active) || null));
    workspace.current
      ?.querySelectorAll(
        ".studio-editor > .studio-scroll,.studio-evidence > .studio-scroll",
      )
      .forEach((element) => {
        element.scrollTop = 0;
      });
  }, [active]);
  useEffect(() => {
    let alive = true;
    clearTimeout(poll.current);
    if (!run?.id || !["queued", "running"].includes(run.status)) return;
    async function read() {
      try {
        const result = await client.get(API + "/runs/" + run.id);
        if (alive) {
          setRun(result);
          setError("");
          if (["queued", "running"].includes(result.status))
            poll.current = setTimeout(read, 2000);
        }
      } catch (e) {
        if (alive) {
          setError("执行状态暂不可读：" + e.message);
          poll.current = setTimeout(read, 5000);
        }
      }
    }
    poll.current = setTimeout(read, 1000);
    return () => {
      alive = false;
      clearTimeout(poll.current);
    };
  }, [run?.id, run?.status]);
  const running = busy || ["queued", "running"].includes(run?.status);
  const dirty =
    draft &&
    JSON.stringify(draft) !==
      JSON.stringify(data.cases.find((c) => c.id === active));
  const report = run?.result_summary?.report;
  const results = run?.result_summary?.case_results || [];
  const currentResult = results.find((r) => r.case_id === active);
  const failedSteps = (run?.result_summary?.timeline || []).filter(
    (t) => t.case_id === active && t.status === 'failed',
  );
  const failedRequests = currentResult?.status === 'failed'
    ? (currentResult.network_issues || run?.result_summary?.network_issues || []).filter(
      (n) => n.case_id === active && failedSteps.some((t) => t.name === n.step),
    ) : [];
  const artifacts = (run?.artifacts || []).filter(
    (a) => a.kind === "video" || a.name.includes(`case-${active}-`),
  );
  const evidence =
    artifacts.find((a) => a.id === artifactId) ||
    artifacts.find((a) => a.name.includes("failure")) ||
    artifacts.find((a) => a.kind === "screenshot") ||
    artifacts[0];
  function choose(id) {
    if (dirty) {
      Modal.confirm({
        title: "当前用例有未保存修改",
        content: "切换会放弃这些修改。",
        okText: "放弃并切换",
        cancelText: "继续编辑",
        onOk: () => setActive(id),
      });
    } else setActive(id);
    setArtifactId(null);
  }
  function changeStep(index, key, value) {
    setDraft((d) => ({
      ...d,
      steps: d.steps.map((s, i) => (i === index ? { ...s, [key]: value } : s)),
    }));
  }
  async function save() {
    if (lock.current) return;
    lock.current = true;
    setSaving(true);
    try {
      const saved = await client.put(API + "/studio/cases/" + active, {
        name: draft.name,
        steps: draft.steps,
      });
      setData((d) => ({
        ...d,
        cases: d.cases.map((c) => (c.id === active ? saved : c)),
      }));
      setDraft(structuredClone(saved));
      message.success("用例已保存");
    } catch (e) {
      setError(e.message);
    } finally {
      lock.current = false;
      setSaving(false);
    }
  }
  async function execute(ids) {
    if (lock.current || running) return;
    if (dirty) {
      message.warning("请先保存用例修改");
      return;
    }
    lock.current = true;
    setBusy(true);
    setError("");
    try {
      const result = await client.post(API + "/studio/runs", {
        branch: BRANCH,
        case_ids: ids,
        data_set_id: dataset,
        viewport,
        target_url: target || null,
      });
      setRun(result);
      setData((d) => ({ ...d, runs: [result, ...d.runs] }));
      setMode("results");
    } catch (e) {
      setError(e.message);
    } finally {
      lock.current = false;
      setBusy(false);
    }
  }
  async function sync() {
    if (lock.current) return;
    lock.current = true;
    setBusy(true);
    try {
      await client.post("/v1/online-preview/sync", { branch: BRANCH });
      message.success("已提交版本同步，请在完成后执行用例");
    } catch (e) {
      setError(e.message);
    } finally {
      lock.current = false;
      setBusy(false);
    }
  }
  function exportReport() {
    const text = [
      "# Emote UI 自动化简短报告",
      `执行：#${run.id} · ${run.branch} · ${run.commit_sha}`,
      `Base URL：${run.result_summary?.base_url || run.result_summary?.target_url || '历史记录未保存'}`,
      `结论：${report?.conclusion || labels[run.status]}`,
      ...results.map(
        (row) =>
          `- ${row.case_name}：${labels[row.status]}${row.reason ? "；" + row.reason : ""}${row.checks?.length ? "；" + row.checks.join("；") : ""}`,
      ),
    ].join("\n\n");
    const url = URL.createObjectURL(
      new Blob([text], { type: "text/markdown;charset=utf-8" }),
    );
    const link = document.createElement("a");
    link.href = url;
    link.download = `Emote-UI-报告-${run.id}.md`;
    link.click();
    window.setTimeout(() => URL.revokeObjectURL(url), 1000);
  }
  return (
    <ConfigProvider
      theme={{
        token: {
          colorPrimary: "#4f775d",
          borderRadius: 10,
          fontSize: 14,
          controlHeight: 40,
        },
      }}
    >
      <main className="emote-studio" data-testid="emote-studio">
        <header className="studio-heading">
          <div>
            <span className="studio-eyebrow">EMOTE / UI STUDIO</span>
            <h1>Emote UI 自动化</h1>
          </div>
          <Space wrap>
            <Button
              onClick={() => setConfig(true)}
              icon={<Settings2 size={16} />}
            >
              执行环境
            </Button>
            <Button
              onClick={load}
              icon={<RefreshCw size={16} />}
              disabled={running || saving}
            >
              刷新
            </Button>
            {onClose && <Button onClick={onClose}>返回</Button>}
          </Space>
        </header>
        {error && (
          <Alert
            type="error"
            title="操作未完成"
            description={error}
            closable
            onClose={() => setError("")}
          />
        )}
        <section className="studio-toolbar">
          <Space wrap>
            <Tag color="blue">1.9.2</Tag>
            <span>测试数据集</span>
            <Select
              aria-label="测试数据集"
              value={dataset}
              onChange={setDataset}
              options={datasets.map((d) => ({ value: d.id, label: d.name }))}
              disabled={running || saving}
              style={{ width: 180, maxWidth: "100%" }}
            />
            <span className="studio-muted">
              {target ? "自定义环境" : "平台测试预览"} ·{" "}
              {viewport === "mobile" ? "移动端" : "桌面端"}
            </span>
          </Space>
          <Button
            type="primary"
            icon={<Play size={16} />}
            loading={busy}
            disabled={running || !selected.length || !dataset}
            onClick={() => execute(selected)}
          >
            运行所选 {selected.length} 项
          </Button>
        </section>
        <div className="studio-workspace" ref={workspace}>
          <aside className="studio-panel studio-catalog">
            <div className="studio-panel-heading">
              <h2>测试场景</h2>
              <Checkbox
                checked={
                  selected.length === data.cases.length && !!selected.length
                }
                onChange={(e) =>
                  setSelected(
                    e.target.checked ? data.cases.map((c) => c.id) : [],
                  )
                }
                disabled={running || saving}
              >
                全选
              </Checkbox>
            </div>
            <Input
              aria-label="搜索用例"
              placeholder="搜索功能或用例"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
            />
            <div className="studio-scroll">
              {loading ? (
                <Spin />
              ) : (
                data.cases
                  .filter((c) => c.name.includes(query))
                  .map((c, index) => {
                    const result = results.find((r) => r.case_id === c.id);
                    return (
                      <div
                        className={
                          "studio-case " + (active === c.id ? "is-active" : "")
                        }
                        key={c.id}
                      >
                        <Checkbox
                          aria-label={"选择" + c.name}
                          checked={selected.includes(c.id)}
                          disabled={running || saving}
                          onChange={(e) =>
                            setSelected((ids) =>
                              e.target.checked
                                ? [...ids, c.id]
                                : ids.filter((id) => id !== c.id),
                            )
                          }
                        />
                        <button
                          onClick={() => choose(c.id)}
                          aria-current={active === c.id ? "page" : undefined}
                        >
                          <span className="studio-case-number">
                            {String(index + 1).padStart(2, "0")}
                          </span>
                          <span>
                            {c.name}
                            <small>
                              {c.steps.length} 个步骤
                              {result ? " · " + labels[result.status] : ""}
                            </small>
                          </span>
                          <ChevronRight size={14} />
                        </button>
                      </div>
                    );
                  })
              )}
            </div>
            <p className="studio-footnote">
              登录态复用 24 小时。独立执行会自动准备登录，从首页开始记录。
            </p>
          </aside>
          <section className="studio-panel studio-editor">
            <div className="studio-panel-heading">
              <div className="studio-tabs">
                <button
                  className={mode === "cases" ? "active" : ""}
                  onClick={() => setMode("cases")}
                >
                  场景编排
                </button>
                <button
                  className={mode === "results" ? "active" : ""}
                  onClick={() => setMode("results")}
                >
                  执行结果
                </button>
              </div>
              {mode === "cases" && (
                <Space>
                  <Button
                    aria-label="保存修改"
                    onClick={save}
                    loading={saving}
                    disabled={!dirty || running}
                  >
                    保存修改
                  </Button>
                  <Button
                    onClick={() => execute([active])}
                    disabled={running || !active || !dataset}
                  >
                    运行当前
                  </Button>
                </Space>
              )}
            </div>
            <div className="studio-scroll">
              {mode === "cases" && draft ? (
                <>
                  <label className="studio-field">
                    用例名称
                    <Input
                      aria-label="用例名称"
                      value={draft.name}
                      disabled={running || saving}
                      onChange={(e) =>
                        setDraft((d) => ({ ...d, name: e.target.value }))
                      }
                    />
                  </label>
                  <div className="studio-callout">
                    只保留业务步骤；登录准备在后台完成。写入操作不自动重试。
                  </div>
                  <ol className="studio-steps">
                    {draft.steps.map((step, index) => (
                      <li key={index}>
                        <span className="studio-step-number">{index + 1}</span>
                        <div className="studio-step-fields">
                          <Input
                            aria-label={`步骤${index + 1}说明`}
                            value={step.label}
                            disabled={running || saving}
                            onChange={(e) =>
                              changeStep(index, "label", e.target.value)
                            }
                          />
                          <Select
                            aria-label={`步骤${index + 1}动作`}
                            value={step.action}
                            options={data.actions.map((a) => ({
                              value: a,
                              label: ACTION_LABELS[a] || a,
                            }))}
                            disabled={running || saving}
                            onChange={(value) =>
                              changeStep(index, "action", value)
                            }
                          />
                          {[
                            "click",
                            "fill",
                            "press",
                            "assert_visible",
                            "assert_text",
                          ].includes(step.action) && (
                            <>
                              <Select
                                aria-label={`步骤${index + 1}定位方式`}
                                value={step.locator_type || "role"}
                                options={[
                                  "role",
                                  "testid",
                                  "placeholder",
                                  "text",
                                  "css",
                                ].map((v) => ({ value: v, label: v }))}
                                onChange={(v) =>
                                  changeStep(index, "locator_type", v)
                                }
                                disabled={running || saving}
                              />
                              {(!step.locator_type ||
                                step.locator_type === "role") && (
                                <Input
                                  aria-label={`步骤${index + 1}元素角色`}
                                  placeholder="角色，例如 button"
                                  value={step.role || "button"}
                                  onChange={(e) =>
                                    changeStep(index, "role", e.target.value)
                                  }
                                  disabled={running || saving}
                                />
                              )}
                              <Input
                                aria-label={`步骤${index + 1}目标元素`}
                                placeholder="元素名称或定位表达式"
                                value={step.locator || ""}
                                onChange={(e) =>
                                  changeStep(index, "locator", e.target.value)
                                }
                                disabled={running || saving}
                              />
                            </>
                          )}
                          {["fill", "press", "assert_text", "open"].includes(
                            step.action,
                          ) && (
                            <Input
                              aria-label={`步骤${index + 1}输入值`}
                              placeholder="输入值，支持 ${timestamp}"
                              value={step.value || ""}
                              onChange={(e) =>
                                changeStep(index, "value", e.target.value)
                              }
                              disabled={running || saving}
                            />
                          )}
                        </div>
                        <Space orientation="vertical">
                          <Button
                            aria-label={"上移步骤" + (index + 1)}
                            icon={<ArrowUp size={14} />}
                            disabled={running || index === 0}
                            onClick={() =>
                              setDraft((d) => {
                                const steps = [...d.steps];
                                [steps[index - 1], steps[index]] = [
                                  steps[index],
                                  steps[index - 1],
                                ];
                                return { ...d, steps };
                              })
                            }
                          />
                          <Button
                            aria-label={"删除步骤" + (index + 1)}
                            icon={<Trash2 size={14} />}
                            disabled={running || draft.steps.length === 1}
                            onClick={() =>
                              setDraft((d) => ({
                                ...d,
                                steps: d.steps.filter((_, i) => i !== index),
                              }))
                            }
                          />
                        </Space>
                      </li>
                    ))}
                  </ol>
                  <Button
                    icon={<Plus size={14} />}
                    disabled={running || saving}
                    onClick={() =>
                      setDraft((d) => ({
                        ...d,
                        steps: [
                          ...d.steps,
                          { action: "home", label: "从首页开始" },
                        ],
                      }))
                    }
                  >
                    添加步骤
                  </Button>
                </>
              ) : null}
              {mode === "results" && (
                <>
                  <Select
                    aria-label="执行历史"
                    value={run?.id}
                    onChange={async (id) => {
                      try {
                        setRun(await client.get(API + "/runs/" + id));
                      } catch (e) {
                        setError(e.message);
                      }
                    }}
                    options={data.runs.map((r) => ({
                      value: r.id,
                      label: `#${r.id} · ${labels[r.status] || r.status}`,
                    }))}
                    style={{ width: "100%" }}
                  />
                  {run ? (
                    <>
                      <div className="studio-summary">
                        <Tag
                          color={
                            run.status === "passed"
                              ? "success"
                              : run.status === "failed"
                                ? "error"
                                : "processing"
                          }
                        >
                          {labels[run.status]}
                        </Tag>
                        <h2>{report?.conclusion || "任务已提交，等待执行"}</h2>
                        <Button onClick={exportReport}>导出简报</Button>
                        {run.error_message && (
                          <Alert
                            type="error"
                            title="执行未完成"
                            description={run.error_message}
                          />
                        )}
                        <p>{run.current_step}</p>
                        <Progress
                          percent={run.progress || 0}
                          status={
                            run.status === "failed" ? "exception" : undefined
                          }
                        />
                        <small>
                          版本 {run.commit_sha?.slice(0, 8)} · 执行 #{run.id}
                        </small>
                      </div>
                      <div className="studio-result-list">
                        {results.map((row) => (
                          <button
                            key={row.case_id}
                            className={"studio-result " + row.status}
                            onClick={() => choose(row.case_id)}
                          >
                            <span>
                              {row.status === "passed" ? (
                                <Check size={18} />
                              ) : (
                                <ChevronRight size={18} />
                              )}
                            </span>
                            <div>
                              <strong>{row.case_name}</strong>
                              <p>
                                {row.reason ||
                                  row.checks?.join("；") ||
                                  "页面操作与结果断言通过"}
                              </p>
                            </div>
                            <Tag>{labels[row.status]}</Tag>
                          </button>
                        ))}
                      </div>
                      {currentResult?.reason && (
                        <Alert
                          type="error"
                          title={currentResult.case_name}
                          description={currentResult.reason}
                        />
                      )}
                      <h3>失败步骤日志</h3>
                      {failedSteps
                        .map((t, i) => (
                          <div
                            className={"studio-timeline " + t.status}
                            key={i}
                          >
                            <span>{labels[t.status]}</span>
                            <strong>{t.name}</strong>
                            <small>{t.duration_ms} ms</small>
                          </div>
                        ))}
                    </>
                  ) : (
                    <Empty description="选择用例后开始第一次运行" />
                  )}
                </>
              )}
            </div>
          </section>
          <aside className="studio-panel studio-evidence">
            <div className="studio-panel-heading">
              <h2>执行证据</h2>
              <span>{artifacts.length} 项</span>
            </div>
            <div className="studio-scroll">
              <div className="studio-media">
                <Evidence client={client} item={evidence} />
              </div>
              <div className="studio-artifacts">
                {artifacts.map((a) => (
                  <Button
                    key={a.id}
                    type={evidence?.id === a.id ? "primary" : "default"}
                    icon={
                      a.kind === "video" ? (
                        <Film size={14} />
                      ) : (
                        <Image size={14} />
                      )
                    }
                    onClick={() => setArtifactId(a.id)}
                  >
                    {a.kind === "video"
                      ? "执行录屏"
                      : a.name.includes("failure")
                        ? "失败截图"
                        : "关键截图"}
                  </Button>
                ))}
              </div>
              <h3>失败日志</h3>
              <p className="studio-muted">
                Base URL：{run?.result_summary?.base_url || run?.result_summary?.target_url || '历史记录未保存'}
              </p>
              {failedRequests
                .map((n, i) => (
                  <details className="studio-network" key={i}>
                    <summary>
                      {n.method} · {n.status || n.category}
                      <span>{n.url}</span>
                    </summary>
                    <pre>{JSON.stringify(n, null, 2)}</pre>
                  </details>
                ))}
              {!failedRequests.length && (
                <p className="studio-footnote">
                  当前场景无失败请求日志。
                </p>
              )}
            </div>
          </aside>
        </div>
        <Modal
          title="执行环境"
          open={config}
          onCancel={() => setConfig(false)}
          onOk={() => setConfig(false)}
          okText="完成"
        >
          <label className="studio-field">
            测试地址（留空使用平台预览）
            <Input
              value={target}
              onChange={(e) => setTarget(e.target.value)}
              placeholder="https://example.com/"
              disabled={running || saving}
            />
          </label>
          <label className="studio-field">
            浏览器视口
            <Select
              value={viewport}
              onChange={setViewport}
              disabled={running || saving}
              options={[
                { value: "mobile", label: "移动端 390 × 844" },
                { value: "desktop", label: "桌面端 1440 × 900" },
              ]}
            />
          </label>
          <StudioDataSets
            client={client}
            items={datasets}
            onChange={(rows) => {
              setDatasets(rows);
              if (!rows.some((d) => d.id === dataset))
                setDataset(
                  rows.find((d) => d.is_default)?.id || rows[0]?.id || null,
                );
            }}
            disabled={running || saving}
          />
          <p>分支：{BRANCH}</p>
          <Button onClick={sync} loading={busy} disabled={running || saving}>
            同步最新分支到预览
          </Button>
          <p className="studio-footnote">
            账号沿用平台已加密保存的测试数据集。日志中的凭据会脱敏。
          </p>
        </Modal>
      </main>
    </ConfigProvider>
  );
}
