export function formatTimestamp(ts: string): string {
  const d = new Date(ts);
  return d.toLocaleString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  });
}

export function formatNumber(val: number, digits = 4): string {
  if (val == null || !isFinite(val)) return 'N/A';
  if (val === 0) return '0';
  if (Math.abs(val) < 0.001 && val !== 0) return val.toExponential(digits);
  return val.toFixed(digits);
}

export function formatPercent(val: number): string {
  if (val == null || !isFinite(val)) return 'N/A';
  return `${(val * 100).toFixed(1)}%`;
}

export function statusColor(status: string): string {
  switch (status) {
    case 'completed': return '#00ff88';
    case 'running': return '#1890ff';
    case 'pending': return '#ffd700';
    case 'failed': return '#e94560';
    default: return '#888';
  }
}

export function gateBadge(pass: boolean): { label: string; color: string } {
  return pass
    ? { label: 'PASS', color: '#00ff88' }
    : { label: 'FAIL', color: '#e94560' };
}
