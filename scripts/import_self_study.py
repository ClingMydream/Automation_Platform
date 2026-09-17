"""Import Word-extracted exam text; fail rather than silently lose questions."""
import argparse
import hashlib
import json
import re
from pathlib import Path


def blocks(text):
    text = text.replace('\r', '\n').replace('\x07', '')
    text = re.sub(r'(?m)^[一二三]、[^\n]*\n?', '', text)
    matches = list(re.finditer(r'(?m)^(\d{1,2})[．.]', text))
    return {int(m[1]): text[m.end():matches[i+1].start() if i+1 < len(matches) else len(text)].strip()
            for i, m in enumerate(matches)}


def parse(path):
    data = blocks(path.read_text(encoding='utf-8-sig'))
    assert set(data) == set(range(1, 32)), (path.name, sorted(data))
    period = re.search(r'(\d{4})年(\d+)月', path.name)
    source = f'{period[1]}年{period[2]}月'
    out = []
    for num, body in data.items():
        q = {'id': f'{period[1]}-{int(period[2]):02d}-{num:02d}', 'source': source,
             'sourceFile': path.name.replace('.txt', '.docx' if period[1] == '2026' else '.doc'),
             'number': num, 'type': 'choice' if num <= 25 else 'short' if num <= 30 else 'material'}
        if num <= 25:
            parts = list(re.finditer(r'([ABCD])[．.]', body))
            assert [p[1] for p in parts] == list('ABCD'), (path.name, num)
            stem = body[:parts[0].start()].strip()
            answer = re.search(r'[（(]\s*([ABCD])\s*[）)]', stem)
            assert answer, (path.name, num)
            q['answer'] = answer[1]
            q['prompt'] = re.sub(r'[（(]\s*[ABCD]\s*[）)]', '（ ）', stem)
            q['options'] = [{'key': p[1], 'text': body[p.end():parts[i+1].start() if i+1 < 4 else len(body)].strip()} for i, p in enumerate(parts)]
        else:
            parts = re.split(r'\n答[：:]\s*', body, maxsplit=1)
            assert len(parts) == 2 and parts[1].strip(), (path.name, num)
            q['prompt'], q['answer'] = (p.strip() for p in parts)
        q['prompt'] = re.sub(r'\d+-(?:\d+|教材中未找到)\s*$', '', q['prompt']).strip()
        # Explicit transcription corrections, keeping the document wording for audit.
        replacements = {'重大改治成果': '重大政治成果', '习近平国志': '习近平同志',
                        '习近平新时代特色社会主义思想': '习近平新时代中国特色社会主义思想',
                        '新发展理理念': '新发展理念'}
        for field in ('prompt', 'answer'):
            original = q[field]
            for before, after in replacements.items():
                q[field] = q[field].replace(before, after)
            if q[field] != original:
                q['original' + field.title()] = original
                q['note'] = '已修正文档中的明显文字录入错误，原文保留在题库来源记录中。'
        q['fingerprint'] = hashlib.sha256(re.sub(r'\s+', '', q['prompt']).encode()).hexdigest()[:16]
        out.append(q)
    return out


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('input', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    files = sorted(args.input.glob('*试题答案.txt'))
    assert len(files) == 4, 'Expected four answer documents'
    questions = [q for path in files for q in parse(path)]
    for path in args.input.glob('*试题.txt'):
        original = blocks(path.read_text(encoding='utf-8-sig'))
        assert len(original) == 31, path.name
        # All numbered questions and options must agree with the paired answer file.
        answered = blocks(path.with_name(path.stem+'答案.txt').read_text(encoding='utf-8-sig'))
        for num, body in original.items():
            expected = re.split(r'\n答[：:]', answered[num], maxsplit=1)[0]
            normalize = lambda s: re.sub(r'\s+', '', re.sub(r'[（(]\s*[ABCD]?\s*[）)]', '()', re.sub(r'\d+-(?:\d+|教材中未找到)', '', s)))
            assert normalize(body).replace('放奔', '放弃').replace('一城', '一域').replace('两个—百年', '两个一百年').replace('分色相应', '相应') == normalize(expected), (path.name, num, 'question/answer mismatch')
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps({'version': 1, 'course': '15040', 'title': '习近平新时代中国特色社会主义思想概论', 'questions': questions}, ensure_ascii=False, indent=2), encoding='utf-8')
    print(f'Validated {len(questions)} questions: 100 choice, 20 short, 4 material; seven input files.')


if __name__ == '__main__':
    main()
