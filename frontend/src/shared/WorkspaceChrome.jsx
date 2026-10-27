import React, { useEffect, useRef, useState } from "react";
import { Modal } from "antd";
import {
  ArrowUpRight,
  ArrowRight,
  Search,
  CornerDownLeft,
  Clock3,
  Command,
  MoveUp,
  MoveDown,
} from "lucide-react";
import {
  BrandMark,
  OrbitArtwork,
  WorkspaceIcon,
} from "./WorkspaceIdentity.jsx";
import {
  MODULE_META,
  SECTION_META,
  readRecentModules,
  searchModules,
} from "./workspaceCatalog.js";

export function useWorkspaceHistory(username, activeKey, items) {
  const [recent, setRecent] = useState([]);
  const signature = items.map((item) => item.key).join("|");
  useEffect(() => {
    if (!username) {
      setRecent([]);
      return;
    }
    const allowed = signature.split("|");
    let previous = [];
    try {
      previous = readRecentModules(localStorage, username, allowed);
    } catch {
      /* Private browsing can disable local storage. */
    }
    if (activeKey !== "home" && allowed.includes(activeKey)) {
      previous = [
        { key: activeKey, at: Date.now() },
        ...previous.filter((row) => row.key !== activeKey),
      ].slice(0, 5);
      try {
        localStorage.setItem(
          `cling:workspace:${username}:recent:v1`,
          JSON.stringify(previous),
        );
      } catch {
        /* Navigation stays available without storage. */
      }
    }
    setRecent(previous);
  }, [username, activeKey, signature]);
  return recent;
}

export function ModuleIntro({ item, section }) {
  const meta = SECTION_META[section?.key];
  return (
    <div
      className={`atelier-module-intro atelier-tone-${meta?.tone || "violet"}`}
    >
      <div>
        <div className="atelier-eyebrow">
          <span>
            {meta?.number || "00"} / {section?.label || "工作空间"}
          </span>
          <i />
          {meta?.english || "YOUR WORKSPACE"}
        </div>
        <h1>{item.label}</h1>
        <p>{MODULE_META[item.key]?.description}</p>
      </div>
      <span className="atelier-module-seal">
        <WorkspaceIcon name={item.key} size={28} />
      </span>
    </div>
  );
}

