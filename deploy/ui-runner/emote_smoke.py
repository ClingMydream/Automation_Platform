"""Whitelisted real Emote flows. No eval/user scripts, no mocked business responses."""
import json
import time
import uuid
from datetime import datetime, timezone, timedelta
from urllib.parse import urlsplit, urlunsplit, urlencode, parse_qs

from playwright.sync_api import expect
from smoke_catalog import SMOKE_KEYS


class ScenarioBlocked(Exception):
    """Missing safe fixtures or explicit consent; never counted as passed."""


class SafetyStop(Exception):
    """A destructive operation could not be restored; stop the entire task."""


def envelope(body, status=200):
    value = body.get('data')
    return {'http_status': status, 'success': body.get('success'), 'code': body.get('code'),
            'message': str(body.get('message') or '')[:200],
            'data_shape': 'null' if value is None else ('bool' if isinstance(value, bool) else type(value).__name__),
            'data_bool': value if isinstance(value, bool) else None}


def items(body):
    value = body.get('data') or []
    return value if isinstance(value, list) else value.get('list', value.get('records', value.get('items', [])))


def deletion_allowed(base_url, api_root, credentials, allow_sensitive):
    """Only an explicit one-run opt-in, distinct B and the known test API qualify."""
    a, b = credentials.get('account_a', {}), credentials.get('account_b', {})
    target = urlsplit(api_root or '')
    return (allow_sensitive is True and target.scheme == 'https'
            and target.hostname == 'www.inxpiration.cn' and target.path.rstrip('/') == '/emote-test/api'
            and bool(a.get('username')) and bool(b.get('username')) and bool(b.get('password'))
            and a['username'] != b['username'])


