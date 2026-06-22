export const API_BASE_URL = 'http://localhost:5000/api';

export const NAV_ITEMS = [
  { path: '/', label: '首页', icon: 'home' },
  { path: '/docs', label: '使用文档', icon: 'school' },
  { path: '/experiment', label: '实验运行器', icon: 'science' },
  { path: '/kernel', label: 'FrozenKernel', icon: 'ac_unit' },
  { path: '/massface', label: 'MASS_FACE', icon: 'bar_chart' },
  { path: '/scf', label: '三层信息波', icon: 'waves' },
  { path: '/cgd', label: '约束动力学', icon: 'link' },
  { path: '/mnq9', label: 'MNQ9信心核', icon: 'gps_fixed' },
  { path: '/deep', label: 'MNQ-Deep', icon: 'psychology' },
  { path: '/kappa', label: 'κ-Snap', icon: 'photo_camera' },
  { path: '/history', label: '实验历史', icon: 'assignment' },
];

export const SSE_BASE_URL = 'http://localhost:5000/api/experiment/progress';

export const POLLING_INTERVAL_MS = 3000;
