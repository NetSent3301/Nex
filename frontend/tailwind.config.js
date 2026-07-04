/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ["./src/**/*.{html,ts}"],
  theme: {
    extend: {
      fontFamily: {
        sans: ['"Outfit"', '-apple-system', 'BlinkMacSystemFont', '"Segoe UI"', 'Roboto', 'sans-serif'],
        mono: ['"Cascadia Code"', '"Fira Code"', '"JetBrains Mono"', 'Consolas', 'monospace'],
      },
      colors: {
        nex: {
          bg: '#080809',
          surface: '#121214',
          panel: '#121214',
          accent: '#6366f1',
        },
      },
      animation: {
        'message-in': 'messageSlideIn 0.25s cubic-bezier(0.16, 1, 0.3, 1)',
        'pulse-dot': 'pulseDot 1.4s infinite ease-in-out both',
        'fade-in': 'fadeIn 0.3s ease-out',
        'shine': 'shine 4s linear infinite',
      },
      keyframes: {
        messageSlideIn: {
          '0%': { opacity: '0', transform: 'translateY(8px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
        pulseDot: {
          '0%, 80%, 100%': { transform: 'scale(0)' },
          '40%': { transform: 'scale(1)' },
        },
        fadeIn: {
          '0%': { opacity: '0' },
          '100%': { opacity: '1' },
        },
        shine: {
          '0%': { backgroundPosition: '200% 0' },
          '100%': { backgroundPosition: '-200% 0' },
        },
      },
    },
  },
  plugins: [],
};
