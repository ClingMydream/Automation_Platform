#!/usr/bin/env python3
"""将钉钉全员圈主帖写入《需求&BUG记录》的“全员圈统计”。

Python 3.10+；安装：python -m pip install playwright
运行：python dingtalk_circle_sync.py
只采集：python dingtalk_circle_sync.py --start 2026-09-01 --end 2026-09-07 --row 209 --dry-run
"""
from __future__ import annotations

import argparse
import base64
import csv
import hashlib
import html
import io
import json
import re
import sys
import time
import uuid
from datetime import date, datetime, timedelta, timezone
from html.parser import HTMLParser
from pathlib import Path

CIRCLE_URL = "https://community-n.dingtalk.com/dingding/ding-community-app/circle/index.html#/community/detail?orgId=461469376&tagId=-1&client=web"
SHEET_URL = "https://alidocs.dingtalk.com/spreadsheetv2/me50Xomxs9MEkGoE/edit?dentryKey=me50Xomxs9MEkGoE&docKey=Q35O851ADQYRzl9V&type=s&dontjump=true"
SHEET_NAME = "全员圈统计"
SHANGHAI = timezone(timedelta(hours=8))
ROOT = Path(__file__).resolve().parent

# 2026-09-08 在用户指定的页面检查过的 DOM；仅提取主帖，不包含评论区。
EXTRACT_POSTS_JS = r"""cards => cards.map(card => {
  const text = selector => {
    const node = card.querySelector(selector);
    return node ? node.innerText.trim() : '';
  };
  return {
    author: text('.dm-common-header .dm-title-text'),
    raw_time: text('.swift-ui-feed-time'),
    title: text('.dm-feed-text-area-title .dm-complext-text'),
    body: text('.swift-ui-text-area-main .dm-complext-text'),
    images: card.querySelectorAll('.dm-feed-photo-area .dm-photo-wall-item').length,
    image_urls: [...card.querySelectorAll('.dm-feed-photo-area .dm-photo-wall-item')]
      .map(item => {
        const img = item.querySelector('img');
        if (img) return img.currentSrc || img.src;
        const styled = item.querySelector('[style*="background-image"]') || item;
        const match = getComputedStyle(styled).backgroundImage.match(/url\(["']?(.*?)["']?\)/);
        return match ? match[1] : '';
      }).filter(Boolean),
    attachments: text('.dm-feed-card-attachments-area')
  };
})"""


class SyncError(RuntimeError):
    pass


def clean(text: str) -> str:
    return text.replace("\r\n", "\n").replace("\r", "\n").replace("\ufeff", "").strip()


def parse_post_time(text: str, now: datetime) -> datetime:
    """无年份日期按页面的当前日期推断，绝不按用户输入的统计年份硬套。"""
    value = clean(text)
    value = re.sub(r"\s+", " ", value)
    for word, offset in (("今天", 0), ("昨天", 1), ("前天", 2)):
        if value.startswith(word):
            suffix = value[len(word):].strip()
            clock = datetime.strptime(suffix or "00:00", "%H:%M").time()
            return datetime.combine(now.date() - timedelta(days=offset), clock, SHANGHAI)
    if value == "刚刚":
        return now
    match = re.fullmatch(r"(\d+)\s*(分钟|小时|天)前", value)
    if match:
        number, unit = match.groups()
        return now - timedelta(**{dict(分钟="minutes", 小时="hours", 天="days")[unit]: int(number)})
    if re.fullmatch(r"\d{1,2}:\d{2}", value):
        return datetime.combine(now.date(), datetime.strptime(value, "%H:%M").time(), SHANGHAI)
    value = value.replace("年", "-").replace("月", "-").replace("日", "").replace("/", "-")
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d"):
        try:
            return datetime.strptime(value, fmt).replace(tzinfo=SHANGHAI)
        except ValueError:
            pass
    # 钉钉本年度帖子显示 MM-DD；在跨年时选择不晚于今天的最近一次该日期。
    if re.fullmatch(r"\d{1,2}-\d{1,2}(?: \d{1,2}:\d{2})?", value):
        fmt = "%Y-%m-%d %H:%M" if " " in value else "%Y-%m-%d"
        for year in range(now.year, now.year - 5, -1):
            try:
                parsed = datetime.strptime(f"{year}-{value}", fmt).replace(tzinfo=SHANGHAI)
            except ValueError:
                continue
            if parsed.date() <= now.date():
                return parsed
    raise SyncError(f"无法可靠识别帖子时间 {text!r}，停止写入。")


