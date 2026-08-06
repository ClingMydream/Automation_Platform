from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.entities import CommandSnippet

BUILTINS = [
    ("MySQL", "登录数据库", "mysql -h 主机 -P 3306 -u 用户名 -p", "连接指定 MySQL 服务，回车后安全输入密码。", "mysql -h 127.0.0.1 -P 3306 -u root -p", "-p 后不要直接写密码，避免出现在历史记录中。", ["连接", "安全"]),
    ("MySQL", "查看数据库和表", "SHOW DATABASES;\nUSE 数据库名;\nSHOW TABLES;", "先选择数据库，再查看其中的数据表。", "USE automation_platform;\nSHOW TABLES;", "SHOW DATABASES、USE、SHOW TABLES 是常见基础题。", ["查看", "基础"]),
    ("MySQL", "查询与限制条数", "SELECT * FROM 表名 WHERE 条件 ORDER BY 字段 DESC LIMIT 20;", "按条件筛选、排序并限制返回数量，避免全表返回过多数据。", "SELECT * FROM users WHERE status=1 ORDER BY id DESC LIMIT 20;", "需要能解释 WHERE、ORDER BY、LIMIT 的执行作用。", ["查询", "SQL"]),
    ("MySQL", "查看执行计划", "EXPLAIN SELECT ...;", "查看查询是否使用索引、扫描行数和连接方式。", "EXPLAIN SELECT * FROM users WHERE phone='13800138000';", "重点关注 type、possible_keys、key、rows、Extra。", ["索引", "性能"]),
    ("MySQL", "查看和终止连接", "SHOW PROCESSLIST;\nKILL 连接ID;", "排查长时间运行或阻塞的数据库连接，确认后再终止。", "SHOW FULL PROCESSLIST;\nKILL 12345;", "KILL 属于有副作用命令，生产环境必须先确认连接。", ["排查", "高风险"]),
    ("Linux", "查看日志末尾", "tail -n 200 文件.log\ntail -f 文件.log", "查看最后 200 行或持续追踪新增日志。", "tail -f /var/log/nginx/error.log", "tail -f 常用于实时观察，Ctrl+C 退出。", ["日志", "常用"]),
    ("Linux", "搜索日志关键字", "grep -n -C 3 '关键字' 文件.log", "显示匹配行号以及前后各 3 行上下文。", "grep -n -C 3 'ERROR' app.log", "常结合 -i 忽略大小写、-r 递归、-v 反向过滤。", ["日志", "搜索"]),
    ("Linux", "查看进程", "ps aux | grep 进程名\ntop", "查询指定进程，并实时查看 CPU 和内存占用。", "ps aux | grep java", "ps 是快照，top 是动态视图；避免把 grep 自身当作目标进程。", ["进程", "排查"]),
    ("Linux", "查看端口监听", "ss -lntp", "查看 TCP 监听端口以及对应进程。", "ss -lntp | grep 8080", "服务无法访问时按进程、端口、防火墙、网络顺序排查。", ["端口", "网络"]),
    ("Linux", "查看磁盘与目录大小", "df -h\ndu -sh 目录", "df 查看文件系统空间，du 查看指定目录实际占用。", "du -sh /var/lib/docker", "磁盘满时先定位大目录，不要直接删除未知文件。", ["磁盘", "排查"]),
    ("Linux", "查看内存", "free -h", "查看总内存、已用内存、可用内存和 Swap。", "free -h", "Linux 中 available 比 free 更能反映实际可用内存。", ["内存", "面试"]),
    ("Redis", "连接 Redis", "redis-cli -h 主机 -p 6379 -a 密码", "连接 Redis；生产环境更推荐通过环境变量或安全配置提供密码。", "redis-cli -h 127.0.0.1 -p 6379", "Redis 默认端口 6379，不应直接暴露到公网。", ["连接", "安全"]),
    ("Redis", "查看键和值", "TYPE 键名\nGET 键名\nHGETALL 键名", "先判断数据类型，再使用对应命令读取。", "TYPE user:1\nHGETALL user:1", "GET 只适用于 string；哈希使用 HGET/HGETALL。", ["查询", "数据类型"]),
    ("Redis", "查看过期时间", "TTL 键名\nEXPIRE 键名 秒数", "TTL 查看剩余秒数，EXPIRE 设置过期时间。", "TTL login:token:123\nEXPIRE login:token:123 3600", "TTL 返回 -1 表示永久，-2 表示键不存在。", ["过期", "缓存"]),
    ("Redis", "安全扫描键", "SCAN 0 MATCH 模式 COUNT 100", "渐进式扫描键，避免生产环境使用 KEYS * 阻塞服务。", "SCAN 0 MATCH 'user:*' COUNT 100", "面试常问 KEYS 与 SCAN：SCAN 分批返回，不会长时间阻塞。", ["扫描", "面试"]),
    ("Docker", "查看容器", "docker ps\ndocker ps -a", "分别查看运行中容器和全部容器。", "docker ps --format 'table {{.Names}}\\t{{.Status}}\\t{{.Ports}}'", "容器退出时先看状态和日志，不要立即删除。", ["容器", "查看"]),
    ("Docker", "查看容器日志", "docker logs --tail 200 -f 容器名", "查看最后 200 行并持续追踪日志。", "docker logs --tail 200 -f automation-platform-backend-1", "可使用 --since 30m 限制时间范围。", ["日志", "排查"]),
    ("Docker", "进入容器", "docker exec -it 容器名 sh", "在运行中的容器执行交互式 Shell。", "docker exec -it mysql sh", "精简镜像可能没有 bash，优先尝试 sh。", ["容器", "调试"]),
    ("Docker", "Compose 服务状态", "docker compose ps\ndocker compose logs -f 服务名", "在 Compose 项目目录查看服务和日志。", "docker compose logs --tail 200 -f backend", "docker compose 针对一组服务，docker 针对单个容器。", ["Compose", "日志"]),
    ("Docker", "重新构建服务", "docker compose up -d --build 服务名", "重新构建并后台启动指定服务。", "docker compose up -d --build frontend", "会改变运行状态，执行前确认项目目录、服务名和配置。", ["构建", "高风险"]),
]


def ensure_commands(db: Session) -> None:
    if db.scalar(select(CommandSnippet.id).where(CommandSnippet.is_builtin.is_(True)).limit(1)):
        return
    for category, title, command, description, example, interview, tags in BUILTINS:
        db.add(CommandSnippet(category=category, title=title, command=command, description=description,
            usage_example=example, interview_note=interview, tags=tags, is_builtin=True))
    db.commit()
