"""Run after importing/revising the frontend bank; grading must use the same references."""
import json
from pathlib import Path

root=Path(__file__).resolve().parents[1]
source=root/'frontend/src/modules/18-self-study/questionBank.json'
target=root/'backend/app/modules/self_study/questionBank.json'
bank=json.loads(source.read_text(encoding='utf-8-sig'))
assert isinstance(bank.get('version'),int) and bank.get('questions'), 'invalid question bank'
assert len({q['id'] for q in bank['questions']})==len(bank['questions']), 'duplicate question IDs'
target.write_text(json.dumps(bank,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(f'Synchronized {len(bank["questions"])} questions to server grading bank.')
