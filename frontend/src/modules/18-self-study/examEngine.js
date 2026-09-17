export const POINTS = { choice: 2, short: 7, material: 15 };
export function gradePaper(questions, responses = {}, selfScores = {}) {
  const rows = questions.map(q => {
    const max = POINTS[q.type], self = selfScores[q.id];
    const pending = q.type !== 'choice' && !(responses[q.id] && Number.isInteger(self) && self >= 0 && self <= max);
    const score = q.type === 'choice' ? (responses[q.id] === q.answer ? max : 0) : pending ? 0 : self;
    return { id: q.id, type: q.type, max, score, pending };
  });
  return { rows, total: rows.reduce((s,r) => s+r.score,0), max: rows.reduce((s,r) => s+r.max,0), pending: rows.filter(r => r.pending).length };
}
export function shuffle(items, random = Math.random) {
  const result = [...items];
  for (let i = result.length - 1; i > 0; i--) {
    const j = Math.floor(random() * (i + 1));
    [result[i], result[j]] = [result[j], result[i]];
  }
  return result;
}

export function createPaper(bank, sources, mode = 'mixed', random = Math.random) {
  const pool = shuffle(bank.filter(q => sources.includes(q.source)), random);
  const seen = new Set();
  const unique = pool.filter(q => {
    if (seen.has(q.fingerprint)) return false;
    seen.add(q.fingerprint); return true;
  });
  const take = (type, count) => {
    const items = unique.filter(q => q.type === type);
    const priority = items.filter(q => q.priority);
    const historical = items.filter(q => !q.priority);
    const selected = priority.slice(0, Math.ceil(count * 0.7));
    const rest = [...historical, ...priority.slice(selected.length)];
    return shuffle([...selected, ...rest.slice(0, count - selected.length)], random);
  };
  return mode === 'choice' ? take('choice', 25) : mode === 'written'
    ? [...take('short', 5), ...take('material', 1)]
    : [...take('choice', 25), ...take('short', 5), ...take('material', 1)];
}
