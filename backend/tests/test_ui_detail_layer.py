"""Regression for identical posts in the background feed and active detail layer."""
import importlib.util
import os
from pathlib import Path
import pytest

api = pytest.importorskip('playwright.sync_api')
source = Path(__file__).resolve().parents[2] / 'deploy/ui-runner/studio_flows.py'
spec = importlib.util.spec_from_file_location('detail_layer_flows', source)
flows = importlib.util.module_from_spec(spec);spec.loader.exec_module(flows)


def test_active_detail_card_and_comments_win_over_visible_background_copy():
    browser_path = os.environ.get('CHROMIUM_PATH', 'C:/Program Files/Google/Chrome/Application/chrome.exe' if os.name == 'nt' else '/usr/bin/chromium')
    if not Path(browser_path).exists():
        pytest.skip('Requires installed Chromium')
    with api.sync_playwright() as pw:
        browser = pw.chromium.launch(executable_path=browser_path, headless=True, args=['--no-sandbox'])
        page = browser.new_page()
        page.goto('about:blank#/post_detail?postId=real-id')
        page.set_content('''<div class="group rounded-[28px]"><p>自然任务正文</p><button data-testid="background">背景操作</button></div>
          <div class="min-h-screen" style="position:fixed;inset:0;background:white;z-index:200">
            <h2>详情</h2><div class="group rounded-[28px]"><p>自然任务正文</p><button data-testid="foreground" onclick="window.clicked=true">详情操作</button></div>
            <div id="comment-99"><p>来自对方账号的自然回复</p></div>
          </div>''')
        pages = flows.EmotePages(page, 'https://example.com', {})
        pages.post_text = '自然任务正文'
        assert pages.card().get_by_test_id('background').count() == 0
        pages.card().get_by_test_id('foreground').click()
        assert page.evaluate('window.clicked') is True
        pages.assert_saved_comment('来自对方账号的自然回复')
        page.set_content('''<div class="garden-plot">
          <button id="visitor"><svg class="lucide-droplets"></svg>访客</button>
          <button id="actual-water" class="bottom-4 right-4"><svg class="lucide-droplets"></svg></button>
        </div>''')
        picked = []
        pages.go = lambda route: None
        pages.water_button = lambda target, label: picked.append(target.get_attribute('id')) or 'watered'
        pages.watering()
        assert picked == ['actual-water']
        browser.close()
