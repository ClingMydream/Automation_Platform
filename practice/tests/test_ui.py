"""Actual browser workflow against the practice frontend; one final screenshot and video."""
import os,re
from pathlib import Path
from uuid import uuid4
import requests
from playwright.sync_api import sync_playwright

def test_shop_order_cancel():
    base=os.environ['PRACTICE_API_URL'].rstrip('/')
    token=os.environ['PRACTICE_ADMIN_TOKEN']
    name='UI-'+uuid4().hex[:10]
    response=requests.post(base+'/products',headers={'Authorization':'Bearer '+token},json={'sku':name,'name':name,'price_cents':2900,'stock':3},timeout=10)
    assert response.status_code==201
    with sync_playwright()as p:
        browser=p.chromium.launch(headless=True,executable_path=os.environ.get('CHROMIUM_PATH','/usr/bin/chromium'),args=['--no-sandbox'])
        context=browser.new_context(viewport={'width':1280,'height':900},record_video_dir=str(Path.cwd()),record_video_size={'width':1280,'height':900})
        context.add_init_script('sessionStorage.setItem("cling:practice:session",'+__import__('json').dumps(__import__('json').dumps({'token':os.environ['PRACTICE_CUSTOMER_TOKEN'],'username':'learner','role':'customer'}))+');')
        page=context.new_page()
        try:
            page.goto(os.environ['PRACTICE_UI_URL'],wait_until='domcontentloaded')
            page.get_by_role('tab',name='商品',exact=True).click()
            row=page.get_by_role('row').filter(has_text=name)
            row.get_by_role('button',name=re.compile(r'下\s*单')).click()
            page.get_by_role('dialog').get_by_role('button',name='确认下单',exact=True).click()
            page.get_by_text('下单成功',exact=True).wait_for()
            page.get_by_role('tab',name='订单',exact=True).click()
            order=page.get_by_role('row').filter(has_text=name)
            order.get_by_role('button',name='取消订单',exact=True).click()
            order.get_by_text('已取消',exact=True).wait_for()
            page.get_by_role('tab',name='商品',exact=True).click()
            row=page.get_by_role('row').filter(has_text=name)
            assert row.get_by_text('3',exact=True).count()>0
            page.screenshot(path='key-screenshot.png',full_page=True)
        except Exception:
            page.screenshot(path='failure.png',full_page=True);raise
        finally:
            context.close();browser.close()
