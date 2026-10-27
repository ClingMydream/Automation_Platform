// File purpose: Login page. Collect credentials, request a token, and notify the app after login.
// How to change: edit UI text/layout in this file; move reusable logic into shared helpers or the module feature file.

import React, { useRef, useState } from 'react';
import { apiClient } from '../../shared/apiClient';
import { BrandMark, OrbitArtwork } from '../../shared/WorkspaceIdentity.jsx';
import { ArrowRight, Eye, EyeOff } from 'lucide-react';


// Login page: submits credentials and stores the returned token.
export function Login({ onLogin, notice }) {
  // State block: values here control loading, selection, form state, and visible page data.
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [visible, setVisible] = useState(false);
  const submitting = useRef(false);

  // Submit the current form and refresh the list after saving.
  async function submit(event) {
    event.preventDefault();
    if (submitting.current) return;
    const fields = new FormData(event.currentTarget);
    const values = { username: String(fields.get('username') || '').trim(), password: String(fields.get('password') || ''), remember_me: fields.get('remember_me') === 'on' };
    if (!values.username || !values.password) { setError('请输入账号和密码'); return; }
    submitting.current = true; setError(''); setLoading(true);
    try {
      const data = await apiClient().post('/auth/login', values);
      if (values.remember_me) { localStorage.setItem('token', data.access_token); sessionStorage.removeItem('token'); }
      else { sessionStorage.setItem('token', data.access_token); localStorage.removeItem('token'); }
      onLogin(data.access_token);

    } catch (err) {
      setError(err.message || '登录失败，请重试');
    } finally {
      submitting.current = false; setLoading(false);
    }
  }

  // Render block: JSX below describes what the user sees on this page.
  return (
    <main className="login-screen atelier-login">
      <section className="atelier-login-story" aria-labelledby="login-story-title">
        <div className="atelier-login-wordmark"><BrandMark/><strong>cling<span>✦</span></strong></div>
        <div className="atelier-login-narrative"><span className="atelier-eyebrow">A LITTLE ORDER. A LITTLE WONDER.</span><h1 id="login-story-title">做好工作，<br/>也留一点空间<br/>给<span>自己。</span></h1><p>让测试更有把握，让成长慢慢发生。<br/>你的日常工作，可以轻盈一点。</p></div>
        <OrbitArtwork/>
        <div className="atelier-login-story-foot"><span>测试 · 成长 · 效率</span><span>YOUR EVERYDAY WORKSPACE</span></div>
      </section>
      <section className="atelier-login-entry" aria-labelledby="login-form-title">
      <div className="atelier-login-entry-label">CLING / PERSONAL WORKSPACE</div>
      <div className="login-card atelier-native-login">
        <div className="atelier-native-stack">
          <div className="login-brand">
            <div>
              <span className="atelier-eyebrow">WELCOME BACK</span>
              <h2 id="login-form-title">欢迎回到你的工作空间</h2>
              <p className="atelier-login-description">使用平台账号登录，继续今天的好工作。</p>
            </div>
          </div>
          {notice && <p className="atelier-login-notice" role="status">{notice}</p>}
          {error && <p className="atelier-login-error" role="alert">{error}</p>}
          <form onSubmit={submit} aria-busy={loading}>
            <label className="atelier-field" htmlFor="login-username">登录账号
              <input id="login-username" name="username" defaultValue="admin" required autoComplete="username" />
            </label>
            <label className="atelier-field" htmlFor="login-password">登录密码</label>
            <div className="atelier-password-field">
              <input id="login-password" name="password" type={visible ? 'text' : 'password'} required autoFocus autoComplete="current-password" />
              <button type="button" className="atelier-password-toggle" aria-label={visible ? '隐藏' : '显示'} aria-pressed={visible} onClick={()=>setVisible(value=>!value)}>{visible ? <EyeOff size={18}/> : <Eye size={18}/>}</button>
            </div>
            <label className="atelier-remember"><input type="checkbox" name="remember_me"/>7 天内记住我，下次打开自动登录</label>
            <button className="atelier-login-submit" type="submit" disabled={loading}><span>{loading ? '正在登录…' : '进入自动化平台'}</span><ArrowRight size={17}/></button>
          </form>
        </div>
      </div>
      <p className="atelier-login-entry-foot">一点秩序，一点灵感。<span>让每一次打开，都离目标更近一点。</span></p>
      </section>
    </main>
  );
}

// Auth module: owns the login screen and token handoff after successful login.
