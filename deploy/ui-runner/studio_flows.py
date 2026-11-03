"""Emote page objects for UI-only scenarios; business writes go through the UI."""
import random
import re
import uuid
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
        self.stamp = datetime.now(ZoneInfo('Asia/Shanghai')).strftime('%Y-%m-%d %H:%M:%S')
        self.run_key = uuid.uuid4().hex[:6]
        self.checks = []

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
            assert action in {'login','home','create_post','verify_post','own_post','like','comment','favorite','delete_post','friend','delete_friend','chat','daily_task','profile'}, '不支持的步骤'
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
        text = self.page.locator('p:visible').filter(has_text=re.compile('^'+re.escape(self.post_text)+'$')).first
        expect(text).to_be_visible()
        return text.locator("xpath=ancestor::div[contains(@class,'rounded-[28px]') and contains(@class,'group')][1]")

    def create_post(self):
        content = self.stamp + ' UI测试 ' + self.run_key + '-' + uuid.uuid4().hex[:4]
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
        public = self.button('公开')
        if public.count() and public.is_visible():
            public.click()
        expect(self.button('私密')).to_be_visible()
        data = self.submit(self.button('释放心语'), '/posts', 'POST')
        self.post_text = content
        self.post_id = data.get('id') if isinstance(data, dict) else data
        self.verify_post()
        self.checks.append(f'已随机选择心情「{mood_text}」与标签「{tag_text}」，发布本人私密时间戳动态')

    def verify_post(self):
        expect(self.card().get_by_text('私密', exact=True)).to_be_visible()

    def own_post(self):
        # Reuse the post within a chain; standalone scenarios create their own fixture via UI.
        if not self.post_text:
            self.create_post()
        else:
            self.home()
            self.verify_post()

    def like(self):
        card = self.card()
        heart = card.locator('button:has(.lucide-heart)')
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
        card = self.card()
        card.locator('button:has(.lucide-ellipsis-vertical), button:has(.lucide-more-vertical)').click()
        card.get_by_role('button', name='删除动态', exact=True).click()
        self.submit(self.button('确认'), '/posts/', 'DELETE')
        expect(self.page.get_by_text(self.post_text, exact=True)).to_have_count(0)
        self.post_text = None

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
        context = self.page.context.browser.new_context(viewport={'width':390,'height':844})
        try:
            other = EmotePages(context.new_page(), self.base, {'account_a': account_b})
            other.login()
            other.go('profile')
            peer_id = other.page.evaluate("localStorage.getItem('emote_current_session')")
            peer_name = other.page.locator('h3.profile-card__title:visible').inner_text().strip()
            assert peer_id and peer_name and peer_id != own_id, '账号 B 身份未确认或与 A 相同，未执行好友操作'
            yield other, peer_id, peer_name, own_id, own_name
        finally:
            context.close()

    def find_test_peer(self, peer_id, peer_name):
        self.home()
        self.go('chat')
        search = self.page.get_by_placeholder('寻找灵魂...', exact=True)
        if search.input_value():
            with self.page.expect_response(lambda r: '/friend-recommend' in r.url):
                search.fill('')
        with self.page.expect_response(lambda r: '/friend-recommend' in r.url and str(peer_id) in (r.request.post_data or '')) as result:
            search.fill(str(peer_id))
        body = result.value.json()
        assert result.value.ok and body.get('success') is True, '搜索专用测试好友失败'
        expect(self.page.get_by_text('同步原野中...',exact=True)).to_be_hidden(timeout=15000)
        heading = self.page.locator('h3:visible,h4:visible').filter(has_text=re.compile('^'+re.escape(peer_name)+'$'))
        expect(heading).to_have_count(1)
        card = heading.locator("xpath=ancestor::div[contains(@class,'justify-between') and contains(@class,'rounded-3xl')][1]")
        expect(card).to_have_count(1)
        return card

    def peer_is_friend(self, card):
        return card.locator('button:has(.lucide-message-circle):visible').count() == 1

    def remove_test_peer(self, card, peer_id, peer_name):
        chat = card.locator('button:has(.lucide-message-circle):visible')
        expect(chat).to_have_count(1)
        chat.click()
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
        self.submit(add, '/friends', 'POST')
        expect(card.get_by_text('已发送', exact=True)).to_be_visible()
        self.checks.append('已通过 UI 向身份核对后的专用账号 B 发送好友申请')

    def friend(self):
        with self.test_peer() as (_, peer_id, peer_name, _, __):
            card = self.find_test_peer(peer_id, peer_name)
            if self.peer_is_friend(card):
                card = self.remove_test_peer(card, peer_id, peer_name)
            self.request_test_peer(card)

    def delete_friend(self):
        with self.test_peer() as (other, peer_id, peer_name, own_id, own_name):
            card = self.find_test_peer(peer_id, peer_name)
            if not self.peer_is_friend(card):
                # Prepare the missing relationship through both test accounts' UI.
                accept = card.locator('button:has(.lucide-check):visible')
                if accept.count() == 1:
                    self.submit(accept, '/friends/accept', 'POST')
                else:
                    self.request_test_peer(card)
                    received = other.find_test_peer(own_id, own_name)
                    accept = received.locator('button:has(.lucide-check):visible')
                    expect(accept).to_have_count(1)
                    other.submit(accept, '/friends/accept', 'POST')
                card = self.find_test_peer(peer_id, peer_name)
                assert self.peer_is_friend(card), '删除好友前未成功建立专用 A/B 好友关系，未报告删除成功'
                self.checks.append('前置准备：通过 UI 接受专用 A/B 好友申请并确认关系')
            self.remove_test_peer(card, peer_id, peer_name)

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
        self.go('profile')
        water = self.page.locator('button:has(.lucide-droplets):visible').first
        expect(water).to_be_visible()
        with self.page.expect_response(lambda r: '/user-watering/water' in r.url and r.request.method == 'POST') as result:
            water.click()
        response = result.value
        outcome, message = watering_outcome(response.json(), response.ok)
        if outcome == 'cooldown':
            expect(self.page.get_by_text(message,exact=True).last).to_be_visible()
            self.checks.append('通过：24小时内已浇水，冷却保护分支符合预期；本轮未重复浇水')
        else:
            expect(self.page.get_by_text('浇水成功！', exact=True).last).to_be_visible()
            self.checks.append('通过：本轮通过页面完成浇水，成功分支符合预期')

    def profile(self):
        self.go('profile')
        self.page.locator('button[aria-label="编辑资料"]:visible').click()
        expect(self.page.get_by_text('个性签名', exact=True)).to_be_visible()
        avatars = self.page.locator('div.flex.flex-wrap.justify-center.gap-2 button:not(.border-indigo-200)')
        expect(avatars.first).to_be_visible()
        avatar=avatars.nth(random.randrange(avatars.count()))
        avatar_text=avatar.inner_text().strip()
        avatar.click()
        field = self.page.locator('textarea:visible')
        signature = 'UI测试 ' + self.stamp + ' ' + self.run_key
        field.fill(signature)
        self.submit(self.button('保存'), '/user', 'PUT')
        expect(self.page.get_by_text('个性签名', exact=True)).to_be_hidden()
        self.home()
        self.go('profile')
        self.page.locator('button[aria-label="编辑资料"]:visible').click()
        expect(self.page.locator('textarea:visible')).to_have_value(signature)
        expect(self.page.locator('div.flex.flex-wrap.justify-center.gap-2 button.border-indigo-200')).to_have_text(avatar_text)
        self.checks.append('已重新打开编辑页核对随机头像和时间戳签名均已保存；昵称未修改')
        self.button('取消').click()
