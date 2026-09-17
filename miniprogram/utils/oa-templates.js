// Keep the two household approval entry points available while the API is
// reconnecting. The server remains the source of truth when it is reachable.
const fallbackTemplates = [
  {
    key: 'leave', name: '游戏 / 出行申请', description: '提交玩游戏或出行的小申请', icon: '🌸', color: '#f69ab7',
    fields: [
      { key: 'plan_type', label: '申请类型', type: 'select', options: ['游戏时间', '约会出行', '旅行计划', '其他'], required: true },
      { key: 'game_name', label: '游戏名称', placeholder: '例如：双人成行', type: 'textarea', required: false },
      { key: 'start_date', label: '开始日期', type: 'date', required: true },
      { key: 'end_date', label: '结束日期', type: 'date', required: true },
      { key: 'reason', label: '计划说明', type: 'textarea', required: true },
    ],
  },
  {
    key: 'purchase', name: '家庭采购', description: '申请一起添置喜欢的生活小物', icon: '🍓', color: '#f4b455',
    fields: [
      { key: 'item_name', label: '', placeholder: '想买的东西', type: 'textarea', required: true },
      { key: 'amount', label: '', placeholder: '预计金额（元）', type: 'textarea', required: true },
      { key: 'reason', label: '想买它的理由', type: 'textarea', required: true },
    ],
  },
];

function getFallbackTemplates() {
  return JSON.parse(JSON.stringify(fallbackTemplates));
}

module.exports = { getFallbackTemplates };
