"""Execute repository-owned offline learning examples in isolated temp folders."""
import json,re,subprocess,sys,tempfile
from pathlib import Path

root=Path(__file__).resolve().parents[1]/'frontend/src/modules/21-personal-space'
catalog=json.loads((root/'pythonCourseCatalog.json').read_text(encoding='utf-8'))
assert len(catalog)==124 and len({u['id']for u in catalog})==124
checked=0
for meta in catalog:
    path=(root/'python-units'/f"{meta['id']}.json").resolve()
    assert path.is_relative_to((root/'python-units').resolve())
    unit=json.loads(path.read_text(encoding='utf-8'))
    examples=re.findall(r'```python\n(.*?)```',unit['body'],re.S)
    assert examples,meta['id']
    for code in examples:
        with tempfile.TemporaryDirectory(prefix='cling-python-unit-')as directory:
            result=subprocess.run([sys.executable,'-I','-c',code],cwd=directory,capture_output=True,timeout=10)
        assert result.returncode==0,(meta['id'],result.stderr)
        checked+=1
print(json.dumps({'units':len(catalog),'offline_python_examples_passed':checked,'external_services_tested':False}))
