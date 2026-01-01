/** @type {import('tailwindcss').Config} */
export default {
  darkMode: ["class"],
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        // v10.0 Floating Islands 设计系统颜色
        background: {
          app: '#050507',      // 应用背景色
          panel: '#121214',    // 面板背景
          element: '#1c1c1f',  // 元素背景
        },
        border: {
          DEFAULT: 'rgba(255, 255, 255, 0.08)',
          hover: 'rgba(255, 255, 255, 0.15)',
        },
        text: {
          main: '#f4f4f5',
          sub: '#a1a1aa',
        },
        zinc: {
          850: '#1f1f22',
          900: '#18181b',
          950: '#09090b',
        },
      },
      boxShadow: {
        'glow': '0 0 20px -10px rgba(255, 255, 255, 0.1)',
        'panel': '0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06), inset 0 1px 0 rgba(255, 255, 255, 0.05)',
      },
      borderRadius: {
        lg: 'var(--radius)',
        md: 'calc(var(--radius) - 2px)',
        sm: 'calc(var(--radius) - 4px)',
      },
    },
  },
  plugins: [],
}