export function WorkspaceHome({
  user,
  sections,
  recent,
  onNavigate,
  onSearch,
}) {
  const [today, setToday] = useState(() => new Date());
  useEffect(() => {
    const timer = setInterval(() => setToday(new Date()), 60000);
    return () => clearInterval(timer);
  }, []);
  const items = sections
    .flatMap((section) => section.children)
    .filter((item) => item.key !== "home");
  const lookup = new Map(items.map((item) => [item.key, item]));
  const last = recent
    .map((row) => ({ ...row, item: lookup.get(row.key) }))
    .filter((row) => row.item);
  const primary =
    last[0]?.item ||
    ["work_journal", "emote_ui_automation", "learning", "data_generator"]
      .map((key) => lookup.get(key))
      .find(Boolean) ||
    items[0];
  const date = new Intl.DateTimeFormat("zh-CN", {
    timeZone: "Asia/Shanghai",
    month: "long",
    day: "numeric",
    weekday: "long",
  }).format(today);
  return (
    <div className="atelier-home">
      <section className="atelier-welcome" aria-labelledby="workspace-welcome">
        <div className="atelier-welcome-copy">
          <div className="atelier-eyebrow">
            <span>YOUR EVERYDAY SPACE</span>
            <i />
            CLING
          </div>
          <p className="atelier-greeting">
            欢迎回来，{user.display_name || user.username}
            <span>✳</span>
          </p>
          <h1 id="workspace-welcome">
            把专注，
            <br />
            留给<span>有意义的事。</span>
          </h1>
          <p className="atelier-welcome-note">
            测试的把握，成长的积累，日常的从容。
            <br />
            让好工具陪你，把每一天过得轻盈一点。
          </p>
          <div className="atelier-welcome-actions">
            {primary && (
              <button
                className="atelier-button atelier-button-primary"
                onClick={() => onNavigate(primary.key)}
              >
                {last.length ? `继续${primary.label}` : "开始我的工作"}
                <ArrowRight size={17} />
              </button>
            )}
            <button
              className="atelier-text-button"
              onClick={() => onSearch("")}
            >
              探索全部功能
              <ArrowUpRight size={16} />
            </button>
          </div>
        </div>
        <div className="atelier-welcome-art">
          <div className="atelier-date">
            <span>好好工作，也好好生活</span>
            <time dateTime={today.toISOString()}>{date}</time>
          </div>
          <OrbitArtwork />
          <span className="atelier-art-caption">
            <span>✦</span>一点秩序，一点灵感。
          </span>
        </div>
      </section>
      <div className="atelier-section-heading">
        <div>
          <span className="atelier-eyebrow">A PLACE FOR EVERYTHING</span>
          <h2>找到今天的工作节奏</h2>
        </div>
        <span className="atelier-count">
          {items.length} 个功能 · 按你的权限呈现
        </span>
      </div>
      {!items.length && (
        <div className="atelier-recent-empty">
          <WorkspaceIcon name="users" />
          <div>
            <strong>工作空间已准备好</strong>
            <p>当前账号尚未分配功能，请联系管理员配置访问权限。</p>
          </div>
        </div>
      )}
      <div className="atelier-spaces">
        {sections
          .filter((section) => SECTION_META[section.key])
          .map((section) => {
            const meta = SECTION_META[section.key];
            return (
              <section
                key={section.key}
                className={`atelier-space atelier-tone-${meta.tone}`}
              >
                <div className="atelier-space-top">
                  <span className="atelier-space-number">{meta.number}</span>
                  <span>{meta.english}</span>
                  <button
                    className="atelier-circle-button"
                    aria-label={`浏览${section.label}`}
                    onClick={() => onSearch(section.label)}
                  >
                    <ArrowUpRight size={19} />
                  </button>
                </div>
                <h3>{section.label}</h3>
                <p>{meta.title}</p>
                <div className="atelier-space-links">
                  {section.children.slice(0, 3).map((item) => (
                    <button key={item.key} onClick={() => onNavigate(item.key)}>
                      <WorkspaceIcon name={item.key} size={17} />
                      <span>{item.label}</span>
                      <ArrowRight size={15} />
                    </button>
                  ))}
                </div>
                <button
                  className="atelier-space-all"
                  onClick={() => onSearch(section.label)}
                >
                  查看全部 {section.children.length} 项
                  <ArrowUpRight size={14} />
                </button>
              </section>
            );
          })}
      </div>
      <section className="atelier-recent" aria-labelledby="workspace-recent">
        <div className="atelier-section-heading">
          <div>
            <span className="atelier-eyebrow">PICK UP WHERE YOU LEFT OFF</span>
            <h2 id="workspace-recent">最近访问</h2>
          </div>
          <Clock3 size={20} strokeWidth={1.5} />
        </div>
        {last.length ? (
          <div className="atelier-recent-grid">
            {last.slice(0, 3).map(({ item, at }) => (
              <button key={item.key} onClick={() => onNavigate(item.key)}>
                <span className="atelier-recent-icon">
                  <WorkspaceIcon name={item.key} />
                </span>
                <span>
                  <strong>{item.label}</strong>
                  <small>
                    {new Intl.DateTimeFormat("zh-CN", {
                      timeZone: "Asia/Shanghai",
                      month: "numeric",
                      day: "numeric",
                      hour: "2-digit",
                      minute: "2-digit",
                    }).format(at)}{" "}
                    访问
                  </small>
                </span>
                <ArrowUpRight size={16} />
              </button>
            ))}
          </div>
        ) : (
          <div className="atelier-recent-empty">
            <BrandMark />
            <div>
              <strong>你的工作轨迹，从这里开始。</strong>
              <p>
                打开一个功能，下次就能在这里继续。访问记录只保存在当前浏览器。
              </p>
            </div>
          </div>
        )}
      </section>
      <footer className="atelier-home-footer">
        <span>
          CLING <i>·</i> MAKE SPACE FOR GOOD WORK
        </span>
        <span>
          按 <kbd>Ctrl / ⌘ K</kbd>，快速找到需要的工具
        </span>
      </footer>
    </div>
  );
}

