/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        mnq: {
          bg: '#1a1a2e',
          paper: '#16213e',
          card: '#0f3460',
          primary: '#1890ff',
          secondary: '#e94560',
          cyan: '#00d4ff',
          gold: '#ffd700',
          green: '#00ff88',
        },
      },
    },
  },
  plugins: [],
  corePlugins: {
    preflight: false,
  },
};
