/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        primary: {
          DEFAULT: '#BD4006',
          hover: '#A33605',
          light: '#FFDBCF',
        },
        secondary: {
          DEFAULT: '#006C49',
          light: '#6CF8BB',
        },
        error: {
          DEFAULT: '#BA1A1A',
          light: '#FFDAD6',
        },
        success: {
          DEFAULT: '#10B981',
          light: '#ECFDF5',
        },
        warning: {
          DEFAULT: '#F59E0B',
          light: '#FFFBEB',
        },
        surface: {
          DEFAULT: '#F9FAFB',
          low: '#F1F3FF',
          container: '#E9EDFF',
        },
        border: {
          DEFAULT: '#E5E7EB',
          muted: '#D1D5DB',
        },
        text: {
          primary: '#111827',
          secondary: '#6B7280',
          muted: '#9CA3AF',
        },
        role: {
          athlete: '#1C1613',
          coach: '#059669',
          physiotherapist: '#7C3AED',
          sports_scientist: '#D97706',
          administrator: '#DC2626',
        },
      },
      fontFamily: {
        display: ['Space Grotesk', 'sans-serif'],
        body: ['Inter', 'sans-serif'],
        mono: ['JetBrains Mono', 'monospace'],
      },
      borderRadius: {
        sm: '0.125rem',
        DEFAULT: '0.25rem',
        md: '0.375rem',
        lg: '0.5rem',
        xl: '0.75rem',
      },
      spacing: {
        gutter: '1rem',
        'gutter-desktop': '1.5rem',
        margin: '1rem',
        'margin-tablet': '1.5rem',
        'margin-desktop': '2.5rem',
        'space-xs': '0.25rem',
        'space-sm': '0.5rem',
        'space-md': '0.75rem',
        'space-lg': '1.25rem',
        'space-xl': '2rem',
      },
      boxShadow: {
        'card': '0px 1px 3px rgba(17, 24, 39, 0.04)',
        'elevated': '0px 8px 16px -4px rgba(17, 24, 39, 0.08), 0px 2px 4px -1px rgba(17, 24, 39, 0.03)',
        'modal': '0px 20px 24px -4px rgba(17, 24, 39, 0.12)',
      },
    },
  },
  plugins: [],
}
