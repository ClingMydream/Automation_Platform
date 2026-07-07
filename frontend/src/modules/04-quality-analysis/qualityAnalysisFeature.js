// File purpose: Quality-analysis helpers. Keep risk labels and table shaping out of the page component.

// Map backend release-risk values to readable UI labels and Ant Design colors.
export function riskMeta(value) {
  const map = {
    high: { label: '高风险', color: 'red' },
    medium: { label: '中风险', color: 'orange' },
    low: { label: '低风险', color: 'green' },
  };
  return map[value] || map.low;
}

// Normalize backend counter items so tables can render empty data safely.
export function counterRows(items = []) {
  return items.map((item, index) => ({
    key: `${item.name}-${index}`,
    name: item.name,
    count: item.count,
  }));
}
