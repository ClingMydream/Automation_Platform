"""Real multi-role browser tests. Only the dedicated automation customer's cart is cleared."""
import base64,json,os,re
from pathlib import Path
from uuid import uuid4
import pytest,requests
from playwright.sync_api import sync_playwright,expect
BASE=os.environ['PRACTICE_API_URL'].rstrip('/')

def session(token):
    claims=json.loads(base64.urlsafe_b64decode(token.split('.')[1]+'=='))
    return {'token':token,'username':claims['username'],'role':claims['role'],'workspace_id':claims['tenant']}

def api(method,path,token,**kwargs):
    r=requests.request(method,BASE+path,headers={'Authorization':'Bearer '+token},timeout=15,**kwargs);r.raise_for_status();return r.json()

def product(stock=3):
    sku='UI-'+uuid4().hex[:10]
    return api('POST','/products',os.environ['PRACTICE_ADMIN_TOKEN'],json={'sku':sku,'name':sku,'price_cents':2900,'stock':stock})

@pytest.fixture(scope='module')
def browser():
    with sync_playwright()as p:
        b=p.chromium.launch(headless=True,executable_path=os.environ.get('CHROMIUM_PATH','/usr/bin/chromium'),args=['--no-sandbox']);yield b;b.close()

@pytest.fixture
def customer(browser):
    token=os.environ['PRACTICE_CUSTOMER_TOKEN']
    for item in api('GET','/commerce/cart',token)['items']:api('DELETE','/commerce/cart/items/'+str(item['id']),token)
    ctx=browser.new_context(viewport={'width':1440,'height':1000},record_video_dir=str(Path.cwd()),record_video_size={'width':1440,'height':1000});ctx.add_init_script('sessionStorage.setItem("cling:practice:session",'+json.dumps(json.dumps(session(token)))+');');page=ctx.new_page();page.goto(os.environ['PRACTICE_UI_URL']);page.get_by_role('heading',name='商品商城',exact=True).wait_for()
    try:yield page
    except Exception:page.screenshot(path='failure-customer.png',full_page=True);raise
    finally:ctx.close()

def role_page(browser,token):
    ctx=browser.new_context(viewport={'width':1440,'height':1000});ctx.add_init_script('sessionStorage.setItem("cling:practice:session",'+json.dumps(json.dumps(session(token)))+');');p=ctx.new_page();p.goto(os.environ['PRACTICE_UI_URL']);p.get_by_role('navigation',name='练习项目导航').wait_for();return ctx,p

def place(page,item):
    search=page.get_by_role('searchbox',name='搜索商城商品',exact=True)
    # Ant Input.Search exposes an ordinary textbox in some supported versions.
    if not search.count():search=page.get_by_role('textbox',name='搜索商城商品',exact=True)
    search.fill(item['sku']);search.press('Enter');card=page.get_by_test_id('product-'+item['sku']);card.get_by_role('button',name='加入购物车',exact=True).click();page.get_by_text('已加入购物车',exact=True).wait_for();page.get_by_role('button',name='购物车',exact=True).click();page.get_by_role('button',name='去结算',exact=True).click();page.get_by_role('checkbox',name='已确认商品和收货信息',exact=True).check();page.get_by_role('button',name='提交订单',exact=True).click();page.get_by_role('heading',name='订单详情',exact=True).wait_for();page.get_by_role('button',name='模拟付款',exact=True).wait_for();return page.url.split('#order/')[1]

def test_shop_order_cancel(customer):
    item=product();identifier=place(customer,item);customer.get_by_role('button',name='取消订单',exact=True).click();customer.get_by_role('dialog').get_by_role('button',name='确认取消订单',exact=True).click();customer.get_by_role('heading',name='已取消',exact=True).wait_for();assert api('GET','/commerce/products/'+str(item['id']),os.environ['PRACTICE_CUSTOMER_TOKEN'])['stock']==3
    customer.reload();customer.get_by_role('heading',name='已取消',exact=True).wait_for();customer.screenshot(path='key-order-cancel.png',full_page=True)

def test_paid_order_fulfilment_and_return(customer,browser):
    item=product();identifier=place(customer,item);customer.get_by_role('button',name='模拟付款',exact=True).click();customer.get_by_role('heading',name='待发货',exact=True).wait_for();warehouse_ctx,warehouse=role_page(browser,os.environ['PRACTICE_WAREHOUSE_TOKEN']);admin_ctx=None
    try:
        warehouse.goto(os.environ['PRACTICE_UI_URL']+'#order/'+identifier);warehouse.get_by_role('button',name='填写发货信息',exact=True).click();warehouse.get_by_role('textbox',name='模拟运单号',exact=True).fill('DEMO'+uuid4().hex[:12]);warehouse.get_by_role('dialog').get_by_role('button',name='确认发货',exact=True).click();warehouse.get_by_role('heading',name='待收货',exact=True).wait_for();customer.reload();customer.get_by_role('button',name='确认收货',exact=True).click();customer.get_by_role('heading',name='已完成',exact=True).wait_for();customer.get_by_role('button',name='申请退款',exact=True).click();customer.get_by_role('textbox',name='退款原因',exact=True).fill('自动化验证收货后退货退款流程');customer.get_by_role('button',name='提交退款申请',exact=True).click();customer.get_by_role('heading',name='退款审核中',exact=True).wait_for();admin_ctx,admin=role_page(browser,os.environ['PRACTICE_ADMIN_TOKEN']);admin.goto(os.environ['PRACTICE_UI_URL']+'#order/'+identifier);admin.get_by_role('button',name='审核通过退款',exact=True).click();admin.get_by_role('textbox',name='审核说明',exact=True).fill('已核对退货与商品数量');admin.get_by_role('checkbox',name='已收到退货，可回补库存',exact=True).check();admin.get_by_role('button',name='提交审核',exact=True).click();admin.get_by_role('heading',name='已退款',exact=True).wait_for();customer.reload();customer.get_by_role('heading',name='已退款',exact=True).wait_for();assert api('GET','/commerce/products/'+str(item['id']),os.environ['PRACTICE_CUSTOMER_TOKEN'])['stock']==3;customer.screenshot(path='key-fulfilment-return.png',full_page=True)
    finally:warehouse_ctx.close();admin_ctx and admin_ctx.close()

