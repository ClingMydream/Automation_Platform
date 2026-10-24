import { mayEditSession } from './sessionState.js';
import { POINTS } from './examEngine.js';
export const newAttemptId = () => globalThis.crypto?.randomUUID?.() || `${Date.now()}-${Math.random()}`;
export function answerRevealed(session, id) {
  return session?.revealed?.[id] ?? (session?.responses?.[id] === 'viewed' && !session?.hidden?.[id]);
}
export function hasWrittenAnswer(session, id) { return Boolean(session?.writtenAnswers?.[id]?.trim()); }
export function updateWrittenAnswer(session, id, value) {
  if (!mayEditSession(session) || value.length > 10000 || session.writtenAnswers?.[id] === value) return session;
  const next = { ...session, writtenAnswers: { ...session.writtenAnswers, [id]: value },
    selfScores: { ...session.selfScores }, scoreSources: { ...session.scoreSources },
    aiAssessments: { ...session.aiAssessments }, responses: { ...session.responses },
    scoreRevisions: { ...session.scoreRevisions, [id]: (session.scoreRevisions?.[id] || 0) + 1 } };
  delete next.selfScores[id]; delete next.scoreSources[id]; delete next.aiAssessments[id];
  if (next.responses[id] === 'answered') delete next.responses[id];
  return next;
}
export function manualScore(session, question, value) {
  if (!mayEditSession(session) || !Number.isInteger(value) || value < 0 || value > POINTS[question.type]
    || (!hasWrittenAnswer(session, question.id) && session.responses[question.id] !== 'viewed')) return session;
  const id = question.id;
  return { ...session, selfScores: { ...session.selfScores, [id]: value },
    responses: { ...session.responses, [id]: hasWrittenAnswer(session, id) ? 'answered' : 'viewed' },
    scoreSources: { ...session.scoreSources, [id]: 'manual' },
    scoreRevisions: { ...session.scoreRevisions, [id]: (session.scoreRevisions?.[id] || 0) + 1 } };
}
export function applyAssessment(session, ticket, result, question) {
  if (!mayEditSession(session) || session.attemptId !== ticket.attemptId
    || session.writtenAnswers?.[question.id] !== ticket.answer
    || (session.scoreRevisions?.[question.id] || 0) !== ticket.revision) return session;
  if (result.question_id !== question.id || result.max_score !== POINTS[question.type]
    || !Number.isInteger(result.score) || result.score < 0 || result.score > POINTS[question.type]
    || typeof result.feedback !== 'string' || !Array.isArray(result.strengths) || !Array.isArray(result.missing_points)
    || ![...result.strengths, ...result.missing_points].every(x => typeof x === 'string')) throw new Error('AI 返回的评分格式不正确，请重试或手动评分');
  return { ...session, responses: { ...session.responses, [question.id]: 'answered' },
    selfScores: { ...session.selfScores, [question.id]: result.score },
    scoreSources: { ...session.scoreSources, [question.id]: 'ai' },
    aiAssessments: { ...session.aiAssessments, [question.id]: { ...result, referenceViewed: Boolean(answerRevealed(session, question.id)) } } };
}
