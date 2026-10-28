from pathlib import Path
import os,sys
root=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(root/'deploy/practice-runner'))
os.environ.update({'UI_RUNNER_TOKEN':'isolated-practice-runner-only','PRACTICE_API_URL':'http://127.0.0.1:8001/api/practice/v1','PRACTICE_UI_URL':'http://127.0.0.1:3104/practice-app','PRACTICE_PROJECT_DIR':str(root/'practice'),'PRACTICE_RUN_DATA_DIR':str(root/'output/workspace-20261028/runner-data'),'CHROMIUM_PATH':'C:/Program Files/Google/Chrome/Application/chrome.exe'})
import uvicorn
uvicorn.run('runner:app',host='127.0.0.1',port=8093)
