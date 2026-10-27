from pathlib import Path
import os,sys,zipfile
root=Path(__file__).resolve().parents[1]
folder=root/'output/platform-audit-20261026';folder.mkdir(parents=True,exist_ok=True)
for name,content in [('audit-package.zip','isolated package'),('audit-effect.zip','<!doctype html><meta charset="UTF-8"><h1>isolated-preview-verified</h1>')]:
    path=folder/name
    if not path.exists():
        with zipfile.ZipFile(path,'w') as archive: archive.writestr('index.html',content)
sys.path.insert(0,str(root/'backend'))
os.environ.update({'DATABASE_URL':'sqlite:///'+str(folder/'audit.db').replace('\\','/'),'ADMIN_USERNAME':'audit-admin','ADMIN_PASSWORD':'isolated-audit-20261026','APP_SECRET_KEY':'isolated-audit-not-production','DEEPSEEK_API_KEY':'','CODEUP_USERNAME':'','CODEUP_PASSWORD':'','JENKINS_ADMIN_PASSWORD':'','JENKINS_URL':'http://127.0.0.1:1','UI_RUNNER_URL':'http://127.0.0.1:1','CIRCLE_RUNNER_URL':'http://127.0.0.1:1','FILE_TRANSFER_DIR':str(folder/'transfers'),'TEST_PACKAGE_DIR':str(folder/'packages'),'TEMP_EFFECTS_DIR':str(folder/'effects'),'PUBLIC_BASE_URL':'http://127.0.0.1:3104'})
import uvicorn
uvicorn.run('app.main:app',host='127.0.0.1',port=8001)
