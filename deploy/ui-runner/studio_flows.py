"""Emote page objects for UI-only scenarios; business writes go through the UI."""
import random
import re
import uuid
from datetime import datetime
from zoneinfo import ZoneInfo
from playwright.sync_api import expect


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
            assert action in {'login','home','create_post','verify_post','own_post','like','comment','favorite','delete_post','friend','chat','daily_task','profile'}, '不支持的步骤'
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
        account = self.credentials.get('account_a', {})
        assert account.get('username') and account.get('password'), '测试数据集缺少账号 A'
        self.page.get_by_placeholder('手机号', exact=True).fill(str(account['username']))
        self.page.locator('input[type=password]:visible').fill(str(account['password']))
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

    def friend(self):
        self.go('chat')
        peer = self.credentials.get('smoke', {}).get('friend_name') or self.credentials.get('account_b', {}).get('username')
        assert peer, '添加好友需要数据集中的专用账号 B 或 smoke.friend_name'
        b = self.credentials.get('account_b',{})
        peer_name=None
        if b.get('username') and b.get('password'):
            assert b['username'] != self.credentials.get('account_a',{}).get('username'), '好友测试账号必须与账号 A 不同'
            peer_context=self.page.context.browser.new_context(viewport={'width':390,'height':844})
            try:
                peer_page=peer_context.new_page()
                peer_pages=EmotePages(peer_page,self.base,{'account_a':b})
                peer_pages.login()
                peer=peer_page.evaluate("localStorage.getItem('emote_current_session')")
                peer_pages.go('profile')
                peer_name=peer_page.locator('h3.profile-card__title:visible').inner_text().strip()
                assert peer, '专用测试账号 B 的身份未获取'
            finally:
                peer_context.close()
        with self.page.expect_response(lambda r:'/friend-recommend' in r.url and str(peer) in (r.request.post_data or '')) as result:
            self.page.get_by_placeholder('寻找灵魂...', exact=True).fill(str(peer))
        assert result.value.ok and result.value.json().get('success') is True, '搜索专用测试好友失败'
        expect(self.page.get_by_text('同步原野中...',exact=True)).to_be_hidden(timeout=15000)
        pending=self.page.get_by_text('已发送',exact=True)
        if pending.count()==1 and pending.is_visible():
            self.checks.append('已有发给专用账号 B 的申请，已核对已发送状态；本轮未重复申请')
            return
        assert peer_name, '重置关系前必须通过账号 B 的个人页核对昵称'
        peer_heading=self.page.locator('h3:visible,h4:visible').filter(has_text=re.compile('^'+re.escape(peer_name))).first
        peer_cards=peer_heading.locator("xpath=ancestor::div[contains(@class,'justify-between') and contains(@class,'rounded-3xl')][1]")
        peer_chats=peer_cards.locator('button:has(.lucide-message-circle):visible')
        if peer_chats.count():
            if self.credentials.get('smoke',{}).get('reset_test_friendship_once') is not True or not b.get('password'):
                raise TestDataRequired('账号 A、B 已是好友；需未建立好友关系的专用账号，未删除现有关系或聊天记录')
            chats=peer_chats
            assert chats.count()==1, '专用好友搜索结果不唯一，未重置任何关系'
            chats.click()
            self.page.locator('button:has(.lucide-ellipsis-vertical):visible,button:has(.lucide-more-vertical):visible').click()
            self.button('删除好友').click()
            self.submit(self.button('删除'), '/friends', 'DELETE')
            self.checks.append('依据本次明确授权，仅重置已核对的专用 A/B 好友关系及聊天记录')
            self.home()
            self.go('chat')
            if self.page.get_by_placeholder('寻找灵魂...',exact=True).input_value():
                with self.page.expect_response(lambda r:'/friend-recommend' in r.url and 'exactMatch' not in (r.request.post_data or '')):
                    self.page.get_by_placeholder('寻找灵魂...',exact=True).fill('')
            with self.page.expect_response(lambda r:'/friend-recommend' in r.url and str(peer) in (r.request.post_data or '')):
                self.page.get_by_placeholder('寻找灵魂...',exact=True).fill(str(peer))
            expect(self.page.get_by_text('同步原野中...',exact=True)).to_be_hidden(timeout=15000)
        add = self.page.locator('button:has(.lucide-user-plus):visible')
        expect(add.first).to_be_visible()
        assert add.count() == 1, '搜索结果不唯一，拒绝向未知用户发送申请'
        self.submit(add, '/friends', 'POST')
        expect(self.page.get_by_text('已发送', exact=True)).to_be_visible()

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
        if water_task.is_disabled():
            expect(water_task).to_contain_text('已完成')
            return
        self.go('profile')
        water = self.page.locator('button:has(.lucide-droplets):visible').first
        expect(water).to_be_visible()
        result=self.submit(water, '/water', 'POST')
        if isinstance(result,dict) and result.get('success') is False:
            last=result.get('lastWateringTime')
            seconds=result.get('remainingSeconds')
            assert last and isinstance(seconds,(int,float)) and 0<seconds<=86400, '浇水被拒绝，且不符合已浇水冷却条件'
            assert '24小时' in str(result.get('error','')), '浇水失败原因不是重复浇水保护'
            expect(self.page.get_by_text(result['error'],exact=True).last).to_be_visible()
            self.checks.append('已验证24小时浇水冷却提示；本轮未重复浇水，保留此前成功记录')
        else:
            assert isinstance(result,dict) and result.get('success') is True, '浇水响应缺少成功标志'
            expect(self.page.get_by_text('浇水成功！', exact=True).last).to_be_visible()
            self.checks.append('本轮通过页面完成浇水')

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