def prepare_posts(raw: list[dict], start: date, end: date, now: datetime) -> list[dict]:
    posts = []
    for index, item in enumerate(raw):
        if not item.get("author") or not item.get("raw_time"):
            raise SyncError(f"第 {index + 1} 个帖子缺少作者或日期，页面结构可能已变化。")
        timestamp = parse_post_time(item["raw_time"], now)
        if not start <= timestamp.date() <= end:
            continue
        title, body = clean(item.get("title", "")), clean(item.get("body", ""))
        description = "\n".join(part for part in (title, body if body != title else "") if part)
        if not description:
            description = "[此帖无文字正文，请到全员圈查看图片或附件]"
        posts.append({
            "description": description,
            "author": clean(item["author"]),
            "date": timestamp.strftime("%Y/%m/%d"),
            "raw_time": item["raw_time"],
            "timestamp": timestamp.isoformat(),
            "source_index": index,
            "images": item.get("images", 0),
            "image_urls": list(dict.fromkeys(item.get("image_urls", []))),
        })
    # 同一天没有具体时分的帖子保留页面顺序，不虚构时间。
    posts.sort(key=lambda p: (p["timestamp"], p["source_index"]))
    return posts


def download_post_images(context, posts: list[dict], folder: Path):
    """Download every selected post image and build one PNG contact sheet per row."""
    from PIL import Image, ImageOps
    image_dir = folder / "images"
    image_dir.mkdir(parents=True, exist_ok=True)
    for index, post in enumerate(posts, 1):
        urls = post.pop("image_urls", [])
        expected = int(post.get("images", 0))
        if expected and len(urls) != expected:
            raise SyncError(f"第 {index} 条显示 {expected} 张图片，但只读取到 {len(urls)} 个图片地址，停止生成计划。")
        opened = []
        for image_index, url in enumerate(urls, 1):
            if not url.startswith(("https://", "http://")):
                raise SyncError(f"第 {index} 条第 {image_index} 张图片不是可下载地址，停止生成计划。")
            response = context.request.get(url, headers={"Referer": CIRCLE_URL}, timeout=30000)
            if not response.ok:
                raise SyncError(f"第 {index} 条第 {image_index} 张图片下载失败（HTTP {response.status}）。")
            payload = response.body()
            if len(payload) > 15 * 1024 * 1024:
                raise SyncError(f"第 {index} 条第 {image_index} 张图片超过 15MB，未写入。")
            try:
                opened.append(ImageOps.exif_transpose(Image.open(io.BytesIO(payload))).convert("RGB"))
            except Exception as exc:
                raise SyncError(f"第 {index} 条第 {image_index} 张图片格式无法识别。") from exc
        if not opened:
            post["image_file"] = None
            continue
        thumb_width = 420
        thumbs = []
        for image in opened:
            image.thumbnail((thumb_width, 420), Image.Resampling.LANCZOS)
            thumbs.append(image)
        gap = 12
        width = max(image.width for image in thumbs) + gap * 2
        height = sum(image.height for image in thumbs) + gap * (len(thumbs) + 1)
        sheet = Image.new("RGB", (width, height), "white")
        y = gap
        for image in thumbs:
            sheet.paste(image, ((width - image.width) // 2, y)); y += image.height + gap
        path = image_dir / f"post-{index:03d}.png"
        sheet.save(path, "PNG", optimize=True)
        post["image_file"] = str(path.relative_to(folder)).replace("\\", "/")
        post["image_sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()


def make_cells(posts: list[dict], row: int) -> dict[str, str]:
    if row < 2:
        raise SyncError("起始行必须至少为 2，不能写入表头。")
    cells = {}
    for offset, post in enumerate(posts):
        target_row = row + offset
        if post.get("target_row", target_row) != target_row:
            raise SyncError(f"第 {offset + 1} 条记录目标行错位，停止写入。")
        for col, key in (("E", "description"), ("H", "author"), ("I", "date")):
            value = post[key]
            if not isinstance(value, str) or not value.strip():
                raise SyncError(f"第 {offset + 1} 条记录的 {key} 为空或不是文字。")
            if len(value) > 32000:
                raise SyncError("单条内容超过 32000 字符，请人工处理，脚本不会截断正文。")
            # 不将用户原文当成可执行公式，发现风险内容先停止，交由人工按纯文本填写。
            if value.lstrip().startswith(("=", "+", "-", "@")):
                raise SyncError(f"{col}{row + offset} 内容以公式符号开头，请人工按纯文本填写该条。")
            cells[f"{col}{target_row}"] = value
    return cells


def same_value(actual: str, expected: str, address: str) -> bool:
    actual, expected = clean(actual), clean(expected)
    if actual == expected:
        return True
    if address.startswith("I"):
        try:
            return datetime.strptime(actual.replace("-", "/"), "%Y/%m/%d").date() == datetime.strptime(expected, "%Y/%m/%d").date()
        except ValueError:
            pass
    return False


def normalized_date(value: str) -> str:
    text = clean(value).replace("-", "/")
    try:
        return datetime.strptime(text, "%Y/%m/%d").date().isoformat()
    except ValueError:
        return text


class ClipboardTable(HTMLParser):
    def __init__(self):
        super().__init__()
        self.merged = False
        self.rows: list[list[str]] = []
        self.in_cell = False

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag in ("td", "th"):
            self.merged |= attrs.get("rowspan", "1") != "1" or attrs.get("colspan", "1") != "1"
            if not self.rows:
                self.rows.append([])
            self.rows[-1].append("")
            self.in_cell = True
        elif tag == "tr":
            self.rows.append([])
        elif tag == "br" and self.in_cell:
            self.rows[-1][-1] += "\n"

    def handle_endtag(self, tag):
        if tag in ("td", "th"):
            self.in_cell = False

    def handle_data(self, data):
        if self.in_cell:
            self.rows[-1][-1] += data


def decode_clipboard(text: str, markup: str, count: int) -> list[str]:
    table = ClipboardTable()
    table.feed(markup)
    if table.merged:
        raise SyncError("目标选区包含合并单元格，请改用未合并的空白行。")
    html_rows = [r for r in table.rows if r]
    rows = [r or [""] for r in csv.reader(io.StringIO(text), delimiter="\t")]
    if not text:
        # 空选区必须有 HTML 表格维度佐证，不能把复制失败当成空白。
        rows = html_rows
    elif (len(rows) != count or any(len(r) != 1 for r in rows)) \
            and len(html_rows) == count and all(len(r) == 1 for r in html_rows):
        # 钉钉的 text/plain 会省略连续空白选区的最后一行；HTML 表格
        # 保留了完整维度，使用它交叉验证，不能仅凭换行数判断选区。
        rows = html_rows
    if len(rows) != count or any(len(r) != 1 for r in rows):
        raise SyncError(f"复制结果不是预期的 {count} 行 × 1 列，停止操作（实际 {len(rows)} 行）。")
    return [r[0] for r in rows]


def save_json(path: Path, data: dict):
    temp = path.with_suffix(".tmp")
    temp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    temp.replace(path)


def collect_posts(page, max_scrolls: int = 300) -> list[dict]:
    page.locator(".dm-feed").first.wait_for(state="attached", timeout=60000)
    all_tab = page.get_by_text("全部", exact=True)
    if all_tab.count() == 1:
        all_tab.click()
    page.wait_for_timeout(1000)
    # 以页面的动态总数校验完整性；不能仅凭滚动停住就认定抓取完成。
    matches = re.findall(r"动态\s*(\d+)", page.locator("body").inner_text())
    if not matches or len(set(matches)) != 1:
        raise SyncError("无法读取唯一的动态总数，不能保证统计完整，停止写入。")
    expected = int(matches[0])
    if not expected:
        return []
    previous = []
    stagnant = 0
    for turn in range(max_scrolls):
        extracted = page.locator(".dm-feed").evaluate_all(EXTRACT_POSTS_JS)
        # 钉钉偶尔会同时保留同一帖的新旧渲染节点；按主帖内容去重，
        # 但不把不同作者或不同时间的相同文案误合并。
        current = []
        seen = set()
        for item in extracted:
            identity = (
                clean(item.get("author", "")), clean(item.get("raw_time", "")),
                clean(item.get("title", "")), clean(item.get("body", "")),
                clean(item.get("attachments", "")), item.get("images", 0),
            )
            if identity not in seen:
                seen.add(identity)
                current.append(item)
        if len(current) < len(previous):
            raise SyncError("页面移除了已加载帖子，当前版本不支持该虚拟列表结构，停止写入。")
        # 页面使用追加列表；若中途有新帖插入/旧帖修改，应重新采集，避免错位。
        if previous and current[:len(previous)] != previous:
            raise SyncError("采集过程中帖子内容或顺序发生变化，请重新运行。")
        stagnant = stagnant + 1 if len(current) == len(previous) else 0
        if len(current) == expected:
            print(f"已读取全部 {expected} 条主帖。", flush=True)
            return current
        if len(current) > expected and stagnant >= 2:
            # 页面“动态”数字可能不包含置顶帖。仅在连续滚动后数量和内容
            # 都保持稳定时接受实际主帖数，后续仍由日期区间筛选和预览确认。
            print(f"页面标示 {expected} 条，稳定读取到 {len(current)} 条主帖（可能含置顶帖）。", flush=True)
            return current
        if stagnant >= 10:
            raise SyncError(f"只加载到 {len(current)}/{expected} 条，可能网络异常；未写入不完整结果。")
        previous = current
        last = page.locator(".dm-feed").last
        last.scroll_into_view_if_needed()
        last.hover()
        page.mouse.wheel(0, 3500)
        page.wait_for_timeout(1800)
        if turn % 4 == 0:
            print(f"正在加载：{len(current)}/{expected} 条……", flush=True)
    raise SyncError("达到最大滚动次数，未确认加载完整；停止写入。")


class DingSheet:
    def __init__(self, page, context):
        self.page = page
        context.grant_permissions(["clipboard-read", "clipboard-write"], origin="https://alidocs.dingtalk.com")

    def select_sheet(self):
        tab = self.page.get_by_role("button", name=SHEET_NAME, exact=True)
        tab.wait_for(state="visible", timeout=60000)
        tab.click()
        self.page.get_by_test_id("SelectionDisplayContainer").wait_for(state="visible")

    def select(self, address: str):
        if not re.fullmatch(r"[DEHI][1-9]\d*(?::[DEHI][1-9]\d*)?", address):
            raise SyncError(f"非法目标地址：{address}")
        self.page.keyboard.press("Escape")
        self.page.get_by_test_id("SelectionDisplayContainer").click()
        box = self.page.get_by_test_id("SelectionEditContainer")
        box.fill(address)
        box.press("Enter")
        self.page.wait_for_timeout(180)
        current = self.page.get_by_test_id("SelectionDisplayContainer").inner_text().replace("$", "").replace(" ", "")
        # 新版钉钉表格选中连续区域后，地址框有时只显示左上角锚点；
        # 后续复制结果仍会严格验证行数，因此接受该显示方式不会放宽写入范围校验。
        anchor = address.split(":", 1)[0]
        if current not in {address, anchor} and not (":" not in address and current == f"{address}:{address}"):
            raise SyncError(f"目标选区不符：要求 {address}，实际 {current}。可能是合并单元格或行数不足。")

    def read_column(self, col: str, row: int, count: int) -> list[str]:
        address = f"{col}{row}" if count == 1 else f"{col}{row}:{col}{row + count - 1}"
        self.select(address)
        sentinel = f"SYNC_COPY_{uuid.uuid4()}"
        self.page.evaluate("s => navigator.clipboard.writeText(s)", sentinel)
        self.page.keyboard.press("Control+c")
        deadline = time.monotonic() + 5
        while time.monotonic() < deadline:
            data = self.page.evaluate("""async () => {
                let result = {text: '', html: ''};
                for (const item of await navigator.clipboard.read()) {
                    if (item.types.includes('text/plain')) result.text = await (await item.getType('text/plain')).text();
                    if (item.types.includes('text/html')) result.html = await (await item.getType('text/html')).text();
                }
                return result;
            }""")
            if data["text"] != sentinel:
                return decode_clipboard(data["text"], data["html"], count)
            self.page.wait_for_timeout(120)
        raise SyncError(f"复制 {address} 超时，无法验证内容。")

    def cell_has_image(self, address: str) -> bool:
        self.select(address)
        sentinel = f"SYNC_IMAGE_{uuid.uuid4()}"
        self.page.evaluate("s => navigator.clipboard.writeText(s)", sentinel)
        self.page.keyboard.press("Control+c")
        self.page.wait_for_timeout(350)
        data = self.page.evaluate("""async () => {
            const result = {text: '', html: '', types: []};
            for (const item of await navigator.clipboard.read()) {
                result.types.push(...item.types);
                if (item.types.includes('text/plain')) result.text = await (await item.getType('text/plain')).text();
                if (item.types.includes('text/html')) result.html = await (await item.getType('text/html')).text();
            }
            return result;
        }""")
        if data["text"] == sentinel:
            raise SyncError(f"复制 {address} 超时，无法检查图片列。")
        return any(t.startswith("image/") for t in data["types"]) or "<img" in data["html"].lower() or bool(clean(data["text"]))

    def read_cells(self, row: int, count: int) -> dict[str, str]:
        result = {}
        for col in ("E", "H", "I"):
            for i, text in enumerate(self.read_column(col, row, count)):
                result[f"{col}{row + i}"] = text
        return result

    def check_headers(self):
        actual = self.read_cells(1, 1)
        for address, title in {"E1": "描述", "H1": "提出人", "I1": "提出时间"}.items():
            if re.sub(r"\s+", "", actual[address]) != title:
                raise SyncError(f"表头变化：{address} 应为“{title}”，实际为 {actual[address]!r}。")
        if clean(self.read_column("D", 1, 1)[0]) != "图片":
            raise SyncError("表头变化：D1 应为“图片”。")

    def write_cell(self, address: str, value: str):
        self.select(address)
        # HTML 单格表格保留正文换行；TSV 为兼容性回退。只粘贴一个单元格。
        stream = io.StringIO(newline="")
        csv.writer(stream, delimiter="\t", lineterminator="\r\n").writerow([value])
        markup = '<html><body><table><tr><td style="white-space:pre-wrap">' + html.escape(value).replace("\n", "<br>") + '</td></tr></table></body></html>'
        self.page.evaluate("""async data => navigator.clipboard.write([new ClipboardItem({
            'text/plain': new Blob([data.text], {type: 'text/plain'}),
            'text/html': new Blob([data.html], {type: 'text/html'})
        })])""", {"text": stream.getvalue(), "html": markup})
        self.page.keyboard.press("Control+v")
        self.page.wait_for_timeout(400)
        # 不自动处理扩区、覆盖或权限弹窗；读回失败时立即停止。
        readback = self.read_column(address[0], int(address[1:]), 1)[0]
        if not same_value(readback, value, address):
            raise SyncError(f"{address} 粘贴后核对不一致。已停止，请检查该单元格；不会自动重复粘贴。")

    def write_image(self, address: str, path: Path):
        if self.cell_has_image(address):
            return
        encoded = base64.b64encode(path.read_bytes()).decode("ascii")
        self.select(address)
        self.page.evaluate("""async encoded => {
            const raw = atob(encoded); const bytes = new Uint8Array(raw.length);
            for (let i = 0; i < raw.length; i++) bytes[i] = raw.charCodeAt(i);
            await navigator.clipboard.write([new ClipboardItem({'image/png': new Blob([bytes], {type:'image/png'})})]);
        }""", encoded)
        self.page.keyboard.press("Control+v")
        self.page.wait_for_timeout(1200)
        for label in ("嵌入单元格", "插入单元格", "放入单元格"):
            button = self.page.get_by_text(label, exact=True)
            if button.count() and button.first.is_visible():
                button.first.click(); self.page.wait_for_timeout(800); break
        if not self.cell_has_image(address):
            raise SyncError(f"{address} 图片粘贴后未能回读确认，已停止。")

    def wait_saved(self):
        self.page.get_by_text("已保存", exact=True).first.wait_for(state="visible", timeout=30000)
        self.page.wait_for_timeout(1000)


def write_plan(sheet: DingSheet, plan: dict, path: Path):
    cells = make_cells(plan["posts"], plan["row"])
    count = len(plan["posts"])
    sheet.select_sheet()
    sheet.check_headers()
    actual = sheet.read_cells(plan["row"], count)
    conflicts = [a for a, value in actual.items() if clean(value) and not same_value(value, cells[a], a)]
    if conflicts:
        by_value = {}
        for offset in range(count):
            target_row = plan["row"] + offset
            key = (clean(actual[f"E{target_row}"]), clean(actual[f"H{target_row}"]), normalized_date(actual[f"I{target_row}"]))
            by_value.setdefault(key, []).append(target_row)
        for post in plan["posts"]:
            key = (clean(post["description"]), clean(post["author"]), normalized_date(post["date"]))
            matches = by_value.get(key, [])
            if len(matches) != 1:
                raise SyncError("现有表格无法按描述、提出人和日期唯一匹配，未补写图片。")
            post["target_row"] = matches[0]
        if len({post["target_row"] for post in plan["posts"]}) != count:
            raise SyncError("现有表格存在重复映射，未补写图片。")
        plan["posts"].sort(key=lambda post: post["target_row"])
        plan["reconciled_existing_order"] = True
        save_json(path, plan)
        cells = make_cells(plan["posts"], plan["row"])
        conflicts = [a for a, value in actual.items() if not same_value(value, cells[a], a)]
        if conflicts:
            raise SyncError("重新排列后仍与现有表格不一致，未补写图片。")
    if plan.get("version") == 2:
        image_files = set()
        for offset, post in enumerate(plan["posts"]):
            target_row = plan["row"] + offset
            identity = "\n".join((post["author"], post["timestamp"], post["description"]))
            expected_id = hashlib.sha256(identity.encode("utf-8")).hexdigest()[:16]
            if post.get("target_row") != target_row or post.get("record_id") != expected_id:
                raise SyncError(f"第 {offset + 1} 条记录映射校验失败，停止写入。")
            relative = post.get("image_file")
            if relative:
                image_path = path.parent / relative
                if not re.fullmatch(r"images/post-\d{3}\.png", relative) or relative in image_files \
                        or not image_path.is_file() \
                        or hashlib.sha256(image_path.read_bytes()).hexdigest() != post.get("image_sha256"):
                    raise SyncError(f"第 {offset + 1} 条图片与帖子映射校验失败，停止写入。")
                image_files.add(relative)
    image_conflicts = []
    verified_images = set(plan.get("image_verified", []))
    for offset, post in enumerate(plan["posts"]):
        address = f"D{plan['row'] + offset}"
        if post.get("image_file") and address not in verified_images and sheet.cell_has_image(address):
            image_conflicts.append(address)
    if image_conflicts:
        raise SyncError("目标图片列已有内容，整批未开始写入：" + ", ".join(image_conflicts[:12]))
    plan["status"] = "writing"
    save_json(path, plan)
    # 按帖子逐行写入，D/E/H/I 始终绑定同一个 target_row 和 record_id。
    for offset, post in enumerate(plan["posts"]):
        target_row = plan["row"] + offset
        if post.get("target_row", target_row) != target_row:
            raise SyncError(f"第 {offset + 1} 条记录目标行错位，停止写入。")
        for col, key in (("E", "description"), ("H", "author"), ("I", "date")):
            address, value = f"{col}{target_row}", post[key]
            if not same_value(actual[address], value, address):
                current = sheet.read_column(col, target_row, 1)[0]
                if not same_value(current, value, address):
                    if clean(current):
                        raise SyncError(f"{address} 在写入前发生变化，停止以避免覆盖。")
                    plan["last_attempt"] = {"record_id": post.get("record_id"), "row": target_row, "address": address}
                    save_json(path, plan)
                    sheet.write_cell(address, value)
        relative = post.get("image_file")
        if relative:
            address = f"D{target_row}"
            sheet.write_image(address, path.parent / relative)
            if address not in plan.setdefault("image_verified", []):
                plan["image_verified"].append(address)
        plan["last_verified"] = {"record_id": post.get("record_id"), "row": target_row}
        if target_row not in plan.setdefault("verified_rows", []):
            plan["verified_rows"].append(target_row)
        save_json(path, plan)
        print(f"已核对第 {target_row} 行（{offset + 1}/{count}）", flush=True)
    sheet.wait_saved()
    # 重载后再读取，检查服务端保存结果，不能仅依据本地粘贴成功。
    sheet.page.reload(wait_until="domcontentloaded")
    sheet.select_sheet()
    final = sheet.read_cells(plan["row"], count)
    bad = [a for a, value in cells.items() if not same_value(final[a], value, a)]
    if bad:
        raise SyncError("重新打开后核对失败：" + ", ".join(bad[:12]))
    missing_images = [a for a in plan.get("image_verified", []) if not sheet.cell_has_image(a)]
    if missing_images:
        raise SyncError("重新打开后图片核对失败：" + ", ".join(missing_images[:12]))
    plan["status"] = "completed"
    plan["completed_at"] = datetime.now(SHANGHAI).isoformat()
    save_json(path, plan)


def argument_parser():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--start", help="开始日期 YYYY-MM-DD，包含当天")
    p.add_argument("--end", help="结束日期 YYYY-MM-DD，包含当天")
    p.add_argument("--row", type=int, help="表格起始行，如 209；不是需要统计的条数")
    p.add_argument("--max-rows", type=int, help="可选：最多可使用多少行；超出则停止，不截断")
    p.add_argument("--dry-run", action="store_true", help="只采集和导出待写入文件，不改在线表格")
    p.add_argument("--resume", type=Path, help="从之前保存的 run.json 续写，不重新采集")
    p.add_argument("--channel", choices=["chrome", "msedge", "chromium"], default="chrome")
    p.add_argument("--headless", action="store_true", help="无界面运行；登录页会保存截图供平台扫码")
    p.add_argument("--login-screenshot", type=Path, help="等待登录时反复保存当前页面截图")
    p.add_argument("--profile", type=Path, default=ROOT / "output" / "dingtalk_sync" / "browser-profile")
    p.add_argument("--output", type=Path, default=ROOT / "output" / "dingtalk_sync" / "runs")
    return p


def capture_login_qr(page, screenshot: Path):
    """Save the QR itself at device resolution; fall back to the full login page."""
    screenshot.parent.mkdir(parents=True, exist_ok=True)
    candidates = []
    for selector in ("canvas", "img", "svg"):
        nodes = page.locator(selector)
        for index in range(min(nodes.count(), 40)):
            node = nodes.nth(index)
            try:
                box = node.bounding_box()
                if box and 140 <= box["width"] <= 420 and 140 <= box["height"] <= 420:
                    ratio = box["width"] / box["height"]
                    if .85 <= ratio <= 1.15 and node.is_visible():
                        candidates.append((box["width"] * box["height"], node))
            except Exception:
                pass
    if candidates:
        candidates.sort(key=lambda item: item[0], reverse=True)
        box = candidates[0][1].bounding_box()
        margin = 70
        viewport = page.viewport_size
        clip = {
            "x": max(0, box["x"] - margin),
            "y": max(0, box["y"] - margin),
            "width": min(box["width"] + margin * 2, viewport["width"] - max(0, box["x"] - margin)),
            "height": min(box["height"] + margin * 2, viewport["height"] - max(0, box["y"] - margin)),
        }
        page.screenshot(path=str(screenshot), clip=clip, scale="device")
    else:
        page.screenshot(path=str(screenshot), full_page=False, scale="device")


def wait_login(page, selector: str, label: str, screenshot: Path | None = None):
    deadline = time.time() + 300
    while time.time() < deadline:
        try:
            page.locator(selector).first.wait_for(state="attached", timeout=3000)
            if screenshot:
                screenshot.unlink(missing_ok=True)
            print(f"已进入{label}。", flush=True)
            return
        except Exception:
            if screenshot:
                capture_login_qr(page, screenshot)
            print(f"WAITING_LOGIN:{label}", flush=True)
    raise SyncError(f"等待登录{label}超时，请重新执行。")


def main() -> int:
    args = argument_parser().parse_args()
    plan = None
    run_path = None
    try:
        if args.resume:
            if args.start or args.end or args.row is not None:
                raise SyncError("--resume 不与 --start、--end、--row 同时使用。")
            run_path = args.resume.resolve()
            plan = json.loads(run_path.read_text(encoding="utf-8"))
            if plan.get("version") not in (1, 2) or plan.get("sheet_url") != SHEET_URL or plan.get("sheet") != SHEET_NAME:
                raise SyncError("续写文件不是此脚本生成的当前表格任务。")
            make_cells(plan["posts"], plan["row"])
        else:
            start = date.fromisoformat(args.start or input("统计开始日期（YYYY-MM-DD）：").strip())
            end = date.fromisoformat(args.end or input("统计结束日期（YYYY-MM-DD，包含当天）：").strip())
            row = args.row if args.row is not None else int(input("从表格第几行开始写入（例如 209）：").strip())
            if start > end:
                raise SyncError("开始日期不能晚于结束日期。")
            if end > datetime.now(SHANGHAI).date():
                raise SyncError("结束日期不能晚于今天。")
            make_cells([], row)
        if args.max_rows is not None and args.max_rows < 1:
            raise SyncError("--max-rows 必须为正整数。")
        from playwright.sync_api import sync_playwright
        args.profile.mkdir(parents=True, exist_ok=True)
        with sync_playwright() as pw:
            context = pw.chromium.launch_persistent_context(
                str(args.profile.resolve()),
                channel=None if args.channel == "chromium" else args.channel,
                executable_path="/usr/bin/chromium" if args.channel == "chromium" else None,
                headless=args.headless, viewport={"width": 1440, "height": 960},
                device_scale_factor=2 if args.headless else 1,
                locale="zh-CN", timezone_id="Asia/Shanghai",
            )
            try:
                if plan is None:
                    page = context.new_page()
                    page.goto(CIRCLE_URL, wait_until="domcontentloaded", timeout=60000)
                    wait_login(page, ".dm-feed", "霖感App全员圈", args.login_screenshot)
                    now = datetime.now(SHANGHAI)
                    raw = collect_posts(page)
                    posts = prepare_posts(raw, start, end, now)
                    make_cells(posts, row)
                    folder = args.output / (now.strftime("%Y%m%d_%H%M%S") + "_" + uuid.uuid4().hex[:6])
                    folder.mkdir(parents=True, exist_ok=True)
                    for offset, post in enumerate(posts):
                        post["target_row"] = row + offset
                        identity = "\n".join((post["author"], post["timestamp"], post["description"]))
                        post["record_id"] = hashlib.sha256(identity.encode("utf-8")).hexdigest()[:16]
                    download_post_images(context, posts, folder)
                    run_path = folder / "run.json"
                    plan = {"version": 2, "status": "prepared", "sheet_url": SHEET_URL,
                            "sheet": SHEET_NAME, "circle_url": CIRCLE_URL, "start": str(start),
                            "end": str(end), "row": row, "collected_at": now.isoformat(), "posts": posts}
                    save_json(run_path, plan)
                    with (folder / "待写入.csv").open("w", encoding="utf-8-sig", newline="") as f:
                        writer = csv.writer(f)
                        writer.writerow(["表格行号", "描述", "提出人", "提出时间"])
                        for offset, post in enumerate(posts):
                            writer.writerow([row + offset, post["description"], post["author"], post["date"]])
                count = len(plan["posts"])
                print(f"区间 {plan['start']} 至 {plan['end']}：共 {count} 条。")
                print(f"待写入文件：{run_path}")
                if args.max_rows is not None and count > args.max_rows:
                    raise SyncError(f"共 {count} 条，超过可用的 {args.max_rows} 行；未写入。")
                if not count or args.dry_run:
                    print("未修改在线表格。")
                    return 0
                print(f"写入“{SHEET_NAME}”第 {plan['row']} 至 {plan['row'] + count - 1} 行，仅 E/H/I 列。")
                target = context.new_page()
                target.goto(SHEET_URL, wait_until="domcontentloaded", timeout=60000)
                wait_login(target, '[id="sheet-tab-st-b84fadd4-95465"]', "需求&BUG记录", args.login_screenshot)
                write_plan(DingSheet(target, context), plan, run_path)
                print(f"完成：{count} 条，已重新打开表格核对。")
                return 0
            finally:
                context.close()
    except KeyboardInterrupt:
        print("\n已中断；若开始过写入，请使用保存的 run.json 续写。", file=sys.stderr)
        return 130
    except Exception as exc:
        if plan is not None and run_path is not None:
            plan["error"] = str(exc)
            save_json(run_path, plan)
        print(f"停止：{exc}", file=sys.stderr)
        if run_path:
            print(f'续写命令：python dingtalk_circle_sync.py --resume "{run_path}"', file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
