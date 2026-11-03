"""Versioned UI-only scenarios. Steps are declarative; no executable user code."""
VERSION = 'studio-20261103'
FLOWS = [
    ('login', '登录', [('login', '账号密码登录'), ('home', '确认首页可操作')]),
    ('post', '发帖', [('home', '从首页开始'), ('create_post', '随机心情与标签，发布时间戳私密动态'), ('verify_post', '检查本人的私密帖子')]),
    ('delete_post', '删帖', [('home', '从首页开始'), ('create_post', '创建专用私密测试帖'), ('delete_post', '删除本次测试帖并核对列表移除')]),
    ('like', '点赞', [('home', '从首页开始'), ('own_post', '定位本次本人私密帖子'), ('like', '点赞并检查选中状态')]),
    ('comment', '评论', [('home', '从首页开始'), ('own_post', '定位本次本人私密帖子'), ('comment', '评论自己并检查内容')]),
    ('favorite', '收藏', [('home', '从首页开始'), ('own_post', '定位本次本人私密帖子'), ('favorite', '收藏自己并检查选中状态')]),
    ('friend', '添加好友', [('home', '从首页开始'), ('friend', '向专用测试账号发起好友申请并检查关系')]),
    ('chat', '聊天', [('home', '从首页开始'), ('chat', '向霖感小秘书发送聊天测试与时间戳')]),
    ('daily_task', '每日任务', [('home', '从首页开始'), ('daily_task', '完成签到与浇水，已完成时核对状态')]),
    ('profile', '修改资料', [('home', '从首页开始'), ('profile', '随机头像与时间戳签名，保存并核对')]),
]
FLOW_ACTIONS = {action for _, _, steps in FLOWS for action, _ in steps}
FLOW_ACTIONS.update({'click','fill','press','assert_visible','assert_text','open'})


def rows():
    return [{'key': key, 'name': name, 'steps': [{'action': action, 'label': label} for action, label in steps]}
            for key, name, steps in FLOWS]
