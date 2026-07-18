"""Menu permission registry.

这个文件是后台菜单权限的唯一配置入口：
- 新增一个普通功能菜单：改 MENU_OPTIONS。
- 新增管理员专属菜单：改 ADMIN_MENU 或扩展管理员判断逻辑。
- 不要在接口文件里手写权限列表，统一使用 ADMIN_MENU_KEYS。
"""

MENU_OPTIONS = [
    {"key": "files", "label": "文件快传"},
    {"key": "images", "label": "图片工具"},
    {"key": "data_generator", "label": "数据生成"},
    {"key": "json_tools", "label": "JSON 工具"},
    {"key": "codec", "label": "转码工具"},
    {"key": "integrations", "label": "集成配置"},
]

ADMIN_MENU = {"key": "users", "label": "用户管理"}
ADMIN_MENU_KEYS = [item["key"] for item in MENU_OPTIONS] + [ADMIN_MENU["key"]]
ALL_MENU_KEYS = set(ADMIN_MENU_KEYS)
