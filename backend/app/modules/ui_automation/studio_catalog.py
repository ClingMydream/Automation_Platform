"""Versioned UI-only scenarios. Steps are declarative; no executable user code."""
VERSION = 'studio-20261104-mutual-social'
LEGACY_POST_STEPS = [{'action': a, 'label': l} for a, l in [
    ('home', '从首页开始'), ('create_post', '随机心情与标签，发布时间戳私密动态'), ('verify_post', '检查本人的私密帖子')]]
FLOWS = [
    ('login', '登录', [('login', '账号密码登录'), ('home', '确认首页可操作')]),
    ('post', '发帖', [('home', '从首页开始'), ('dual_post', '账号 A、B 分别随机心情与标签，发布私密时间戳动态并保留')]),
    ('delete_post', '删帖', [('home', '从首页开始'), ('create_post', '创建专用私密测试帖'), ('delete_post', '删除本次测试帖并核对列表移除')]),
    ('like', '点赞', [('home', '从首页开始'), ('mutual_like', '账号 A、B 互相点赞对方任务帖并验证保存')]),
    ('comment', '评论', [('home', '从首页开始'), ('mutual_comment', '账号 A、B 互相评论对方任务帖并验证保存')]),
    ('cross_comment', '双账号任务互评', [('home', '从首页开始'), ('cross_comment', 'AI 依据双方每日任务生成自然正文并互评，保留帖子与评论')]),
    ('favorite', '收藏', [('home', '从首页开始'), ('mutual_favorite', '账号 A、B 互相收藏对方任务帖并验证保存')]),
    ('friend', '添加好友', [('home', '从首页开始'), ('friend', '向专用测试账号发起好友申请并检查关系')]),
    ('chat', '聊天', [('home', '从首页开始'), ('chat', '向霖感小秘书发送聊天测试与时间戳')]),
    ('peer_chat', '双账号聊天', [('home', '从首页开始'), ('peer_chat', '专用账号 A、B 互相发送消息并验证接收')]),
    ('daily_task', '每日任务', [('home', '从首页开始'), ('daily_task', '完成签到与浇水，已完成时核对状态')]),
    ('kindness_home', '首页日行一善', [('home', '从首页开始'), ('kindness_home', '通过首页日行一善入口完成任务并核对每日任务状态')]),
    ('kindness_task', '每日任务日行一善', [('home', '从首页开始'), ('kindness_task', '从每日任务入口完成日行一善；已完成时核对状态')]),
    ('watering', '浇水', [('home', '从首页开始'), ('watering', '自己及小秘书都冷却时，专用账号 A、B 互相浇水')]),
    ('profile', '修改资料', [('home', '从首页开始'), ('profile', '随机头像与时间戳签名，保存并核对')]),
    ('avatar', '切换头像', [('home', '从首页开始'), ('avatar', '切换为另一个头像，保存后重新打开核对')]),
    ('delete_friend', '删除好友', [('home', '从首页开始'), ('delete_friend', '核对专用账号 B，删除好友并验证关系移除')]),
]
FLOW_ACTIONS = {action for _, _, steps in FLOWS for action, _ in steps}
FLOW_ACTIONS.update({'click','fill','press','assert_visible','assert_text','open'})


def rows():
    return [{'key': key, 'name': name, 'steps': [{'action': action, 'label': label} for action, label in steps]}
            for key, name, steps in FLOWS]

LEGACY_INTERACTION_STEPS = {'like': [{'action': 'home', 'label': '从首页开始'}, {'action': 'own_post', 'label': '定位本次本人私密帖子'}, {'action': 'like', 'label': '点赞并检查选中状态'}], 'comment': [{'action': 'home', 'label': '从首页开始'}, {'action': 'own_post', 'label': '定位本次本人私密帖子'}, {'action': 'comment', 'label': '评论自己并检查内容'}], 'favorite': [{'action': 'home', 'label': '从首页开始'}, {'action': 'own_post', 'label': '定位本次本人私密帖子'}, {'action': 'favorite', 'label': '收藏自己并检查选中状态'}]}
LEGACY_INTERACTION_STEPS.update({
    'cross_comment': [{'action':'home','label':'从首页开始'}, {'action':'cross_comment','label':'AI 依据双方每日任务生成公开测试帖及时间戳评论，互评后保留记录'}],
    'watering': [{'action':'home','label':'从首页开始'}, {'action':'watering','label':'先给自己浇水；冷却时改给霖感小秘书浇水'}],
})
