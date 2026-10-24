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
    if (!value.ids.includes(id) || (q.type === 'choice' ? !q.options.some(option => option.key === answer) : !['viewed', 'answered'].includes(answer))) return null;
  }
  for (const [id, score] of Object.entries(value.selfScores || {})) {
    const q = byId.get(id);
    if (!value.ids.includes(id) || q.type === 'choice' || !Number.isInteger(score) || score < 0 || score > (q.type === 'short' ? 7 : 15)) return null;
  }
  if (value.attemptId !== undefined && (typeof value.attemptId !== 'string' || value.attemptId.length > 100)) return null;
  for (const field of ['writtenAnswers', 'revealed', 'scoreSources', 'scoreRevisions', 'aiAssessments']) {
    if (value[field] !== undefined && !object(value[field])) return null;
    for (const [id, item] of Object.entries(value[field] || {})) {
      const q = byId.get(id);
      if (!value.ids.includes(id) || q.type === 'choice') return null;
      if (field === 'writtenAnswers' && (typeof item !== 'string' || item.length > 10000)) return null;
      if (field === 'revealed' && typeof item !== 'boolean') return null;
      if (field === 'scoreSources' && !['ai', 'manual'].includes(item)) return null;
      if (field === 'scoreRevisions' && (!Number.isSafeInteger(item) || item < 0)) return null;
      if (field === 'aiAssessments' && (!object(item) || !Number.isInteger(item.score) || item.score < 0
        || item.score > (q.type === 'short' ? 7 : 15) || typeof item.feedback !== 'string'
        || item.feedback.length > 2000 || !Array.isArray(item.strengths) || !Array.isArray(item.missing_points)
        || item.strengths.length > 12 || item.missing_points.length > 12
        || ![...item.strengths, ...item.missing_points].every(x => typeof x === 'string' && x.length <= 500))) return null;
    }
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