export function WorkspaceSearch({
  open,
  initialQuery,
  items,
  onClose,
  onNavigate,
}) {
  const [query, setQuery] = useState(""),
    [active, setActive] = useState(0);
  const input = useRef(null),
    list = useRef(null);
  useEffect(() => {
    if (open) {
      setQuery(initialQuery || "");
      setActive(0);
      const id = setTimeout(() => input.current?.focus(), 80);
      return () => clearTimeout(id);
    }
  }, [open, initialQuery]);
  const matches = searchModules(items, query);
  const choose = (item) => {
    if (item) {
      onClose();
      onNavigate(item.key);
    }
  };
  function move(index) {
    const next = Math.max(0, Math.min(matches.length - 1, index));
    setActive(next);
    const row = list.current?.children[next];
    if (row && list.current) {
      const y = row.offsetTop;
      if (y < list.current.scrollTop) list.current.scrollTop = y;
      else if (
        y + row.offsetHeight >
        list.current.scrollTop + list.current.clientHeight
      )
        list.current.scrollTop =
          y + row.offsetHeight - list.current.clientHeight;
    }
  }
  return (
    <Modal
      open={open}
      onCancel={onClose}
      title={<span className="atelier-sr-only">搜索平台功能</span>}
      footer={null}
      closable={false}
      width={620}
      className="atelier-command"
      destroyOnHidden
      afterOpenChange={(visible) => {
        if (visible) input.current?.focus();
      }}
      aria-label="搜索平台功能"
    >
      <div className="atelier-command-input">
        <Search size={22} strokeWidth={1.6} />
        <input
          ref={input}
          value={query}
          onChange={(event) => {
            setQuery(event.target.value);
            setActive(0);
          }}
          role="combobox"
          aria-autocomplete="list"
          aria-label="搜索功能"
          aria-expanded={open}
          aria-controls="atelier-command-results"
          aria-activedescendant={
            matches[active]
              ? `atelier-command-${matches[active].key}`
              : undefined
          }
          placeholder="搜索功能、工具或关键词…"
          autoComplete="off"
          onKeyDown={(event) => {
            if (event.key === "ArrowDown") {
              event.preventDefault();
              move(active + 1);
            }
            if (event.key === "ArrowUp") {
              event.preventDefault();
              move(active - 1);
            }
            if (event.key === "Enter") {
              event.preventDefault();
              choose(matches[active]);
            }
          }}
        />
        <button onClick={onClose} aria-label="关闭功能搜索">
          <kbd>Esc</kbd>
        </button>
      </div>
      <div className="atelier-command-label">
        <span>{query ? "搜索结果" : "前往功能"}</span>
        <span aria-live="polite">{matches.length} 个入口</span>
      </div>
      <div
        ref={list}
        className="atelier-command-results"
        id="atelier-command-results"
        role="listbox"
        aria-label="功能搜索结果"
      >
        {matches.map((item, index) => (
          <button
            role="option"
            aria-selected={active === index}
            id={`atelier-command-${item.key}`}
            key={item.key}
            onMouseMove={() => setActive(index)}
            onClick={() => choose(item)}
            tabIndex={-1}
          >
            <span className="atelier-command-icon">
              <WorkspaceIcon name={item.key} />
            </span>
            <span>
              <strong>{item.label}</strong>
              <small>{item.sectionLabel || "工作空间"}</small>
            </span>
            <CornerDownLeft size={16} />
          </button>
        ))}
      </div>
      {!matches.length && (
        <div className="atelier-command-empty">
          <Search size={28} />
          <strong>还没找到这个功能</strong>
          <p>试试“周报”“图片”或“API”，也可以清空关键词查看全部。</p>
          <button
            onClick={() => {
              setQuery("");
              setActive(0);
              input.current?.focus();
            }}
          >
            查看全部功能
          </button>
        </div>
      )}
      <div className="atelier-command-foot">
        <span>
          <MoveUp size={12} />
          <MoveDown size={12} /> 选择 <CornerDownLeft size={12} /> 打开
        </span>
        <span>
          <Command size={12} /> 你的工作，少走一步。
        </span>
      </div>
    </Modal>
  );
}
