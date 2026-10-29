import {TodayPanel} from "../modules/21-personal-space/TodayPanel.jsx";
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
  client,
}) {
  const [today, setToday] = useState(() => new Date());
  useEffect(() => {
    const timer = setInterval(() => setToday(new Date()), 60000);
    return () => clearInterval(timer);
  }, []);
  const items = sections.flatMap(section => section.children).filter(item => item.key !== 'home');
  const lookup = new Map(items.map(item => [item.key, item]));
  const last = recent.map(row => ({...row,item:lookup.get(row.key)})).filter(row=>row.item);
  const primary = last[0]?.item || ['work_journal','emote_ui_automation','data_generator'].map(key=>lookup.get(key)).find(Boolean) || items[0];
  const date = new Intl.DateTimeFormat('zh-CN',{timeZone:'Asia/Shanghai',month:'long',day:'numeric',weekday:'long'}).format(today);
  return (
    <div className="atelier-home">
      <section className="atelier-welcome atelier-welcome--compact" aria-labelledby="workspace-welcome">
        <div><h1 id="workspace-welcome">你好，{user.display_name || user.username}</h1><p>{date} · 继续今天的工作</p></div>
        <div className="atelier-welcome-actions">
          {primary && <button className="atelier-button atelier-button-primary" onClick={()=>onNavigate(primary.key)}>{last.length ? `继续${primary.label}` : '开始工作'}<ArrowRight size={17}/></button>}
          <button className="atelier-text-button" onClick={()=>onSearch('')}>查找功能<Search size={16}/></button>
        </div>
      </section>
      <TodayPanel client={client} onNavigate={onNavigate} practiceAllowed={items.some(item=>item.key==='practice_lab')} workJournalAllowed={items.some(item=>item.key==='work_journal')}/>
      {last.length>0&&<section className="atelier-recent" aria-labelledby="workspace-recent">
        <div className="atelier-section-heading"><h2 id="workspace-recent">最近使用</h2><Clock3 size={20}/></div>
        {last.length ? <div className="atelier-recent-grid">{last.slice(0,3).map(({item,at})=><button key={item.key} onClick={()=>onNavigate(item.key)}><span className="atelier-recent-icon"><WorkspaceIcon name={item.key}/></span><span><strong>{item.label}</strong><small>{new Intl.DateTimeFormat('zh-CN',{timeZone:'Asia/Shanghai',month:'numeric',day:'numeric',hour:'2-digit',minute:'2-digit'}).format(at)} 访问</small></span><ArrowUpRight size={16}/></button>)}</div> : <div className="atelier-recent-empty"><BrandMark/><div><strong>还没有访问记录</strong><p>打开下方功能，下次可在这里继续。</p></div></div>}
      </section>}
      <details className="atelier-feature-directory"><summary>浏览全部功能</summary><div className="atelier-section-heading"><h2>全部功能</h2><span className="atelier-count">{items.length} 个入口</span></div>
      {!items.length && <div className="atelier-recent-empty"><WorkspaceIcon name="users"/><p>当前账号尚未分配功能，请联系管理员配置访问权限。</p></div>}
      <div className="atelier-spaces">{sections.filter(section=>SECTION_META[section.key]).map(section=><section key={section.key} className={`atelier-space atelier-tone-${SECTION_META[section.key].tone}`}><h3>{section.label}</h3><div className="atelier-space-links">{section.children.slice(0,3).map(item=><button key={item.key} onClick={()=>onNavigate(item.key)}><WorkspaceIcon name={item.key} size={17}/><span>{item.label}</span><ArrowRight size={15}/></button>)}</div>{section.children.length>3 && <button className="atelier-space-all" onClick={()=>onSearch(section.label)}>查看全部 {section.children.length} 项<ArrowUpRight size={14}/></button>}</section>)}</div>
      </details>
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
