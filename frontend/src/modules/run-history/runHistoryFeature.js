// Run history feature functions.
// Summary calculation is kept outside the component so the table UI remains simple.

// Calculate total, running, passed, and failed run counts.
export function buildRunSummary(runs) {
  return {
    total: runs.length,
    running: runs.filter((run) => ['queued', 'running'].includes(run.status)).length,
    passed: runs.filter((run) => run.status === 'passed').length,
    failed: runs.filter((run) => run.status === 'failed').length,
  };
}

// Find the selected run by ID for detail display.
export function findRunById(runs, runId) {
  return runs.find((run) => run.id === runId) || null;
}
