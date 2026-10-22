"""Versioned, data-only Emote 1.9.2 smoke catalog (also copied to the runner)."""
CATALOG_VERSION = 'emote192-v1'
SMOKE_CATALOG = [
    ('nickname_available', 'profile', '修改资料', '昵称可用与 data=null 契约', 'P1'),
    ('nickname_duplicate', 'profile', '修改资料', '已占用昵称拦截与 code=409 契约', 'P1'),
    ('nickname_sensitive', 'profile', '修改资料', '违规昵称原因提示与禁止保存', 'P1'),
    ('nickname_pending', 'profile', '修改资料', '昵称等待校验时禁止保存', 'P1'),
    ('delete_home', 'delete_post', '删帖', '首页删除本轮本人私密动态', 'P1'),
    ('delete_profile', 'delete_post', '删帖', '个人收藏页删除本人动态并移除卡片', 'P1'),
    ('delete_meadow', 'delete_post', '删帖', '原野删除指定可丢弃公开测试动态', 'P1'),
    ('favorite_cycle', 'favorite', '收藏', '收藏与取消收藏同步个人列表', 'P1'),
    ('block_user', 'block', '拉黑管理', '拉黑测试用户并过滤当前原野动态', 'P1'),
    ('unblock_user', 'block', '拉黑管理', '黑名单移除测试用户', 'P1'),
    ('friend_remark', 'chat', '聊天', '好友备注保存与顶部昵称更新', 'P1'),
    ('message_report', 'chat', '聊天', '举报本轮测试消息并关闭弹窗', 'P1'),
    ('system_single', 'system_message', '系统消息', '单条系统消息已读并清除红点', 'P1'),
    ('system_all', 'system_message', '系统消息', '系统消息全部已读并清除角标', 'P1'),
    ('feedback', 'feedback', '意见反馈', '反馈提交成功并在两秒后收起', 'P1'),
    ('deletion_cycle', 'account_security', '账号与安全', '专用账号申请注销与冷静期取消登录', 'P1'),
]
SMOKE_KEYS = frozenset(row[0] for row in SMOKE_CATALOG)
SENSITIVE_KEYS = frozenset({'deletion_cycle'})

def catalog_rows():
    return [{'key': k, 'feature_key': f, 'feature_name': fn, 'name': n, 'priority': p,
             'sensitive': k in SENSITIVE_KEYS} for k, f, fn, n, p in SMOKE_CATALOG]
