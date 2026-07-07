// File purpose: Test report feature helpers. Keep report filtering and summary calculations out of UI.
// How to change: edit UI text/layout in this file; move reusable logic into shared helpers or the module feature file.

// Test report feature functions.
// Filtering and summary calculation live here; the UI only renders controls and tables.

// Filter reports by case type and status.
// Feature block: exported helpers below are used by the page component and can be tested independently.
export function filterReports(reports, { typeFilter, statusFilter }) {
  return reports.filter((item) => {
    if (typeFilter !== 'all' && item.case_type !== typeFilter && item.report_kind !== typeFilter) return false;
    if (statusFilter !== 'all' && item.status !== statusFilter) return false;
    return true;
  });
}

// Calculate report totals, pass/fail counts, and average duration.
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

// Find the selected report by its stable report key.
export function findReportById(reports, reportKey) {
  return reports.find((item) => (item.report_key || String(item.id)) === reportKey) || null;
}
