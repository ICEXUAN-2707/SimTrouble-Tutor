const labels: Record<string, string> = {
  READY:'准备就绪', EXECUTING:'正在执行', GRASP_ATTEMPT:'尝试抓取', FAILURE_OBSERVED:'发现异常',
  CREATED:'已创建', OBSERVING:'观察中', INVESTIGATING:'调查中', SUBMITTED:'已提交', REVIEWED:'已评估',
  gripper_state:'夹爪状态', gripper_status:'夹爪状态', object_pose:'工件位姿', pose_measurement:'位姿测量', motion_log:'运动记录', controller_log:'控制记录',
  target_pose:'目标位姿', closed:'已闭合', open:'已打开', success:'成功', failure:'失败', close:'闭合',
  x_mm:'横向位置（毫米）',y_mm:'纵向位置（毫米）',z_mm:'高度（毫米）',x:'横向',y:'纵向',z:'高度',
  planned_pose:'计划位姿', actual_pose:'实际位姿', offset:'偏移量', offset_mm:'偏移量（毫米）',
  planned_x_mm:'计划横向位置（毫米）', actual_x_mm:'实际横向位置（毫米）', delta_x_mm:'横向偏移（毫米）',
  grasp_success:'抓取成功', object_attached:'工件已连接', command:'指令', status:'状态',
  expected:'预期', actual:'实际', measured:'测量值', unit:'单位', mm:'毫米', state:'状态', axis:'方向',
  holding_object:'是否夹持工件', expected_mm:'期望位置（毫米）', actual_mm:'实际位置（毫米）',
  target_available:'目标点可用', target_conflict:'目标点冲突',
  observe_scene:'观察场景',inspect_evidence:'查看证据',submit_hypothesis:'提交假设',revise_hypothesis:'修正假设',submit_diagnosis:'提交诊断',reflect:'复盘训练',
};
export function label(value: string, fallback = '其他信息'): string { return labels[value] ?? (/^[\d\s.,:+\-/%]+$/.test(value) ? value : /[\u3400-\u9fff]/.test(value) ? value : fallback); }
export function evidenceName(id: string, type?: string): string { return type && labels[type] ? labels[type] : `证据${id.replace(/\D/g,'') || '详情'}`; }
export function formatValue(value: unknown): string {
  if (value === null) return '暂无数据';
  if (typeof value === 'boolean') return value ? '是' : '否';
  if (typeof value === 'number') return String(value);
  if (Array.isArray(value)) return value.map(formatValue).join('，');
  if (typeof value === 'object') return Object.entries(value).map(([k,v]) => `${fieldLabel(k)}：${formatValue(v)}`).join('；');
  return labels[String(value)] ?? sourceText(String(value));
}

/** Normalize verified public-contract terms without changing the underlying facts. */
export function sourceText(value: string): string {
  return value.replace(/\bmm\b/gi, '毫米').replace(/\bST-\d+\b/gi, '当前案例');
}

export function fieldLabel(value: string): string { return labels[value] ?? sourceText(value); }
