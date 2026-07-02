// Test report feature functions.
// Filtering and summary calculation live here; the UI only renders controls and tables.

export function filterReports(reports, { typeFilter, statusFilter }) {
  return reports.filter((item) => {
    if (typeFilter !== 'all' && item.case_type !== typeFilter) return false;
    if (statusFilter !== 'all' && item.status !== statusFilter) return false;
    return true;
  });
}

export function buildReportSummary(reports) {
  const completed = reports.filter((item) => ['passed', 'failed'].includes(item.status));
  return {
    total: reports.length,
    passed: reports.filter((item) => item.status === 'passed').length,
    failed: reports.filter((item) => item.status === 'failed').length,
    avgDuration: completed.length
      ? Math.round(completed.reduce((sum, item) => sum + (item.duration_ms || 0), 0) / completed.length)
      : null,
  };
}

export function findReportById(reports, reportId) {
  return reports.find((item) => item.id === reportId) || null;
}
