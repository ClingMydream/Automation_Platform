"""Convert the user-provided prediction outline to clearly labelled practice questions."""
import hashlib
import json
import re
from pathlib import Path

root = Path(__file__).resolve().parents[1]
text = (root/'output/self-study/prediction-202610.txt').read_text(encoding='utf-8-sig').replace('\r','\n')
source = '2026年10月押题'
rows = []
choices = [
('“两个结合”是把马克思主义基本原理同中国具体实际相结合、同什么相结合？','中华优秀传统文化','国外政治制度','资本主义发展模式','所有传统习俗'),
('“六个必须坚持”体现的根本立场是？','人民至上','自信自立','系统观念','胸怀天下'),
('“六个必须坚持”中强调立足点的是？','自信自立','守正创新','问题导向','系统观念'),
('“六个必须坚持”中强调思想方法的是？','系统观念','人民至上','自信自立','胸怀天下'),
('中国式现代化是什么现代化？','中国共产党领导的社会主义现代化','全盘西化的现代化','少数人富裕的现代化','仅追求物质增长的现代化'),
('下列哪项属于中国式现代化的中国特色？','全体人民共同富裕','少数人率先富裕即完成目标','单纯追求物质富足','依靠对外扩张发展'),
('中国式现代化如何处理物质文明与精神文明的关系？','相协调','相互替代','只重视物质文明','只重视精神文明'),
('新发展理念中引领发展的第一动力是？','创新','协调','开放','共享'),
('新发展理念中属于持续健康发展的内在要求的是？','协调','创新','开放','共享'),
('新发展理念中属于国家繁荣发展的必由之路的是？','开放','协调','绿色','共享'),
('新发展格局以什么为主体？','国内大循环','国际大循环','单一出口循环','封闭的自给自足循环'),
('全面建设社会主义现代化国家的首要任务是？','高质量发展','单纯扩大经济规模','追求最高增长速度','扩大资源消耗'),
('社会主义市场经济体制中，市场在资源配置中起什么作用？','决定性作用','辅助性作用','唯一作用','完全替代政府的作用'),
('社会主义民主政治的本质属性是？','全过程人民民主','只有选举民主','只有程序民主','只有间接民主'),
('全过程人民民主是怎样的民主？','最广泛、最真实、最管用','只体现在选举时','仅体现在管理环节','只强调形式与程序'),
('社会主义核心价值观中国家层面的内容是？','富强、民主、文明、和谐','自由、平等、公正、法治','爱国、敬业、诚信、友善','创新、协调、绿色、开放'),
('社会主义核心价值观中社会层面的内容是？','自由、平等、公正、法治','富强、民主、文明、和谐','爱国、敬业、诚信、友善','人口、资源、环境、生态'),
('社会主义核心价值观中个人层面的内容是？','爱国、敬业、诚信、友善','富强、民主、文明、和谐','自由、平等、公正、法治','开放、绿色、廉洁、包容'),
('生态文明建设中“绿水青山”与“金山银山”的关系是？','绿水青山就是金山银山','两者必然对立','必须牺牲生态换取财富','生态保护与发展完全无关'),
('总体国家安全观以什么为宗旨？','人民安全','政治安全','经济安全','科技安全'),
('总体国家安全观以什么为根本？','政治安全','人民安全','经济安全','文化安全'),
('总体国家安全观以什么为基础？','经济安全','政治安全','人民安全','社会安全'),
('新型国际关系的主要内容是？','相互尊重、公平正义、合作共赢','单边主导、零和竞争','强权支配、阵营对抗','排他合作、以邻为壑'),
('党跳出历史周期率的第二个答案是？','自我革命','对外扩张','停止改革','放弃监督'),
('中国式现代化两步走战略中，到2035年的目标是？','基本实现社会主义现代化','全面建成社会主义现代化强国','实现共产主义','仅实现局部地区现代化'),
('资料强调解决台湾问题应坚持什么原则与共识？','一个中国原则和“九二共识”','两个中国','一中一台','以外部干涉为前提'),
('资料概括的社会保障体系要求包含哪一项？','覆盖全民、统筹城乡、公平统一、安全规范、可持续','只覆盖少数群体','完全依赖个人储蓄','城乡保障相互割裂'),
('全面从严治党是什么的必由之路？','党永葆生机活力、走好新的赶考之路','以形式代替监督','放松党内约束','只重发展不重建设'),
]

def add(kind, prompt, answer, **extra):
    rows.append(dict(id=f'prediction-202610-{len(rows)+1:02d}',source=source,
        sourceFile='习大大26年10月押题(1).doc',number=len(rows)+1,type=kind,
        prompt=prompt,answer=answer,priority=True,
        fingerprint=hashlib.sha256(re.sub(r'\s+','',prompt).encode()).hexdigest()[:16],**extra))

for i,(prompt,*options) in enumerate(choices):
    offset=i%4
    options=options[-offset:]+options[:-offset] if offset else options
    add('choice',prompt+'（ ）','ABCD'[offset],options=[dict(key=k,text=v) for k,v in zip('ABCD',options)],
        note='依据押题资料考点改编的单项选择练习，非原卷真题。')

section=text.split('二、简答题预测',1)[1].split('论述题预测',1)[0]
heads=['简述 “六个必须坚持” 的内涵。','简述中国式现代化五个中国特色。','简述新发展理念及其地位。','简述全过程人民民主内涵。','简述总体国家安全观的内涵。','简述全面从严治党，党的自我革命的重大意义。']
for i,head in enumerate(heads):
    start=section.index(head)+len(head)
    end=section.index(heads[i+1]) if i+1<len(heads) else len(section)
    answer=section[start:end].strip().replace('**','').replace('> ','').replace('新发展“理念“”','新发展理念')
    add('short',head,answer,note='押题资料参考要点；本题按练习卷 7 分自评。')

part=text.split('论述题预测',1)[1]
matches=list(re.finditer(r'预测\s*(\d)：([^\n]+)',part))
assert len(matches)==4
for i,m in enumerate(matches):
    answer=part[m.end():matches[i+1].start() if i+1<len(matches) else len(part)].strip()
    add('material',m[2].replace('（最高概率）','').strip(),answer,
        note='押题论述练习，按 15 分自评。'+('原文件提供答题框架。' if i==0 else '原文件仅提供答题提示，并非完整参考答案；不可仅凭这段提示判断满分。'),
        answerKind='framework' if i==0 else 'hint')

assert len(rows)==38 and all(q['answer'] for q in rows)
path=root/'frontend/src/modules/18-self-study/questionBank.json'
bank=json.loads(path.read_text(encoding='utf-8-sig'))
bank['questions']=[q for q in bank['questions'] if q.get('source')!=source]+rows
path.write_text(json.dumps(bank,ensure_ascii=False,indent=2),encoding='utf-8')
print('Imported 38 prediction exercises: 28 choice, 6 short, 4 discussion. Total',len(bank['questions']))
