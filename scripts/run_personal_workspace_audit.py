"""Local-only full-system acceptance environment; no production credentials or services."""
from pathlib import Path
import os,sys
root=Path(__file__).resolve().parents[1]
folder=root/'output/workspace-20261028/audit';folder.mkdir(parents=True,exist_ok=True)
sys.path.insert(0,str(root/'backend'))
os.environ.update({'DATABASE_URL':'sqlite:///'+str(folder/'platform.db').replace('\\','/'),'ADMIN_USERNAME':'audit-admin','ADMIN_PASSWORD':'isolated-audit-20261028','APP_SECRET_KEY':'isolated-personal-workspace-20261028','DEEPSEEK_API_KEY':'','CODEUP_USERNAME':'','CODEUP_PASSWORD':'','JENKINS_ADMIN_PASSWORD':'','JENKINS_URL':'http://127.0.0.1:1','UI_RUNNER_URL':'http://127.0.0.1:1','CIRCLE_RUNNER_URL':'http://127.0.0.1:1','UI_RUNNER_TOKEN':'isolated-practice-runner-only','PRACTICE_RUNNER_URL':'http://127.0.0.1:8093','PERSONAL_WORKSPACE_DATA_DIR':str(folder/'personal'),'FILE_TRANSFER_DIR':str(folder/'transfers'),'TEST_PACKAGE_DIR':str(folder/'packages'),'TEMP_EFFECTS_DIR':str(folder/'effects'),'PUBLIC_BASE_URL':'http://127.0.0.1:3104'})
import uvicorn
uvicorn.run('app.main:app',host='127.0.0.1',port=8001)
