from pathlib import Path
import io
import zipfile
from fastapi import Depends, Request, Response
from fastapi.openapi.docs import get_swagger_ui_html
from app.core.auth import AuthContext
from .router import management, guard

@management.get('/project-download')
def project_download(user: AuthContext=Depends(guard)):
    root=Path(__file__).resolve().parents[3]/'practice'
    if not root.is_dir():root=Path(__file__).resolve().parents[4]/'practice'
    if not root.is_dir():
        from fastapi import HTTPException
        raise HTTPException(503,'练习工程未打包，请重新构建后端镜像')
    content=io.BytesIO()
    with zipfile.ZipFile(content,'w',zipfile.ZIP_DEFLATED)as archive:
        for file in root.rglob('*'):
            if file.is_file()and '__pycache__'not in file.parts and file.suffix!='.pyc':archive.write(file,'cling-practice/'+str(file.relative_to(root)))
    return Response(content.getvalue(),media_type='application/zip',headers={'Content-Disposition':'attachment; filename="cling-practice.zip"'})

def mount_docs(app):
    @app.get('/api/practice/openapi.json',include_in_schema=False)
    def specification():
        schema=app.openapi()
        return {**schema,'info':{'title':'Cling 订单库存练习 API','version':'2.0.0','description':'练习 Token 由平台实践实验室登录获取。v1旧订单接口保留；/commerce 为完整商城与履约接口。金额单位为分，付款物流均为本地模拟。'},'paths':{path:item for path,item in schema['paths'].items()if path.startswith('/api/practice/v1/')}}
    @app.get('/api/practice/docs',include_in_schema=False)
    def swagger():return get_swagger_ui_html(openapi_url='/api/practice/openapi.json',title='订单库存练习接口文档')