class Flow:
    def __init__(self, page, contexts, variables, base_url, key):
        self.page, self.contexts, self.variables, self.base_url, self.key = page, contexts, variables, base_url.rstrip('/')+'/', key
        self.credentials = variables.get('_credentials', {})
        self.options = self.credentials.get('smoke') or {}
        self.root = None
        self.variables['_scenario_page'] = page
        self.checks = []
        self.variables['_scenario_result'] = {'scenario': key, 'checks': self.checks}
        self.cache = variables.setdefault('_smoke_cache', {})
        self.listener_page = page
        page.on('request', self.discover)

    def discover(self, request):
        parsed = urlsplit(request.url)
        if '/api/' in parsed.path:
            prefix, suffix = parsed.path.split('/api/', 1)
            if suffix.startswith(('user-extra/', 'posts-extra/', 'system-messages/')) and parsed.scheme in ('http','https'):
                root = urlunsplit((parsed.scheme, parsed.netloc, prefix+'/api', '', ''))
                if self.root is None:
                    self.root = root

    def close(self):
        self.listener_page.remove_listener('request', self.discover)

    def record(self, label, data=None):
        self.checks.append({'check': label, **(data or {})})
        emit = self.variables.get('_scenario_progress')
        if emit:
            emit(label, self.page)

    def need(self, condition, message):
        if not condition:
            raise AssertionError(message)

    def go(self, route):
        url = self.base_url+'?cling_smoke='+uuid.uuid4().hex+'#/'+route
        self.page.goto(url, wait_until='commit', timeout=30000)
        self.page.wait_for_timeout(1600)
        for label in ('跳过引导','开始体验'):
            button = self.page.get_by_role('button', name=label, exact=True)
            if button.count() and button.first.is_visible():
                button.first.click()

    def token(self, page=None):
        return (page or self.page).evaluate("() => {try{return JSON.parse(localStorage.getItem('emoted_tokens')||'{}').accessToken||''}catch{return ''}}")

    def request(self, method, path, body=None, token=None):
        if not self.root or not path.startswith('/'):
            raise ScenarioBlocked('未从实际页面请求识别到 Emote API，未发送辅助请求')
        bearer = token or (self.token() if path != '/login' else '')
        if not bearer and path != '/login':
            raise ScenarioBlocked('测试登录态缺失，不能准备业务夹具')
        try:
            response = self.page.context.request.fetch(self.root+path, method=method,
                headers={'Content-Type':'application/json', **({'Authorization':'Bearer '+bearer} if bearer else {})},
                data=json.dumps(body) if body is not None else None, timeout=20000)
            data = response.json()
        except Exception:
            # Playwright request exceptions can include Authorization headers.
            raise ScenarioBlocked(f'辅助接口访问失败：{method} {path.split("?")[0]}，未记录请求头') from None
        if not isinstance(data, dict):
            raise AssertionError(f'辅助接口响应不是对象：{method} {path}')
        return data

    def check_response(self, response, label):
        try:
            body = response.json()
        except Exception:
            raise AssertionError(label+'：接口未返回 JSON') from None
        safe = envelope(body, response.status)
        self.record('收到接口响应', {'operation': label, 'response': safe})
        self.need(response.ok and body.get('success') is True, label+'未成功：'+json.dumps(safe,ensure_ascii=False))
        self.record(label)
        return body

    def me(self):
        uid = self.page.evaluate("localStorage.getItem('emote_current_session')")
        if not uid:
            raise ScenarioBlocked('当前页面没有已登录测试账号')
        body = self.request('GET','/user-extra/basic/'+str(uid))
        self.need(body.get('success') is True, '读取测试账号资料失败')
        user = body.get('data') or {}
        self.need(str(user.get('id')) == str(uid), '测试账号身份无法确认')
        return user

    def login_peer(self, fresh=False):
        if 'peer' in self.cache and not fresh:
            return self.cache['peer']
        a, b = self.credentials.get('account_a',{}), self.credentials.get('account_b',{})
        if not b.get('username') or not b.get('password') or b.get('username') == a.get('username'):
            raise ScenarioBlocked('需要与账号 A 不同的专用测试账号 B')
        body = self.request('POST','/login',{'phone':b['username'],'password':b['password'],'deviceId':'cling-emote192-smoke'})
        auth = body.get('data') or {}
        if body.get('success') is not True or not auth.get('accessToken') or not (auth.get('user') or {}).get('id'):
            raise ScenarioBlocked('专用测试账号 B 登录失败；未输出凭据')
        self.cache['peer'] = auth
        return auth

    def nickname(self, kind):
        self.go('profile')
        self.page.get_by_role('button',name='编辑资料',exact=True).first.click()
        field = self.page.locator('input[type=text]:visible')
        field.wait_for()
        save = self.page.get_by_role('button',name='保存',exact=True)
        if kind == 'pending':
            field.fill('校验'+uuid.uuid4().hex[:6]);self.page.wait_for_timeout(100)
            self.need(save.is_disabled(),'昵称输入后 500ms 防抖等待期间保存仍可点击')
            self.record('待校验昵称禁止保存');return
        value = ('校验'+uuid.uuid4().hex[:6]) if kind == 'available' else (
            str(self.login_peer()['user'].get('userName') or '') if kind == 'duplicate' else self.options.get('sensitive_nickname','操你妈'))
        if not value or len(value)>8:
            raise ScenarioBlocked('昵称样本需为 1 至 8 个字符')
        with self.page.expect_response(lambda r:'/check-username-duplicate' in r.url,timeout=15000) as event:
            field.fill(value)
        response=event.value;body=response.json();safe=envelope(body,response.status)
        self.record('收到真实昵称查重响应',{'response':safe});self.page.wait_for_timeout(350)
        if kind == 'available':
            self.need(body.get('success') is True and body.get('data') is None,'空闲昵称不符合 success=true/data=null 新契约：'+json.dumps(safe,ensure_ascii=False))
            expect(self.page.get_by_text('该昵称可以使用',exact=True)).to_be_visible()
            self.need(save.is_enabled(),'空闲昵称仍不能保存')
        elif kind == 'duplicate':
            self.need(body.get('success') is False and body.get('code')==409 and save.is_disabled(),'已占用昵称未按 code=409 拦截，或保存未禁用：'+json.dumps(safe,ensure_ascii=False))
            expect(self.page.get_by_text('该昵称已被占用',exact=True)).to_be_visible()
        else:
            self.need(body.get('success') is False and body.get('code')!=409 and save.is_disabled(),'违规昵称未被阻止')
            self.need(bool(body.get('message')) and body['message'] in self.page.locator('body').inner_text(),'未展示后端返回的违规原因')
        self.record('昵称提示及保存状态符合预期')

    def create_private_fixture(self):
        me=self.me();label='自动化测试 '+datetime.now(timezone(timedelta(hours=8))).strftime('%Y-%m-%d %H:%M:%S')+' '+uuid.uuid4().hex[:8]
        body={'id':'cling192-'+uuid.uuid4().hex,'userId':str(me['id']),'userName':me.get('userName'),'userAvatar':'🌱','content':label,
              'timestamp':int(time.time()*1000),'isPublic':False,'sentiment':'平静','analysis':{'sentiment':'平静','emoji':'🌱','colorHex':'#86efac','supportiveMessage':'自动化测试夹具'},'tags':[],'isKindnessPost':False}
        result=self.request('POST','/posts',body)
        if result.get('success') is not True:
            raise ScenarioBlocked('无法准备本轮私密测试帖：'+json.dumps(envelope(result),ensure_ascii=False))
        rows=items(self.request('POST','/posts-extra/published',{'userId':str(me['id']),'limit':100}))
        post=next((row for row in rows if row.get('content')==label and str(row.get('userId'))==str(me['id'])),None)
        if not post or post.get('isPublic') not in (False,0):
            raise ScenarioBlocked('新建测试帖的归属或私密属性无法确认，未执行删除')
        self.record('已确认本轮私密夹具归属；仅用于前置，不计为发帖场景通过')
        return post

    def card(self, content):
        return self.page.get_by_text(content,exact=True).first.locator("xpath=ancestor::div[.//button//*[contains(@class,'lucide-heart')]][1]")

    def find_in_feed(self, content):
        for _ in range(9):
            if self.page.get_by_text(content,exact=True).count():
                return self.card(content)
            self.page.mouse.move(200,620);self.page.mouse.wheel(0,1700);self.page.wait_for_timeout(600)
        raise ScenarioBlocked('目标测试动态不在本次可加载的原野列表中，未操作其他用户帖子')

    def delete_post(self, entry):
        if entry == 'meadow':
            fixture_id=self.options.get('public_fixture_id')
            if not fixture_id or self.options.get('allow_delete_public_fixture') is not True:
                raise ScenarioBlocked('原野删帖需在数据集中指定可丢弃公开测试帖 ID 并确认允许删除；不自动创建公开帖')
            me=self.me();rows=items(self.request('POST','/posts-extra/published',{'userId':str(me['id']),'limit':100}))
            post=next((x for x in rows if str(x.get('id'))==str(fixture_id)),None)
            if not post or str(post.get('userId'))!=str(me['id']) or post.get('isPublic') not in (True,1):
                raise ScenarioBlocked('未确认指定公开夹具为当前测试账号本人，拒绝删除')
        else:
            post=self.create_private_fixture()
        pid=str(post['id']);content=post['content']
        if entry=='profile':
            result=self.request('POST','/posts-extra/favorite/'+pid)
            self.need(result.get('success') is True,'准备个人收藏夹具失败')
            self.go('profile');self.page.get_by_role('button').filter(has_text='珍藏回声').click()
        else:self.go('community' if entry=='meadow' else 'home')
        card=self.find_in_feed(content) if entry=='meadow' else self.card(content)
        card.locator('button:has(.lucide-ellipsis-vertical)').click();self.page.get_by_role('button',name='删除动态',exact=True).click()
        with self.page.expect_response(lambda r:r.request.method=='DELETE' and r.url.rstrip('/').endswith('/posts/'+pid),timeout=15000) as event:
            self.page.get_by_role('button',name='确认',exact=True).click()
        self.check_response(event.value,'删除接口成功，不依赖 data===true')
        expect(self.page.get_by_text(content,exact=True)).to_have_count(0,timeout=8000)
        self.record('删除后当前列表立即移除本人动态')

    def favorite(self):
        post=self.create_private_fixture();pid=str(post['id']);content=post['content'];self.go('home')
        with self.page.expect_response(lambda r:r.request.method=='POST' and '/posts-extra/favorite/'+pid in r.url) as event:
            self.card(content).locator('button:has(.lucide-bookmark)').click()
        self.check_response(event.value,'收藏成功')
        self.go('profile');self.page.get_by_role('button').filter(has_text='珍藏回声').click()
        expect(self.page.get_by_text(content,exact=True).first).to_be_visible(timeout=12000);self.record('个人收藏列表同步新增')
        with self.page.expect_response(lambda r:r.request.method=='POST' and '/posts-extra/favorite/'+pid in r.url) as event:
            self.card(content).locator('button:has(.lucide-bookmark)').click()
        self.check_response(event.value,'取消收藏成功')
        expect(self.page.get_by_text(content,exact=True)).to_have_count(0,timeout=8000);self.record('个人收藏列表同步移除，保留私密测试帖')

    def ensure_not_blocked(self, peer_id):
        rows=items(self.request('GET','/blocks'))
        if any(str(x.get('id'))==str(peer_id) for x in rows):
            raise ScenarioBlocked('账号 B 原本已在黑名单，保留既有关系，未擅自移除')

    def restore_block(self, me_id, peer_id):
        try:
            self.request('DELETE','/block',{'blockerId':str(me_id),'blockedId':str(peer_id)})
            remaining=items(self.request('GET','/blocks'))
            if any(str(x.get('id'))==str(peer_id) for x in remaining):
                raise ValueError('still blocked')
        except Exception:
            raise SafetyStop('测试账号拉黑关系无法确认恢复，已停止后续用例，请人工核查') from None
        self.record('测试拉黑关系已恢复')

    def block(self, unblock_only=False):
        peer=self.login_peer();me=self.me();bid=str(peer['user']['id']);aid=str(me['id']);self.ensure_not_blocked(bid)
        changed=False
        try:
            if unblock_only:
                changed=True;result=self.request('POST','/block',{'blockerId':aid,'blockedId':bid})
                self.need(result.get('success') is True,'黑名单前置准备失败')
                self.go('profile');self.page.locator('button:has(.lucide-settings):visible').click();self.page.get_by_role('button',name='黑名单',exact=True).click()
                target=self.page.get_by_text(peer['user']['userName'],exact=True).last
                row=target.locator("xpath=ancestor::div[.//button//*[contains(@class,'lucide-trash')]][1]")
                row.locator('button:has(.lucide-trash-2)').click()
                with self.page.expect_response(lambda r:r.request.method=='DELETE' and r.url.endswith('/block')) as event:self.page.get_by_role('button',name='确认',exact=True).click()
                self.check_response(event.value,'移出黑名单成功');expect(target).to_have_count(0);self.record('黑名单列表同步移除')
            else:
                rows=items(self.request('POST','/posts-extra/published',{'userId':bid,'limit':100},peer['accessToken']))
                post=next((x for x in rows if x.get('isPublic') in (True,1) and str(x.get('userId'))==bid),None)
                if not post:raise ScenarioBlocked('测试账号 B 没有可用于拉黑的公开动态；不操作其他用户')
                self.go('community');card=self.find_in_feed(post['content'])
                self.need(card.get_by_text(peer['user']['userName'],exact=True).count()>0,'目标卡片作者与测试账号 B 不一致，未操作')
                def guard(route):
                    body=route.request.post_data_json or {}
                    if route.request.method=='POST' and str(body.get('blockedId'))!=bid:route.abort()
                    else:route.continue_()
                self.page.route('**/api/block',guard)
                try:
                    card.locator('button:has(.lucide-ellipsis-vertical)').click();self.page.get_by_role('button',name='拉黑用户',exact=True).click();changed=True
                    with self.page.expect_response(lambda r:r.request.method=='POST' and r.url.endswith('/block')) as event:self.page.get_by_role('button',name='确认',exact=True).click()
                    self.check_response(event.value,'拉黑接口成功');expect(self.page.get_by_text('已拉黑该用户',exact=True)).to_be_visible()
                    expect(self.page.get_by_text(peer['user']['userName'],exact=True)).to_have_count(0,timeout=8000);self.record('当前已加载原野列表不再显示测试用户')
                finally:self.page.unroute('**/api/block',guard)
        finally:
            if changed:self.restore_block(aid,bid)

    def chat(self):
        self.go('chat');name=self.page.get_by_text(self.options.get('chat_friend_name','霖感小秘书'),exact=True).first
        card=name.locator("xpath=ancestor::div[.//button//*[contains(@class,'lucide-message-circle')]][1]")
        card.locator('button:has(.lucide-message-circle)').click();self.page.get_by_placeholder('Message...',exact=True).wait_for()

    def remark(self):
        self.chat();self.page.locator('main button:has(.lucide-ellipsis-vertical):visible').last.click();self.page.get_by_role('button',name='修改备注',exact=True).click()
        field=self.page.get_by_placeholder('输入备注',exact=True);old=field.input_value();new='测试'+uuid.uuid4().hex[:6]
        query=parse_qs(urlsplit(self.page.url).fragment.partition('?')[2]);friend=query.get('friendId',[None])[0]
        if not friend:raise ScenarioBlocked('无法确定好友备注归属，未保存')
        aid=str(self.me()['id']);may_have_written=False;write_rejected=False
        try:
            field.fill(new);may_have_written=True
            with self.page.expect_response(lambda r:r.request.method=='PUT' and '/friends/remark' in r.url) as event:self.page.get_by_role('button',name='保存',exact=True).click()
            write_rejected = event.value.json().get('success') is False
            self.check_response(event.value,'好友备注保存成功');expect(self.page.get_by_text('备注修改成功',exact=True)).to_be_visible();expect(self.page.get_by_role('heading',name=new,exact=True)).to_be_visible();self.record('私聊顶部昵称更新')
        finally:
            if may_have_written:
                try:
                    restored=self.request('PUT','/friends/remark',{'userId':aid,'friendId':friend,'remark':old})
                    if restored.get('success') is True:self.record('好友原备注已恢复')
                    elif not write_rejected:raise SafetyStop('好友备注恢复失败，已停止后续用例')
                except SafetyStop:raise
                except Exception:
                    if not write_rejected:raise SafetyStop('好友备注无法确认恢复，已停止后续用例') from None

    def report(self):
        self.chat();text='聊天测试'+datetime.now(timezone(timedelta(hours=8))).strftime('%Y%m%d%H%M%S')+uuid.uuid4().hex[:4]
        field=self.page.get_by_placeholder('Message...',exact=True);field.fill(text);field.press('Enter');bubble=self.page.get_by_text(text,exact=True)
        expect(bubble).to_be_visible(timeout=15000);bubble.scroll_into_view_if_needed();bubble.dispatch_event('mousedown',{'button':0});self.page.wait_for_timeout(700)
        self.page.get_by_role('button',name='举报',exact=True).click();self.page.get_by_placeholder('请输入举报原因...',exact=True).fill('自动化专项测试：仅举报本轮测试消息，请忽略业务处理。')
        with self.page.expect_response(lambda r:r.request.method=='POST' and '/message-reports' in r.url) as event:self.page.get_by_role('button',name='提交举报',exact=True).click()
        self.check_response(event.value,'测试消息举报成功');expect(self.page.get_by_text('举报成功',exact=True)).to_be_visible()
        expect(self.page.get_by_placeholder('请输入举报原因...',exact=True)).to_have_count(0,timeout=6000);self.record('举报成功后关闭弹窗')

    def system(self, all_read=False):
        self.go('chat');self.page.get_by_role('button',name='系统消息',exact=True).click()
        categories=self.page.locator('[data-section=message-categories]');categories.wait_for();self.page.wait_for_timeout(600)
        if not categories.locator('span.bg-rose-500').count():raise ScenarioBlocked('测试账号没有未读系统消息，未伪造已读通过')
        if not all_read:
            with self.page.expect_response(lambda r:r.request.method=='GET' and '/system-messages?' in r.url and 'type=' in r.url) as listed:
                categories.locator('button').filter(has=self.page.locator('span.bg-rose-500')).first.click()
            list_path=listed.value.url.removeprefix(self.root)
            container=self.page.locator('[data-section=message-list]');container.wait_for()
            target=container.locator('button').filter(has=self.page.locator('span.bg-rose-500')).first;target.wait_for()
            before=container.locator('span.bg-rose-500').count()
            with self.page.expect_response(lambda r:r.request.method=='POST' and '/system-messages/read' in r.url) as event:target.click()
            self.check_response(event.value,'单条系统消息标记已读');self.page.wait_for_timeout(400)
            # A jump to another business page is legitimate, verify persisted read using the exact request IDs.
            sent=event.value.request.post_data_json or {};mid=sent.get('messageId')
            self.need(bool(mid) and sent.get('readAll') is False,'单条已读请求缺少 messageId 或误设为全部已读')
            rows=items(self.request('GET',list_path))
            saved=next((x for x in rows if str(x.get('id') or x.get('messageId'))==str(mid)),None)
            self.need(saved is not None and saved.get('read') is True,'单条已读状态未持久化')
            if container.count():
                self.need(container.locator('span.bg-rose-500').count()<before,'单条已读后列表红点未消退')
            else:
                self.go('chat');self.page.get_by_role('button',name='系统消息',exact=True).click()
                typ=parse_qs(urlsplit(list_path).query).get('type',[''])[0]
                group=next((x for x in items(self.request('GET','/system-messages?'+urlencode({'userId':sent.get('userId')}))) if x.get('type')==typ),None)
                self.need(group is not None,'已读后未能重新确认系统消息分类')
                self.page.get_by_role('button').filter(has_text=group.get('label') or typ).last.click()
                self.page.wait_for_timeout(500)
                self.need(self.page.locator('[data-section=message-list] span.bg-rose-500').count()<before,'返回列表后未读红点未消退')
            self.record('单条已读持久化且列表红点消退')
        else:
            with self.page.expect_response(lambda r:r.request.method=='POST' and '/system-messages/read' in r.url) as event:self.page.get_by_role('button',name='全部已读',exact=True).click()
            self.check_response(event.value,'系统消息全部标记已读');expect(self.page.get_by_role('button',name='全部已读',exact=True)).to_have_count(0)
            self.need(categories.locator('span.bg-rose-500').count()==0,'全部已读后红点未清除');self.record('全部已读后未读红点清除')

    def feedback(self):
        self.go('profile');self.page.locator('button:has(.lucide-settings):visible').click();self.page.get_by_role('button',name='反馈与帮助',exact=True).click();self.page.get_by_placeholder('...',exact=True).fill('自动化测试 1.9.2 '+uuid.uuid4().hex[:10]+'（专用测试反馈，无需业务处理）')
        with self.page.expect_response(lambda r:r.request.method=='POST' and r.url.endswith('/feedback')) as event:self.page.get_by_role('button',name='发送',exact=True).click()
        self.check_response(event.value,'意见反馈提交成功');expect(self.page.get_by_text('Sent!',exact=True)).to_be_visible();self.page.wait_for_timeout(2300)
        self.need(self.page.get_by_text('Sent!',exact=True).count()==0 and self.page.get_by_placeholder('...',exact=True).count()==0,'反馈成功后约两秒未收起表单');self.record('反馈成功状态与自动收起正常')

    def deletion(self):
        if not deletion_allowed(self.base_url,self.root,self.credentials,self.variables.get('_allow_sensitive')):
            raise ScenarioBlocked('注销未获本次授权，或不是 emote-test 专用环境 / 缺少独立账号 B')
        auth=self.login_peer(fresh=True);user=auth['user'];uid=str(user['id'])
        if user.get('isAdmin') or user.get('deletionStartTime'):raise ScenarioBlocked('账号 B 是管理员或原本已在冷静期，拒绝变更既有状态')
        page=self.contexts['account_b'].pages[0];self.page=page;self.variables['_scenario_page']=page;self.variables['_used_accounts']={'account_b'}
        page.goto(self.base_url,wait_until='commit',timeout=30000)
        state={'emoted_tokens':json.dumps({'accessToken':auth['accessToken'],'refreshToken':auth.get('refreshToken',''),'permissions':auth.get('permissions',[]),'expiresIn':auth.get('expiresIn'),'issuedAt':int(time.time()*1000)}),'emote_current_session':uid,'emote_agreed_terms':'true','emote_onboarding_completed':'true','emote_feature_guide_install':json.dumps({'status':'skipped','nextStep':5,'updatedAt':int(time.time()*1000)})}
        page.evaluate('(state)=>{for(const [k,v] of Object.entries(state)) localStorage.setItem(k,v)}',state)
        # Hide phone values in videos/screenshots, without changing form behavior.
        page.add_init_script("document.addEventListener('DOMContentLoaded',()=>{const s=document.createElement('style');s.textContent='input[type=tel]{-webkit-text-security:disc!important}';document.head.appendChild(s)})")
        may_have_requested=False
        try:
            self.go('profile');page.locator('button:has(.lucide-settings):visible').click();page.get_by_role('button',name='账号与安全',exact=True).click();page.get_by_role('button').filter(has_text='注销账号').click()
            may_have_requested=True
            with page.expect_response(lambda r:r.request.method=='POST' and '/deletion/request/' in r.url) as event:page.get_by_role('button',name='确认',exact=True).click()
            self.check_response(event.value,'专用账号 B 申请注销成功');page.wait_for_url(lambda url:url.endswith('#/login'),wait_until='commit',timeout=15000);self.record('申请后退出至登录页')
            page.get_by_role('button',name='登录',exact=True).click();account=self.credentials['account_b']
            page.locator("div[style*='pointer-events: auto'] input[type=tel][placeholder='手机号']").fill(account['username']);page.locator("div[style*='pointer-events: auto'] input[type=password]").fill(account['password'])
            toggle=page.locator('form button[type=button]:has(+ p):visible')
            if toggle.count() and 'bg-emerald-500' not in (toggle.get_attribute('class') or ''):toggle.click()
            page.get_by_role('button',name='进入心灵花园',exact=True).click();expect(page.get_by_role('heading',name='账号注销冷静期',exact=True)).to_be_visible(timeout=15000);self.record('冷静期登录弹出明确确认')
            with page.expect_response(lambda r:r.request.method=='POST' and '/deletion/cancel/' in r.url) as event:page.get_by_role('button',name='确认',exact=True).click()
            self.check_response(event.value,'取消注销接口成功');page.wait_for_url(lambda url:url.endswith('#/home'),wait_until='commit',timeout=15000);self.record('冷静期弹窗关闭并正常进入首页')
        finally:
            self.cache.pop('peer',None)
            if may_have_requested:
                restored=False
                for _ in range(2):
                    try:
                        fresh=self.login_peer(fresh=True)
                        result=self.request('POST','/user-extra/deletion/cancel/'+uid,token=fresh['accessToken'])
                        restored=(result.get('success') is True or (result.get('code')==400 and result.get('i18nKey')=='error.user.account_not_cancelling'))
                        if restored:break
                    except Exception:pass
                self.cache.pop('peer',None)
                if not restored:raise SafetyStop('专用账号 B 注销状态无法确认恢复，已停止整轮，请立即人工处理')
                self.record('专用账号 B 注销状态已安全恢复')


def run_scenario(page, contexts, step, variables, base_url):
    key=step.get('scenario')
    if key not in SMOKE_KEYS:
        raise ValueError('专项场景不在白名单中')
    flow=Flow(page,contexts,variables,base_url,key)
    try:
        if key=='deletion_cycle' and variables.get('_allow_sensitive') is not True:
            raise ScenarioBlocked('注销需本次执行单独勾选授权；未触碰任何账号状态')
        flow.go('home')
        if key.startswith('nickname_'):flow.nickname(key.removeprefix('nickname_'))
        elif key.startswith('delete_'):flow.delete_post(key.removeprefix('delete_'))
        elif key=='favorite_cycle':flow.favorite()
        elif key in ('block_user','unblock_user'):flow.block(key=='unblock_user')
        elif key=='friend_remark':flow.remark()
        elif key=='message_report':flow.report()
        elif key in ('system_single','system_all'):flow.system(key=='system_all')
        elif key=='feedback':flow.feedback()
        elif key=='deletion_cycle':flow.deletion()
        return flow.page
    finally:
        variables['_scenario_result']['checks']=flow.checks
        flow.close()