def test_admin_product_and_inventory(browser):
    ctx,page=role_page(browser,os.environ['PRACTICE_ADMIN_TOKEN']);sku='UI-ADMIN-'+uuid4().hex[:8]
    try:
        page.get_by_role('button',name='商品管理',exact=True).click();page.get_by_role('button',name='新增商品',exact=True).click();page.get_by_role('textbox',name='SKU',exact=True).fill(sku);page.get_by_role('textbox',name='商品名称',exact=True).fill(sku);page.get_by_role('spinbutton',name='价格（分）',exact=True).fill('3900');page.get_by_role('spinbutton',name='初始库存',exact=True).fill('2');page.get_by_role('button',name='保存商品',exact=True).click();page.get_by_text('商品已创建',exact=True).wait_for();page.get_by_role('button',name='库存管理',exact=True).click();field=page.get_by_label('搜索库存商品',exact=True);field.fill(sku);field.press('Enter');row=page.get_by_role('row').filter(has_text=sku);row.get_by_role('button',name='登记入库',exact=True).click();page.get_by_role('spinbutton',name='入库数量',exact=True).fill('3');page.get_by_role('textbox',name='入库原因',exact=True).fill('自动化补货验收');page.get_by_role('button',name='确认入库',exact=True).click();page.get_by_text('入库成功，已生成库存流水',exact=True).wait_for();assert row.get_by_text('5',exact=True).count()>=1
        with page.expect_download()as download:page.get_by_role('button',name='导出流水 CSV',exact=True).click()
        assert download.value.suggested_filename=='inventory-movements.csv';page.screenshot(path='key-admin-inventory.png',full_page=True)
    except Exception:page.screenshot(path='failure-admin.png',full_page=True);raise
    finally:ctx.close()


def test_stable_ui_hierarchy_and_locators(customer):
    """Exercise the public locator contract, not CSS classes or generated Ant IDs."""
    page=customer;item=product()
    expect(page.get_by_test_id('commerce-app')).to_have_attribute('data-ui-version','1')
    expect(page.get_by_test_id('commerce-page-store')).to_have_attribute('data-ready','true')
    expect(page.get_by_role('main',name='练习项目内容',exact=True)).to_have_count(1)
    search=page.get_by_test_id('commerce-catalog-filters').get_by_label('搜索商城商品',exact=True)
    search.fill(item['sku']);search.press('Enter')
    card=page.get_by_test_id('commerce-page-store').get_by_test_id('product-'+item['sku'])
    for _ in range(2):
        card.get_by_role('button',name='查看商品：'+item['name'],exact=True).click()
        dialog=page.get_by_role('dialog',name='商品详情',exact=True)
        expect(dialog.get_by_test_id('commerce-product-detail-dialog')).to_be_visible()
        dialog.get_by_role('button',name='Close',exact=True).click()
        expect(page.get_by_test_id('commerce-product-detail-dialog')).to_have_count(0)
    card.get_by_role('button',name='加入购物车',exact=True).click()
    page.get_by_text('已加入购物车',exact=True).wait_for()
    page.get_by_test_id('commerce-navigation').get_by_test_id('commerce-nav-cart').click()
    row=page.get_by_test_id('commerce-cart-table').get_by_test_id('cart-row-'+item['sku'])
    row.get_by_role('spinbutton',name='购物车数量：'+item['sku'],exact=True).fill('2')
    row.get_by_role('button',name='更新数量',exact=True).click()
    expect(page.get_by_test_id('commerce-content')).to_have_attribute('aria-busy','false')
    page.reload()
    expect(row.get_by_role('spinbutton',name='购物车数量：'+item['sku'],exact=True)).to_have_value('2')
    for width in [1440,768,390,320]:
        page.set_viewport_size({'width':width,'height':960})
        expect(page.get_by_test_id('commerce-nav-cart')).to_have_count(1)
        expect(row).to_have_count(1)
        duplicates=page.evaluate('''() => {
            const ids=[...document.querySelectorAll('[data-testid]')].map(n=>n.dataset.testid);
            return ids.filter((id,i)=>ids.indexOf(id)!==i);
        }''')
        assert not duplicates,duplicates
        assert page.evaluate('document.documentElement.scrollWidth <= innerWidth + 2')
    page.set_viewport_size({'width':1440,'height':1000})
    page.screenshot(path='key-ui-locator-contract.png',full_page=True)


def test_expired_session_recovery(browser):
    ctx=browser.new_context()
    ctx.add_init_script('sessionStorage.setItem("cling:practice:session",JSON.stringify({token:"invalid-expired-session",username:"lab_admin",role:"admin"}));')
    page=ctx.new_page()
    try:
        page.goto(os.environ['PRACTICE_UI_URL'])
        expect(page.get_by_test_id('commerce-session-expired')).to_be_visible()
        expect(page.get_by_text('重新加载业务',exact=True)).to_have_count(0)
        page.get_by_test_id('commerce-session-relogin').click()
        expect(page.get_by_test_id('commerce-login')).to_be_visible()
        assert page.evaluate('sessionStorage.getItem("cling:practice:session")')is None
    finally:ctx.close()
