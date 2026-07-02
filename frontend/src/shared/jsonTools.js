// JSON 工具模块。
// 修改建议：如果后续要支持“忽略字段”“数组按 key 对比”等能力，优先扩展 compareJsonValues。

// Parse user JSON input and treat empty input as null.
export function parseJsonInput(text) {
  return JSON.parse(text || 'null');
}

// Stringify JSON with stable indentation or compact output.
export function stableStringifyJson(value, compact = false) {
  return JSON.stringify(value, null, compact ? 0 : 2);
}

// Return the precise JSON value type used by comparison.
function valueType(value) {
  if (Array.isArray(value)) return 'array';
  if (value === null) return 'null';
  return typeof value;
}

// Convert a compared value into short table display text.
function previewValue(value) {
  if (value === undefined) return '不存在';
  if (typeof value === 'string') return value;
  return JSON.stringify(value);
}

// Recursively compare two JSON values and return path-level differences.
export function compareJsonValues(left, right, path = '$') {
  const diffs = [];
  const leftType = valueType(left);
  const rightType = valueType(right);
  if (leftType !== rightType) {
    return [{ path, type: '类型不同', left: previewValue(left), right: previewValue(right) }];
  }
  if (leftType === 'object') {
    const keys = new Set([...Object.keys(left), ...Object.keys(right)]);
    [...keys].sort().forEach((key) => {
      const nextPath = `${path}.${key}`;
      if (!(key in left)) diffs.push({ path: nextPath, type: '右侧新增', left: '不存在', right: previewValue(right[key]) });
      else if (!(key in right)) diffs.push({ path: nextPath, type: '左侧独有', left: previewValue(left[key]), right: '不存在' });
      else diffs.push(...compareJsonValues(left[key], right[key], nextPath));
    });
    return diffs;
  }
  if (leftType === 'array') {
    const max = Math.max(left.length, right.length);
    for (let index = 0; index < max; index += 1) {
      const nextPath = `${path}[${index}]`;
      if (index >= left.length) diffs.push({ path: nextPath, type: '右侧新增', left: '不存在', right: previewValue(right[index]) });
      else if (index >= right.length) diffs.push({ path: nextPath, type: '左侧独有', left: previewValue(left[index]), right: '不存在' });
      else diffs.push(...compareJsonValues(left[index], right[index], nextPath));
    }
    return diffs;
  }
  if (left !== right) {
    diffs.push({ path, type: '值不同', left: previewValue(left), right: previewValue(right) });
  }
  return diffs;
}
