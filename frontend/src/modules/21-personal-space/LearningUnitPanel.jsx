import React, { useEffect, useRef, useState } from "react";
import {
  App,
  Alert,
  Button,
  Card,
  Collapse,
  Empty,
  Input,
  Select,
  Space,
  Spin,
  Tag,
  Progress,
} from "antd";
import { MarkdownView } from "./MarkdownView.jsx";
import { requestId } from "../../shared/requestId.js";
import { firstUnit, learningUnits, loadLearningUnit } from "./learningUnits.js";
import { useRouteSearch } from "../../shared/useRouteSearch.js";

const API = "/v1/personal-workspace/records";
const marker = "\n\n## 我的学习记录\n";
export function LearningUnitPanel(props) {
  const params = useRouteSearch();
  const [query, setQuery] = useState(""),
    [busy, setBusy] = useState(false),
    [notes, setNotes] = useState([]),
    [progressError, setProgressError] = useState(""),
    [openGroups, setOpenGroups] = useState([]);
  const unit =
    learningUnits.find((x) => x.id === params.get("unit")) ||
    learningUnits.find((x) => x.id === firstUnit.id);
  useEffect(() => {
    setOpenGroups([unit.group]);
  }, [unit.group]);
  useEffect(() => {
    let alive = true;
    props.client
      .get(
        API +
          "?kind=note&q=" +
          encodeURIComponent("学习单元｜") +
          "&limit=1000",
      )
      .then((rows) => {
        if (alive) setNotes(rows);
      })
      .catch((e) => {
        if (alive) setProgressError(e.message);
      });
    return () => {
      alive = false;
    };
  }, [props.userKey]);
  const done = new Set(
    notes
      .filter((n) => n.status === "done")
      .flatMap((n) =>
        n.tags
          .filter((t) => t.startsWith("learning-unit:"))
          .map((t) => t.slice(14)),
      ),
  );
  const groups = [...new Set(learningUnits.map((x) => x.group))];
  const index = learningUnits.findIndex((x) => x.id === unit.id);
  function choose(id) {
    props.onNavigate("learning_route", { unit: id });
  }
  return (
    <div className="link-learning" data-testid="link-learning">
      <header className="link-learning-header">
        <div>
          <Tag color="blue">按链接学习</Tag>
          <h2>把一节课，真正学会。</h2>
          <p>理解 → 运行 → 改写 → 自测 → 复习</p>
        </div>
        <Button onClick={props.onHistory} disabled={busy}>
          历史学习记录
        </Button>
      </header>
      <div className="link-learning-layout">
        <aside aria-label="课程与学习单元">
          <Card title="零基础学 Python（新版）">
            {progressError && (
              <Alert
                type="warning"
                title="课程进度暂不可读"
                description={progressError}
              />
            )}
            <p>
              已完成 {learningUnits.filter((x) => done.has(x.id)).length} /{" "}
              {learningUnits.length} 单元（自己确认）
            </p>
            <Progress
              percent={Math.round(
                (learningUnits.filter((x) => done.has(x.id)).length /
                  learningUnits.length) *
                  100,
              )}
            />
            <Input
              aria-label="搜索学习单元"
              placeholder="搜索标题或章节"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
            />
            <div className="learning-unit-catalog">
              {!learningUnits.some((u) =>
                (u.title + u.group).toLowerCase().includes(query.toLowerCase()),
              ) && <Empty description="没有匹配的学习单元" />}
              <Collapse
                onChange={setOpenGroups}
                activeKey={query ? groups : openGroups}
                items={groups
                  .filter((g) =>
                    learningUnits.some(
                      (u) =>
                        u.group === g &&
                        (u.title + g)
                          .toLowerCase()
                          .includes(query.toLowerCase()),
                    ),
                  )
                  .map((g) => ({
                    key: g,
                    label: g,
                    children: learningUnits
                      .filter(
                        (u) =>
                          u.group === g &&
                          (u.title + g)
                            .toLowerCase()
                            .includes(query.toLowerCase()),
                      )
                      .map((u) => (
                        <Button
                          block
                          key={u.id}
                          data-testid={"learning-nav-" + u.id}
                          disabled={busy}
                          aria-current={unit.id === u.id ? "page" : undefined}
                          type={unit.id === u.id ? "primary" : "text"}
                          onClick={() => choose(u.id)}
                        >
                          {done.has(u.id) ? "✓ " : ""}
                          {u.title}
                        </Button>
                      )),
                  }))}
              />
            </div>
          </Card>
          <Card title="学习建议">
            <p>
              每天学习1—2讲。先运行示例，再改变一个输入观察结果；每章总结课做一次闭卷复习。
            </p>
            <p>
              原课程归纳与补充测试练习分开标明。代码环境与外部服务条件请先阅读。
            </p>
          </Card>
        </aside>
        <section aria-label="学习单元内容" data-testid="learning-unit-content">
          <UnitContent
            key={props.userKey + unit.id}
            {...props}
            metadata={unit}
            onBusy={setBusy}
            onSaved={(note) =>
              setNotes((rows) => [
                note,
                ...rows.filter((r) => r.id !== note.id),
              ])
            }
          />
          <Space wrap>
            <Button
              disabled={busy || index === 0}
              onClick={() => choose(learningUnits[index - 1].id)}
            >
              上一单元
            </Button>
            <Button
              disabled={busy || index === learningUnits.length - 1}
              onClick={() => choose(learningUnits[index + 1].id)}
            >
              下一单元
            </Button>
          </Space>
        </section>
      </div>
    </div>
  );
}
function UnitContent({
  client,
  userKey,
  onNavigate,
  metadata,
  onBusy,
  onSaved,
}) {
  const [unit, setUnit] = useState(null),
    [contentError, setContentError] = useState("");
  useEffect(() => {
    let alive = true;
    loadLearningUnit(metadata.id)
      .then((value) => {
        if (alive) setUnit(value);
      })
      .catch((e) => {
        if (alive) setContentError(e.message);
      });
    return () => {
      alive = false;
    };
  }, [metadata.id]);
  if (contentError)
    return (
      <Alert
        type="error"
        title="单元资料加载失败"
        description={contentError}
        action={<Button onClick={() => location.reload()}>重新加载</Button>}
      />
    );
  return unit ? (
    <UnitForm
      key={unit.id}
      {...{ client, userKey, onNavigate, unit, onBusy, onSaved }}
    />
  ) : (
    <Spin />
  );
}
function UnitForm({ client, userKey, onNavigate, unit, onBusy, onSaved }) {
  const tag = "learning-unit:" + unit.id,
    title = "学习单元｜" + unit.title;
  const answerHeading = "## 参考答案（练习时先自己回答）";
  const [beforeAnswer, tail = ""] = unit.body.split(answerHeading),
    [answer, ...remaining] = tail.split("## 与测试工作的联系");
  const { message } = App.useApp();
  const [note, setNote] = useState(null),
    [text, setText] = useState(""),
    [status, setStatus] = useState("open");
  const [loading, setLoading] = useState(true),
    [busy, setBusy] = useState(false),
    [error, setError] = useState(""),
    [draftWarning, setDraftWarning] = useState(""),
    [loadFailed, setLoadFailed] = useState(false);
  const lock = useRef(false),
    key = useRef(requestId());
  const storage = "cling:learning-unit:" + userKey + ":" + unit.id;
  useEffect(() => {
    let alive = true;
    setLoading(true);
    client
      .get(API + "?kind=note&q=" + encodeURIComponent(title))
      .then((rows) => {
        if (!alive) return;
        const saved = rows.find((row) => row.tags.includes(tag));
        setNote(saved || null);
        let local;
        try {
          local = JSON.parse(localStorage.getItem(storage) || "null");
        } catch {
          setDraftWarning("无法读取本机草稿，请留意保存状态。");
        }
        const valid =
          local &&
          typeof local.text === "string" &&
          ["open", "doing", "done"].includes(local.status);
        setText(
          valid
            ? local.text
            : saved?.content.split(marker).slice(1).join(marker) || "",
        );
        setStatus(valid ? local.status : saved?.status || "open");
        if (valid)
          setDraftWarning("已恢复本机未提交的学习记录，请核对后保存。");
        setError("");
      })
      .catch((e) => {
        if (alive) {
          setError(e.message);
          setLoadFailed(true);
        }
      })
      .finally(() => {
        if (alive) setLoading(false);
      });
    return () => {
      alive = false;
    };
  }, [userKey]);
  function draft(nextText, nextStatus) {
    setText(nextText);
    setStatus(nextStatus);
    try {
      localStorage.setItem(
        storage,
        JSON.stringify({ text: nextText, status: nextStatus }),
      );
    } catch {
      setDraftWarning("本机草稿保存失败，请及时保存到笔记本。");
    }
  }
  async function save() {
    if (lock.current) return;
    if (status === "done" && text.trim().length < 10) {
      message.warning("请至少记录10字的学习过程，再标记完成。");
      return;
    }
    lock.current = true;
    setBusy(true);
    onBusy(true);
    setError("");
    const body = {
      kind: "note",
      title,
      content: unit.body + marker + text,
      status,
      tags: [tag, "学习单元", unit.course],
      due_at: null,
      client_request_id: note?.client_request_id || key.current,
    };
    try {
      const result = note
        ? await client.put(API + "/" + note.id, {
            ...body,
            revision: note.revision,
          })
        : await client.post(API, body);
      setNote(result);
      onSaved(result);
      try {
        localStorage.removeItem(storage);
      } catch {}
      setDraftWarning("");
      message.success("学习记录已保存到笔记本");
    } catch (e) {
      setError(
        e.message +
          "；输入仍保留。若提示版本冲突，请先在笔记本核对，避免覆盖其他修改。",
      );
    } finally {
      setBusy(false);
      onBusy(false);
      lock.current = false;
    }
  }
  return (
    <div
      className="learning-unit-detail"
      data-testid="learning-unit-detail"
      data-unit-id={unit.id}
    >
      <Card
        extra={
          <Button href={unit.url} target="_blank" rel="noopener noreferrer">
            {unit.sourceKind === "video" ? "打开原视频" : "打开原课资料"}
          </Button>
        }
        title={unit.title}
      >
        <Alert
          type="info"
          title="个人学习整理"
          description="依据已核对的课程字幕要点或配套内容归纳；示例、练习与测试联系为补充设计。原视频在极客时间播放。"
        />
        <MarkdownView text={beforeAnswer} />
        <Collapse
          items={[
            {
              key: "answer",
              label: "查看参考答案",
              children: <MarkdownView text={answer} />,
            },
          ]}
        />
        <MarkdownView
          text={"## 与测试工作的联系" + remaining.join("## 与测试工作的联系")}
        />
      </Card>
      <Card title="我的学习记录" data-testid="learning-unit-notes">
        {loading ? (
          <Spin />
        ) : (
          <>
            {error && (
              <Alert
                type="error"
                title="保存或读取未完成"
                description={error}
              />
            )}
            {draftWarning && <Alert type="warning" title={draftWarning} />}
            <Input.TextArea
              aria-label="本单元学习记录"
              value={text}
              onChange={(e) => draft(e.target.value, status)}
              rows={6}
              maxLength={10000}
              disabled={busy || loadFailed}
              placeholder="实际命令和输出、遇到的问题、解决方式，还有哪里不理解。"
            />
            {loadFailed && (
              <Button onClick={() => location.reload()}>
                重新读取学习记录
              </Button>
            )}
            <Space wrap>
              <Select
                aria-label="本单元学习状态"
                value={status}
                disabled={busy}
                onChange={(value) => draft(text, value)}
                options={[
                  { value: "open", label: "未开始" },
                  { value: "doing", label: "学习中" },
                  { value: "done", label: "已完成（自己确认）" },
                ]}
              />
              <Button
                type="primary"
                loading={busy}
                onClick={save}
                disabled={loadFailed}
              >
                保存学习记录到笔记本
              </Button>
              {note && (
                <Button
                  onClick={() => onNavigate("knowledge", { record: note.id })}
                >
                  打开关联笔记
                </Button>
              )}
            </Space>
            <p className="personal-footnote">
              {note
                ? "已建立笔记关联；修改后请保存。"
                : "首次保存会在你的笔记本中创建本单元记录。"}
              完成状态由你确认，不表示代码已经自动验证。
            </p>
          </>
        )}
      </Card>
    </div>
  );
}
