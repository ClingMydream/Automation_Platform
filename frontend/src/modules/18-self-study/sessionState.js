const object = value => value && typeof value === 'object' && !Array.isArray(value);
export function validateSession(value, bank) {
  const byId = new Map(bank.questions.map(q => [q.id, q]));
  if (!object(value) || value.version !== bank.version || !Array.isArray(value.ids) || !value.ids.length
      || new Set(value.ids).size !== value.ids.length || !value.ids.every(id => byId.has(id))
      || !Number.isInteger(value.index) || value.index < 0 || value.index >= value.ids.length
      || !object(value.responses) || (value.selfScores !== undefined && !object(value.selfScores))) return null;
  if (value.finished !== undefined && typeof value.finished !== 'boolean') return null;
  if (value.reviewing !== undefined && typeof value.reviewing !== 'boolean') return null;
  for (const [id, answer] of Object.entries(value.responses)) {
    const q = byId.get(id);
    if (!value.ids.includes(id) || (q.type === 'choice' ? !q.options.some(option => option.key === answer) : answer !== 'viewed')) return null;
  }
  for (const [id, score] of Object.entries(value.selfScores || {})) {
    const q = byId.get(id);
    if (!value.ids.includes(id) || q.type === 'choice' || !Number.isInteger(score) || score < 0 || score > (q.type === 'short' ? 7 : 15)) return null;
  }
  if (value.gradeSnapshot !== undefined) {
    const grade = value.gradeSnapshot;
    if (!object(grade) || !Number.isInteger(grade.total) || !Number.isInteger(grade.max)
        || grade.total < 0 || grade.total > grade.max || !Array.isArray(grade.rows)
        || grade.rows.length !== value.ids.length || !Number.isInteger(grade.pending)
        || grade.rows.some((row, index) => !object(row) || row.id !== value.ids[index]
          || !Number.isInteger(row.score) || !Number.isInteger(row.max) || row.score < 0 || row.score > row.max)) return null;
  }
  return value;
}
export function mayEditSession(session) { return !session?.finished && !session?.reviewing; }
