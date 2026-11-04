"""Emote page objects for UI-only scenarios; business writes go through the UI."""
import random
import re
import uuid
import hashlib
import time
import os
import httpx
from urllib.parse import urlencode, parse_qs, urlsplit
from pathlib import Path
from contextlib import contextmanager
from datetime import datetime
from zoneinfo import ZoneInfo
from playwright.sync_api import expect, TimeoutError as PlaywrightTimeout


def watering_outcome(body, http_ok=True):
    assert http_ok and isinstance(body, dict), '浇水接口请求失败，请查看失败请求日志'
    data = body.get('data')
    result = data if isinstance(data, dict) else body
    message = str(result.get('error') or result.get('message') or body.get('message') or '')
    cooldown = re.search(r'24\s*小时内.*(?:已经|已).*浇', message)
    if cooldown and result.get('success') is False and body.get('code') not in (401, 403, 500):
        return 'cooldown', message
    assert body.get('success') is True and isinstance(data, dict) and data.get('success') is True, '浇水未成功，且不是24小时内已浇水分支'
    return 'watered', message


class TestDataRequired(Exception):
    """A real UI scenario cannot run without its explicitly prepared test data."""


class EmotePages:
    def __init__(self, page, base_url, credentials):
        self.page, self.base, self.credentials = page, base_url.rstrip('/'), credentials
        self.post_text = None
        self.post_id = None
        self.post_public = False
        self.stamp = datetime.now(ZoneInfo('Asia/Shanghai')).strftime('%Y-%m-%d %H:%M:%S')
        self.run_key = uuid.uuid4().hex[:6]
        self.checks = []
        self.extra_images = []
        self.network = None
        self.auth_dir = None

    def perform(self, step):
        action = step['action']
        if action in {'click','fill','press','assert_visible','assert_text'}:
            kind, value = step.get('locator_type','role'), step.get('locator','')
            assert value, '请配置步骤目标元素'
            if kind=='role':
                target=self.page.get_by_role(step.get('role','button'),name=value,exact=True)
            elif kind=='testid':
                target=self.page.get_by_test_id(value)
            elif kind=='placeholder':
                target=self.page.get_by_placeholder(value,exact=True)
            elif kind=='text':
                target=self.page.get_by_text(value,exact=True)
            elif kind=='css':
                target=self.page.locator(value)
            else:
                raise AssertionError('不支持的元素定位方式')
            content=str(step.get('value','')).replace('${timestamp}',self.stamp)
            if action=='click':target.click()
            elif action=='fill':target.fill(content)
            elif action=='press':target.press(content)
            elif action=='assert_visible':expect(target).to_be_visible()
            elif action=='assert_text':expect(target).to_have_text(content)
        elif action=='open':
            route=step.get('value','home')
            assert re.fullmatch(r'[a-z_]+',route), '仅允许应用内页面名称'
            self.go(route)
        else:
            assert action in {'login','home','create_post','verify_post','own_post','like','comment','favorite','delete_post','friend','delete_friend','chat','daily_task','profile','dual_post','kindness_home','kindness_task','watering','avatar','cross_comment','mutual_like','mutual_comment','mutual_favorite','peer_chat'}, '不支持的步骤'
            getattr(self,action)()

    def go(self, route):
        if route=='weekly_tasks':
            self.go('profile')
            self.page.locator('button[data-feature-guide="daily-tasks"]:visible').click()
            self.page.wait_for_url(re.compile(r'#/weekly_tasks(?:\?|$)'),wait_until='commit')
            return
        selector={'chat':'button:has(.lucide-message-square):visible','profile':'button[data-feature-guide="profile-entry"]:visible'}.get(route)
        current=self.page.url.split('#/')[-1].split('?')[0]
        if route=='profile' and current=='weekly_tasks':
            self.page.locator('button[aria-label="back"]').click()
            self.page.wait_for_url(re.compile(r'#/profile(?:\?|$)'),wait_until='commit')
            return
        if selector and current in {'home','community','chat','profile'} and self.page.locator(selector).count():
            self.page.locator(selector).first.click()
            self.page.wait_for_url(re.compile(r'#/'+re.escape(route)+r'(?:\?|$)'),wait_until='commit')
            return
        self.page.goto(self.base + '/?cling_studio=' + uuid.uuid4().hex + '#/' + route, wait_until='domcontentloaded')

    def button(self, text):
        return self.page.get_by_role('button', name=text, exact=True)

    def dismiss_guides(self):
        try:
            self.button('同意并继续').wait_for(state='visible',timeout=1500)
            self.button('同意并继续').click()
        except Exception:
            pass
        for _ in range(5):
            advanced=False
            for text in ['继续','开启旅程']:
                target=self.button(text)
                if target.count()==1 and target.is_visible():
                    target.click();advanced=True;break
            if not advanced:break
        progress=self.page.evaluate("() => {try{return JSON.parse(localStorage.getItem('emote_feature_guide_install')||'{}').status||''}catch{return ''}}")
        if progress not in ('completed','skipped'):
            self.button('跳过引导').wait_for(state='visible',timeout=15000)
            self.button('跳过引导').click()
            self.button('开始体验').wait_for(state='visible',timeout=10000)
            self.button('开始体验').click()
        elif self.button('开始体验').count() and self.button('开始体验').is_visible():
            self.button('开始体验').click()
        expect(self.page.locator('[role=dialog][aria-label="发布动态"].pointer-events-auto')).to_be_hidden(timeout=10000)

    def home(self):
        self.go('home')
        expect(self.page.locator('button[data-feature-guide="create-post"]:visible')).to_be_visible(timeout=15000)
        self.dismiss_guides()
        expect(self.page.locator('button[data-feature-guide="create-post"]:visible')).to_be_visible()

    def login(self):
        self.go('login')
        consent = self.button('同意并继续')
        try:
            consent.wait_for(state='visible', timeout=3000)
        except PlaywrightTimeout:
            pass
        else:
            consent.click()
            expect(consent).to_be_hidden()
        account = self.credentials.get('account_a', {})
        assert account.get('username') and account.get('password'), '测试数据集缺少账号 A'
        self.page.get_by_placeholder('手机号', exact=True).fill(str(account['username']))
        self.page.get_by_placeholder('请输入密码', exact=True).fill(str(account['password']))
        # Agreement control is the button directly preceding the agreement paragraph.
        toggle = self.page.get_by_text('已阅读并同意', exact=False).locator('xpath=preceding-sibling::button')
        if toggle.count() and 'bg-emerald-500' not in (toggle.get_attribute('class') or ''):
            toggle.click()
        self.submit(self.button('进入心灵花园'), '/login')
        self.page.wait_for_url(re.compile(r'#/home(?:\?|$)'), timeout=30000,wait_until='domcontentloaded')
        self.dismiss_guides()
        expect(self.page.locator('button[data-feature-guide="create-post"]:visible')).to_be_visible()

    def submit(self, target, endpoint, method=None):
        with self.page.expect_response(lambda r: endpoint in r.url and (not method or r.request.method == method), timeout=30000) as result:
            target.click()
        response = result.value
        body = response.json()
        assert response.ok and body.get('success') is True, f'{endpoint} 返回失败（HTTP {response.status}），请查看本步骤请求证据'
        return body.get('data')

    def card(self):
        assert self.post_text, '本次测试帖子尚未创建'
        scope = self.detail_root() if '#/post_detail?' in self.page.url else self.page
        text = scope.locator('p:visible').filter(has_text=re.compile('^'+re.escape(self.post_text)+'$')).first
        expect(text).to_be_visible()
        return text.locator("xpath=ancestor::div[contains(@class,'rounded-[28px]') and contains(@class,'group')][1]")

    def detail_root(self):
        heading = self.page.get_by_role('heading', name=re.compile(r'^(详情|Detail|Details)$'))
        expect(heading).to_be_visible(timeout=15000)
        return heading.locator('xpath=ancestor::div[contains(@class,"min-h-screen")][1]')

    def create_post(self, content=None, public=False):
        content = content or self.stamp + ' UI测试 ' + self.run_key + '-' + uuid.uuid4().hex[:4]
        self.page.locator('button[data-feature-guide="create-post"]:visible').click()
        moods = self.page.locator('div.grid.grid-cols-3 > button:visible')
        expect(moods.first).to_be_visible()
        mood=moods.nth(random.randrange(moods.count()))
        mood_text=mood.inner_text().strip()
        mood.click()
        field = self.page.get_by_placeholder('开始书写...', exact=True)
        field.fill(content)
        tags = field.locator("xpath=following::div[contains(@class,'flex-wrap')][1]/button")
        expect(tags.first).to_be_visible()
        tag=tags.nth(random.randrange(tags.count()))
        tag_text=tag.inner_text().strip()
        tag.click()
        toggle = self.button('私密' if public else '公开')
        if toggle.count() and toggle.is_visible():
            toggle.click()
        expect(self.button('公开' if public else '私密')).to_be_visible()
        self.publish_post(self.button('释放心语'), content, public)
        self.verify_post()
        self.checks.append(f'已随机选择心情「{mood_text}」与标签「{tag_text}」，发布本人' + ('公开' if public else '私密') + '动态；操作时间：' + self.stamp)

    def publish_post(self, button, content, public):
        with self.page.expect_response(lambda r: r.request.method == 'POST' and r.url.split('?')[0].endswith('/posts')) as result:
            button.click()
        response = result.value
        assert response.ok and response.json().get('success') is True, '发帖接口失败，请查看失败请求日志'
        sent = response.request.post_data_json
        assert isinstance(sent, dict) and sent.get('isPublic') is public, '实际发帖可见性与所选用例不符'
        self.post_text, self.post_public = content, public
        self.post_id = self.resolve_persisted_post_id(content, public)

    def resolve_persisted_post_id(self, content, public):
        # Creation can replace the client UUID with a server-generated numeric ID.
        with self.page.expect_response(lambda r: r.request.method == 'POST' and '/posts-extra/published' in r.url) as result:
            self.page.goto(self.base + '/?cling_studio=' + uuid.uuid4().hex + '#/home', wait_until='domcontentloaded')
        response = result.value
        body = response.json()
        assert response.ok and body.get('success') is True, '读取本人已发布帖子失败'
        data = body.get('data')
        items = data.get('items', []) if isinstance(data, dict) else data
        own_id = str(self.page.evaluate("localStorage.getItem('emote_current_session')") or '')
        matches = [row for row in (items or []) if str(row.get('userId')) == own_id
            and row.get('content') == content and row.get('isPublic') is public]
        assert len(matches) == 1 and matches[0].get('id'), '未能从本人发布列表唯一确认帖子实际 ID，停止跨账号操作'
        return str(matches[0]['id'])

    def verify_post(self):
        card = self.card()
        if not self.post_public:
            expect(card.get_by_text('私密', exact=True)).to_be_visible()

    def own_post(self):
        # Reuse the post within a chain; standalone scenarios create their own fixture via UI.
        if not self.post_text:
            self.create_post()
        else:
            self.home()
            self.verify_post()

    def like(self):
        card = self.card()
        heart = card.locator('button:has(.lucide-heart)').first
        if not heart.locator('.fill-pink-500').count():
            self.submit(heart, '/reactions', 'POST')
        expect(heart.locator('.fill-pink-500')).to_be_visible()

    def comment(self):
        card = self.card()
        card.locator('button:has(.lucide-message-circle)').click()
        field = card.get_by_placeholder('添加评论...')
        text = '自动化评论 ' + self.stamp + ' ' + self.run_key
        field.fill(text)
        with self.page.expect_response(lambda r: '/comment' in r.url and r.request.method == 'POST') as response:
            field.press('Enter')
        assert response.value.ok and response.value.json().get('success') is True, '评论接口失败，请查看请求证据'
        expect(card.get_by_text(text, exact=True)).to_be_visible()

    def favorite(self):
        button = self.card().locator('button:has(.lucide-bookmark)')
        if not button.locator('.fill-amber-400').count():
            self.submit(button, '/favorite/', 'POST')
        expect(button.locator('.fill-amber-400')).to_be_visible()

    def delete_post(self):
        post_id = self.post_id
        self.open_test_post(post_id, self.post_text)
        card = self.card()
        card.locator('button:has(.lucide-ellipsis-vertical), button:has(.lucide-more-vertical)').click()
        card.get_by_role('button', name='删除动态', exact=True).click()
        self.submit(self.button('确认'), '/posts/', 'DELETE')
        with self.page.expect_response(lambda r: r.request.method == 'POST' and '/posts-extra/published' in r.url) as result:
            self.home()
        body = result.value.json()
        assert result.value.ok and body.get('success') is True, '删除后重新读取本人帖子失败'
        data = body.get('data')
        items = data.get('items', []) if isinstance(data, dict) else data
        assert all(str(row.get('id')) != post_id for row in (items or [])), '删除后帖子仍在本人发布列表中'
        expect(self.page.get_by_text(self.post_text, exact=True)).to_have_count(0)
        self.post_text = None
        self.post_id, self.post_public = None, False

    def chat(self):
        self.go('chat')
        search=self.page.get_by_placeholder('寻找灵魂...',exact=True)
        expect(search).to_be_visible()
        if search.input_value():
            with self.page.expect_response(lambda r:'/friend-recommend' in r.url and 'exactMatch' not in (r.request.post_data or '')):
                search.fill('')
            expect(self.page.get_by_text('同步原野中...',exact=True)).to_be_hidden(timeout=15000)
        name = self.page.locator('h3:visible,h4:visible').filter(has_text='霖感小秘书').first
        expect(name).to_be_visible()
        card = name.locator("xpath=ancestor::div[contains(@class,'justify-between') and contains(@class,'rounded-3xl')][1]")
        card.locator('button:has(.lucide-message-circle)').click()
        expect(self.page.get_by_role('heading', name='霖感小秘书', exact=True)).to_be_visible()
        field = self.page.get_by_placeholder('Message...', exact=True)
        text = '聊天测试' + self.stamp + ' ' + self.run_key
        field.fill(text)
        with self.page.expect_response(lambda r: r.request.method == 'POST' and '/message' in r.url) as response:
            field.press('Enter')
        assert response.value.ok and response.value.json().get('success') is True, '聊天发送失败，请查看请求证据'
        expect(self.page.get_by_text(text, exact=True)).to_be_visible()

    @contextmanager
    def test_peer(self):
        account_a = self.credentials.get('account_a', {})
        account_b = self.credentials.get('account_b', {})
        assert account_b.get('username') and account_b.get('password'), '好友增删需要数据集中的专用账号 B 和密码'
        assert str(account_b['username']) != str(account_a.get('username')), '好友测试账号 A、B 必须不同'
        self.go('profile')
        own_id = self.page.evaluate("localStorage.getItem('emote_current_session')")
        own_name = self.page.locator('h3.profile-card__title:visible').inner_text().strip()
        assert own_id and own_name, '账号 A 身份未确认，未执行好友操作'
        options = {'viewport': {'width':390,'height':844}}
        state = None
        if getattr(self, 'auth_dir', None):
            identity = self.base + '/|' + str(account_b['username'])
            state = Path(self.auth_dir) / (hashlib.sha256(identity.encode()).hexdigest() + '.json')
            if state.exists() and time.time()-state.stat().st_mtime < 86400:
                options['storage_state'] = str(state)
        context = self.page.context.browser.new_context(**options)
        other = None
        try:
            other = EmotePages(context.new_page(), self.base, {'account_a': account_b})
            other.network = getattr(self, 'network', None)
            if other.network:
                other.network.bind(other.page)
            fresh = 'storage_state' not in options
            if not fresh:
                try:
                    other.home()
                except Exception:
                    fresh = True
            if fresh:
                other.login()
                if state:
                    context.storage_state(path=str(state));state.chmod(0o600)
            other.go('profile')
            peer_id = other.page.evaluate("localStorage.getItem('emote_current_session')")
            peer_name = other.page.locator('h3.profile-card__title:visible').inner_text().strip()
            assert peer_id and peer_name and peer_id != own_id, '账号 B 身份未确认或与 A 相同，未执行好友操作'
            yield other, peer_id, peer_name, own_id, own_name
        except Exception:
            if other:
                try:
                    self.extra_images.append(('account-b-failure', other.page.screenshot(full_page=False)))
                except Exception:
                    pass
            raise
        finally:
            context.close()

    def dual_post(self):
        with self.test_peer() as (other, _, __, ___, ____):
            self.home()
            self.create_post()
            other.home()
            other.create_post()
            self.extra_images.append(('account-b-post', other.page.screenshot(full_page=False)))
            self.checks.append('账号 A 私密帖：' + self.post_text)
            self.checks.append('账号 B 私密帖：' + other.post_text + '；两条帖子均保留，未执行跨账号互评')

    def find_test_peer(self, peer_id, peer_name):
        seen_ids = set()
        def observe(response):
            if '/friend' not in response.url:
                return
            try:
                body = response.json()
                if body.get('success') is not True:
                    return
                def collect(value):
                    if isinstance(value, dict):
                        for key in ['id', 'userId']:
                            if value.get(key) is not None:seen_ids.add(str(value[key]))
                        for child in value.values():collect(child)
                    elif isinstance(value, list):
                        for child in value:collect(child)
                collect(body.get('data'))
            except Exception:
                pass
        self.page.on('response', observe)
        try:
            self.home();self.go('chat')
            search = self.page.get_by_placeholder('寻找灵魂...', exact=True)
            search.fill(str(peer_id))
            deadline = time.monotonic() + 20
            while str(peer_id) not in seen_ids and time.monotonic() < deadline:
                self.page.wait_for_timeout(100)
            assert str(peer_id) in seen_ids, '未从好友查询响应确认专用账号 ID，未操作任何用户'
            expect(self.page.get_by_text('同步原野中...',exact=True)).to_be_hidden(timeout=15000)
            heading = self.page.locator('h3:visible,h4:visible').filter(has_text=re.compile('^'+re.escape(peer_name)+'$'))
            expect(heading).to_have_count(1)
            card = heading.locator("xpath=ancestor::div[contains(@class,'justify-between') and contains(@class,'rounded-3xl')][1]")
            expect(card).to_have_count(1)
            return card
        finally:
            self.page.remove_listener('response', observe)

    def peer_is_friend(self, card):
        return card.locator('button:has(.lucide-message-circle):visible').count() == 1

    def remove_test_peer(self, card, peer_id, peer_name):
        chat = card.locator('button:has(.lucide-message-circle):visible')
        expect(chat).to_have_count(1)
        chat.click()
        self.page.wait_for_url(lambda url: parse_qs(urlsplit(url).fragment.partition('?')[2]).get('friendId') == [str(peer_id)])
        self.page.locator('button:has(.lucide-ellipsis-vertical):visible,button:has(.lucide-more-vertical):visible').click()
        self.button('删除好友').click()
        self.submit(self.button('删除'), '/friends', 'DELETE')
        expect(self.page.get_by_text('删除好友成功', exact=True)).to_be_visible()
        card = self.find_test_peer(peer_id, peer_name)
        expect(card.locator('button:has(.lucide-message-circle):visible')).to_have_count(0)
        self.checks.append('已通过 UI 删除经身份核对的专用账号 B，并重新搜索确认好友关系移除；双方聊天记录按应用规则清除')
        return card

    def request_test_peer(self, card):
        pending = card.get_by_text('已发送', exact=True)
        if pending.count() and pending.is_visible():
            self.checks.append('已确认发给专用账号 B 的申请处于已发送状态，本轮未重复发送')
            return
        add = card.locator('button:has(.lucide-user-plus):visible')
        expect(add).to_have_count(1)
        with self.page.expect_response(lambda r: '/friends/request' in r.url and r.request.method == 'POST') as result:
            add.click()
        response = result.value;body = response.json()
        if response.ok and body.get('success') is False and body.get('i18nKey') == 'error.friend.add_limit_daily':
            raise TestDataRequired(str(body.get('message') or '今日好友申请额度已用完') + '；本轮未发送新的好友申请')
        assert response.ok and body.get('success') is True, '好友申请接口失败，请查看请求证据'
        expect(card.get_by_text('已发送', exact=True)).to_be_visible()
        self.checks.append('已通过 UI 向身份核对后的专用账号 B 发送好友申请')

    def friend(self):
        with self.test_peer() as (_, peer_id, peer_name, _, __):
            card = self.find_test_peer(peer_id, peer_name)
            if self.peer_is_friend(card):
                card = self.remove_test_peer(card, peer_id, peer_name)
            self.request_test_peer(card)

    def ensure_test_friendship(self, other, peer_id, peer_name, own_id, own_name):
        card = self.find_test_peer(peer_id, peer_name)
        if self.peer_is_friend(card):
            return card
        accept = card.locator('button:has(.lucide-check):visible')
        if accept.count() == 1:
            self.submit(accept, '/friends/accept', 'POST')
        else:
            other_card = other.find_test_peer(own_id, own_name)
            other_accept = other_card.locator('button:has(.lucide-check):visible')
            if other_accept.count() == 1:
                other.submit(other_accept, '/friends/accept', 'POST')
            else:
                # Fixture preparation uses B's own valid application quota.
                other.request_test_peer(other_card)
                card = self.find_test_peer(peer_id, peer_name)
                accept = card.locator('button:has(.lucide-check):visible')
                expect(accept).to_have_count(1)
                self.submit(accept, '/friends/accept', 'POST')
        card = self.find_test_peer(peer_id, peer_name)
        assert self.peer_is_friend(card), '未建立专用 A/B 好友关系，后续聊天前置条件未满足'
        self.checks.append('已通过专用账号双方页面确认好友关系')
        return card

    def delete_friend(self):
        with self.test_peer() as (other, peer_id, peer_name, own_id, own_name):
            card = self.find_test_peer(peer_id, peer_name)
            if not self.peer_is_friend(card):
                card = self.ensure_test_friendship(other, peer_id, peer_name, own_id, own_name)
                self.checks.append('前置准备：已建立专用 A/B 好友关系')
            self.remove_test_peer(card, peer_id, peer_name)

    def read_daily_task(self):
        button = self.kindness_task_button()
        text = button.locator('xpath=..').inner_text()
        related = self.page.get_by_role('heading', name=re.compile('评论|回响|互动'))
        for index in range(related.count()):
            heading = related.nth(index)
            if heading.is_visible():
                card = heading.locator('xpath=ancestor::div[./button][1]')
                if card.count() == 1:
                    text += '\n' + card.inner_text()
        self.home()
        section = self.page.locator('section:visible').filter(has=self.page.get_by_text('日行一善', exact=True)).last
        expect(section).to_be_visible()
        return (text + '\n' + section.inner_text())[:2000]

    def open_test_post(self, post_id, text):
        current_id = self.page.evaluate("localStorage.getItem('emote_current_session')")
        query = urlencode({'postId': post_id, 'currentUserId': current_id, 'actionType': 'view_post'})
        self.page.goto(self.base + '/?cling_studio=' + uuid.uuid4().hex + '#/post_detail?' + query, wait_until='domcontentloaded')
        self.post_text, self.post_public = text, True
        expect(self.card()).to_be_visible()

    def comment_on_test_post(self, post_id, post_text, comment):
        self.open_test_post(post_id, post_text)
        field = self.card().get_by_placeholder('添加评论...', exact=True)
        expect(field).to_be_visible()
        field.fill(comment)
        with self.page.expect_response(lambda r: '/comment' in r.url and r.request.method == 'POST') as result:
            field.press('Enter')
        assert result.value.ok and result.value.json().get('success') is True, '跨账号评论接口失败，请查看请求日志'
        self.assert_saved_comment(comment)

    def assert_saved_comment(self, comment):
        # Detail comments are rendered beside the visual post-card wrapper.
        assert '#/post_detail?' in self.page.url, '评论核验必须位于已确认的帖子详情页'
        target = self.detail_root().locator('[id^="comment-"]:visible p').filter(has_text=re.compile('^'+re.escape(comment)+'$')).first
        expect(target).to_be_visible(timeout=20000)

    def publish_task_post(self, content):
        action = self.kindness_task_button()
        expect(action).to_contain_text(re.compile('去完成|已完成'))
        if '已完成' in action.inner_text():
            self.home()
            self.create_post(content, public=True)
            self.checks.append('日行一善已完成，本轮按任务主题发布公开互评测试帖，不重复领取任务奖励')
            return
        expect(action).to_be_enabled(timeout=15000)
        action.click()
        field = self.page.get_by_placeholder('开始书写...', exact=True)
        expect(field).to_be_visible();field.fill(content)
        private = self.button('私密')
        if private.count() and private.is_visible():
            private.click()
        expect(self.button('公开')).to_be_visible()
        self.publish_post(self.button('完成并绽放'), content, True)
        self.home();self.verify_post()
        expect(self.kindness_task_button()).to_contain_text('已完成', timeout=15000)
        self.home()

    def generate_daily_content(self, tasks):
        try:
            response = httpx.post('http://backend:8000/api/v1/ui-automation/internal/task-content',
                headers={'X-Runner-Token': os.environ.get('UI_RUNNER_TOKEN', '')}, json=tasks, timeout=75)
            if response.status_code == 503:
                raise TestDataRequired('AI 尚未配置，未生成或发布任务互评帖子')
            response.raise_for_status()
            generated = response.json()
        except httpx.HTTPError:
            raise TestDataRequired('AI 每日任务内容生成不可用，未发布任务互评帖子') from None
        return generated

    def social_pair(self, other):
        fixture = getattr(self, 'social_fixture', None)
        if fixture:
            return fixture
        tasks = {'task_a': self.read_daily_task(), 'task_b': other.read_daily_task()}
        generated = self.generate_daily_content(tasks)
        post_a, post_b = generated['post_a'], generated['post_b']
        self.publish_task_post(post_a);post_a_id = self.post_id
        other.publish_task_post(post_b);post_b_id = other.post_id
        fixture = {'post_a': post_a, 'post_b': post_b, 'id_a': post_a_id, 'id_b': post_b_id,
            'comment_a': re.sub(r'\s+', ' ', generated['comment_a_to_b']).strip(),
            'comment_b': re.sub(r'\s+', ' ', generated['comment_b_to_a']).strip(), 'completed': []}
        self.social_fixture = fixture
        return fixture

    def mutual_like(self):
        self.mutual_interaction('like')

    def mutual_comment(self):
        self.mutual_interaction('comment')

    def mutual_favorite(self):
        self.mutual_interaction('favorite')

    def cross_comment(self):
        self.mutual_interaction('comment')

    def mutual_interaction(self, kind):
        previous_post = (self.post_text, self.post_id, self.post_public)
        with self.test_peer() as (other, _, __, ___, ____):
            fixture = self.social_pair(other)
            if kind == 'comment':
                if kind not in fixture['completed']:
                    self.comment_on_test_post(fixture['id_b'], fixture['post_b'], fixture['comment_a'])
                    other.comment_on_test_post(fixture['id_a'], fixture['post_a'], fixture['comment_b'])
                else:
                    self.checks.append('本用例复核本轮已完成的双向评论，未重复发送')
                self.open_test_post(fixture['id_a'], fixture['post_a'])
                self.assert_saved_comment(fixture['comment_b'])
                other.open_test_post(fixture['id_b'], fixture['post_b'])
                other.assert_saved_comment(fixture['comment_a'])
            else:
                for actor, pid, text in [(self, fixture['id_b'], fixture['post_b']), (other, fixture['id_a'], fixture['post_a'])]:
                    actor.open_test_post(pid, text)
                    getattr(actor, kind)()
                    actor.open_test_post(pid, text)
                    icon = '.fill-pink-500' if kind == 'like' else '.fill-amber-400'
                    expect(actor.card().locator(icon)).to_be_visible()
            fixture['completed'].append(kind)
            self.extra_images.append(('account-b-mutual-' + kind, other.page.screenshot(full_page=False)))
            self.checks.extend(['双方互相' + {'like':'点赞','comment':'评论','favorite':'收藏'}[kind] + '并重新读取确认持久化',
                'A帖子实际ID：' + fixture['id_a'] + '；B帖子实际ID：' + fixture['id_b'],
                '操作时间：' + datetime.now(ZoneInfo('Asia/Shanghai')).isoformat(), '帖子及互动记录全部保留'])
        self.post_text, self.post_id, self.post_public = previous_post

    def peer_chat(self):
        with self.test_peer() as (other, peer_id, peer_name, own_id, own_name):
            self.ensure_test_friendship(other, peer_id, peer_name, own_id, own_name)
            message_a = '聊天测试 ' + self.stamp + ' A→B ' + self.run_key
            message_b = '聊天测试 ' + self.stamp + ' B→A ' + self.run_key
            for actor, uid, name, text in [(self, peer_id, peer_name, message_a), (other, own_id, own_name, message_b)]:
                card = actor.find_test_peer(uid, name)
                card.locator('button:has(.lucide-message-circle):visible').click()
                field = actor.page.get_by_placeholder('Message...', exact=True)
                field.fill(text)
                with actor.page.expect_response(lambda r: '/message' in r.url and r.request.method == 'POST') as result:
                    field.press('Enter')
                assert result.value.ok and result.value.json().get('success') is True, '双账号消息发送失败'
                expect(actor.page.get_by_text(text, exact=True)).to_be_visible()
            self.find_test_peer(peer_id, peer_name).locator('button:has(.lucide-message-circle):visible').click()
            expect(self.page.get_by_text(message_b, exact=True)).to_be_visible(timeout=15000)
            self.extra_images.append(('account-b-chat', other.page.screenshot(full_page=False)))
            self.checks.append('A→B、B→A 消息已发送并验证接收，聊天记录保留')

    def daily_task(self):
        self.go('weekly_tasks')
        expect(self.page.locator('[data-section="checkin-week"]')).to_be_visible()
        title = self.page.get_by_role('heading',name=re.compile('签到')).first
        expect(title).to_be_visible()
        card = title.locator('xpath=ancestor::div[./button][1]')
        check = card.locator(':scope > button').last
        if check.is_enabled():
            self.submit(check, '/check', 'POST')
            expect(check).to_be_disabled(timeout=15000)
        else:
            expect(check).to_contain_text(re.compile('完成|已签'))
        water_title=self.page.get_by_role('heading',name=re.compile('浇水')).first
        expect(water_title).to_be_visible()
        water_task=water_title.locator('xpath=ancestor::div[./button][1]').locator(':scope > button').last
        expect(water_task).to_contain_text(re.compile('已完成|去完成'))
        if '已完成' in water_task.inner_text():
            self.checks.append('浇水任务已完成，本轮无需重复浇水')
            return
        self.watering()

    def water_button(self, water, label):
        expect(water).to_be_visible(timeout=15000)
        if water.is_disabled() and re.search(r'已浇水|Watered', water.inner_text()):
            self.checks.append('通过：' + label + '页面已显示已浇水，未重复发送请求')
            return 'cooldown'
        expect(water).to_be_enabled(timeout=15000)
        with self.page.expect_response(lambda r: '/user-watering/water' in r.url and r.request.method == 'POST') as result:
            water.click()
        response = result.value
        outcome, message = watering_outcome(response.json(), response.ok)
        if outcome == 'cooldown':
            expect(self.page.get_by_text(message,exact=True).last).to_be_visible()
            self.checks.append('通过：' + label + '24小时内已浇水，冷却保护符合预期')
        else:
            expect(self.page.get_by_text('浇水成功！', exact=True).last).to_be_visible()
            self.checks.append('通过：本轮给' + label + '浇水成功')
        return outcome

    def watering(self):
        self.go('profile')
        outcome = self.water_button(self.page.locator('.garden-plot button.bottom-4.right-4:visible').first, '自己')
        if outcome == 'watered':
            return
        if self.water_secretary() == 'cooldown':
            self.home()
            self.water_peer()

    def water_secretary(self):
        # Use the explicitly requested official account, avoiding arbitrary users.
        self.home()
        self.go('chat')
        search = self.page.get_by_placeholder('寻找灵魂...', exact=True)
        if search.input_value():
            with self.page.expect_response(lambda r: '/friend-recommend' in r.url):
                search.fill('')
        heading = self.page.locator('h3:visible,h4:visible').filter(has_text=re.compile('^霖感小秘书$'))
        expect(heading).to_have_count(1)
        heading.click()
        water = self.page.get_by_role('button', name=re.compile(r'^(浇水|已浇水！|Water Garden|Watered!)$'))
        expect(water).to_have_count(1)
        outcome = self.water_button(water, '霖感小秘书')
        self.checks.append('自己处于冷却，已切换小秘书；' + ('小秘书也在冷却，本轮未再次浇水' if outcome == 'cooldown' else '已实际完成向小秘书浇水'))
        return outcome

    def water_peer(self):
        with self.test_peer() as (other, peer_id, peer_name, own_id, own_name):
            for actor, uid, name, label in [(self, peer_id, peer_name, '账号B'), (other, own_id, own_name, '账号A')]:
                card = actor.find_test_peer(uid, name)
                card.locator('h3:visible,h4:visible').filter(has_text=re.compile('^'+re.escape(name)+'$')).click()
                water = actor.page.get_by_role('button', name=re.compile(r'^(浇水|已浇水！|Water Garden|Watered!)$'))
                expect(water).to_have_count(1)
                outcome = actor.water_button(water, label)
                self.checks.append(('A→B' if actor is self else 'B→A') + ('：24小时内已浇水，保护分支通过' if outcome == 'cooldown' else '：本轮浇水成功'))
            self.extra_images.append(('account-b-water', other.page.screenshot(full_page=False)))

    def kindness_task_button(self):
        self.go('weekly_tasks')
        title = self.page.get_by_role('heading', name=re.compile('日行一善|每日善行|接受.*绽放')).first
        expect(title).to_be_visible()
        return title.locator('xpath=ancestor::div[./button][1]').locator(':scope > button').last

    def publish_kindness(self):
        field = self.page.get_by_placeholder('开始书写...', exact=True)
        expect(field).to_be_visible()
        content = '日行一善 ' + self.stamp + ' ' + self.run_key
        field.fill(content)
        public = self.button('公开')
        if public.count() and public.is_visible():
            public.click()
        expect(self.button('私密')).to_be_visible()
        self.publish_post(self.button('完成并绽放'), content, False)
        self.home()
        self.verify_post()
        self.checks.append('已发布并保留私密日行一善时间戳记录：' + content)

    def kindness_home(self):
        self.home()
        section = self.page.locator('section:visible').filter(has=self.page.get_by_text('日行一善', exact=True)).last
        expect(section).to_be_visible()
        action = section.locator('button').last
        expect(action).to_contain_text(re.compile('标记完成|已完成'))
        if '已完成' not in action.inner_text():
            expect(action).to_be_enabled(timeout=15000)
            action.click()
            self.publish_kindness()
        else:
            self.checks.append('首页日行一善已完成，未重复发布')
        expect(self.kindness_task_button()).to_contain_text('已完成', timeout=15000)
        self.checks.append('首页与每日任务中的日行一善完成状态一致')

    def kindness_task(self):
        action = self.kindness_task_button()
        expect(action).to_contain_text(re.compile('去完成|已完成'))
        if '已完成' not in action.inner_text():
            expect(action).to_be_enabled(timeout=15000)
            action.click()
            self.publish_kindness()
        else:
            self.checks.append('每日任务中的日行一善已完成，未重复发布')
        expect(self.kindness_task_button()).to_contain_text('已完成', timeout=15000)

    def profile(self):
        self.edit_profile(True)

    def avatar(self):
        self.edit_profile(False)

    def edit_profile(self, change_signature):
        self.go('profile')
        self.page.locator('button[aria-label="编辑资料"]:visible').click()
        expect(self.page.get_by_text('个性签名', exact=True)).to_be_visible()
        avatars = self.page.locator('div.flex.flex-wrap.justify-center.gap-2 button:not(.border-indigo-200)')
        expect(avatars.first).to_be_visible()
        avatar=avatars.nth(random.randrange(avatars.count()))
        avatar_text=avatar.inner_text().strip()
        avatar.click()
        field = self.page.locator('textarea:visible')
        original = field.input_value()
        signature = 'UI测试 ' + self.stamp + ' ' + self.run_key if change_signature else original
        if change_signature:
            field.fill(signature)
        self.submit(self.button('保存'), '/user', 'PUT')
        expect(self.page.get_by_text('个性签名', exact=True)).to_be_hidden()
        self.home()
        self.go('profile')
        self.page.locator('button[aria-label="编辑资料"]:visible').click()
        expect(self.page.locator('textarea:visible')).to_have_value(signature)
        expect(self.page.locator('div.flex.flex-wrap.justify-center.gap-2 button.border-indigo-200')).to_have_text(avatar_text)
        self.checks.append('已重新打开编辑页核对头像保存；' + ('时间戳签名已保存，昵称未修改' if change_signature else '昵称和个性签名保持原值'))
        self.button('取消').click()
