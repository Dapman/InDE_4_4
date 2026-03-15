/** @type {import('tailwindcss').Config} */
export default {
  darkMode: 'class',
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      // ================================================================
      // COLOR SYSTEM
      // ================================================================
      colors: {
        // shadcn/ui CSS variable colors
        border: 'hsl(var(--border))',
        input: 'hsl(var(--input))',
        ring: 'hsl(var(--ring))',
        background: 'hsl(var(--background))',
        foreground: 'hsl(var(--foreground))',
        primary: {
          DEFAULT: 'hsl(var(--primary))',
          foreground: 'hsl(var(--primary-foreground))',
        },
        secondary: {
          DEFAULT: 'hsl(var(--secondary))',
          foreground: 'hsl(var(--secondary-foreground))',
        },
        destructive: {
          DEFAULT: 'hsl(var(--destructive))',
          foreground: 'hsl(var(--destructive-foreground))',
        },
        muted: {
          DEFAULT: 'hsl(var(--muted))',
          foreground: 'hsl(var(--muted-foreground))',
        },
        popover: {
          DEFAULT: 'hsl(var(--popover))',
          foreground: 'hsl(var(--popover-foreground))',
        },
        card: {
          DEFAULT: 'hsl(var(--card))',
          foreground: 'hsl(var(--card-foreground))',
        },

        // Core brand
        inde: {
          50:  '#eef2ff',
          100: '#e0e7ff',
          200: '#c7d2fe',
          300: '#a5b4fc',
          400: '#818cf8',
          500: '#6366f1',   // Primary
          600: '#4f46e5',
          700: '#4338ca',
          800: '#3730a3',
          900: '#312e81',
          950: '#1e1b4b',
        },

        // Surface colors (dark theme primary)
        surface: {
          0:   '#09090b',   // Deepest background
          1:   '#0f0f12',   // App background
          2:   '#18181b',   // Card/panel background
          3:   '#1f1f23',   // Elevated surface
          4:   '#27272a',   // Hover state
          5:   '#3f3f46',   // Active/selected state
          border: '#27272a', // Default border
          'border-light': '#3f3f46', // Emphasized border
        },

        // Light mode surfaces
        'surface-light': {
          0:   '#ffffff',
          1:   '#fafafa',
          2:   '#f4f4f5',
          3:   '#e4e4e7',
          4:   '#d4d4d8',
          5:   '#a1a1aa',
          border: '#e4e4e7',
          'border-light': '#d4d4d8',
        },

        // Innovation phase colors
        phase: {
          vision:   { DEFAULT: '#3b82f6', light: '#93c5fd', dark: '#1d4ed8' },
          pitch:    { DEFAULT: '#8b5cf6', light: '#c4b5fd', dark: '#6d28d9' },
          derisk:   { DEFAULT: '#10b981', light: '#6ee7b7', dark: '#059669' },
          build:    { DEFAULT: '#f59e0b', light: '#fcd34d', dark: '#d97706' },
          deploy:   { DEFAULT: '#f43f5e', light: '#fda4af', dark: '#e11d48' },
        },

        // Confidence levels
        confidence: {
          high:     '#22c55e',  // Strong pattern
          moderate: '#f59e0b',  // Emerging pattern
          low:      '#8b5cf6',  // Tentative
          insufficient: '#6b7280', // Not enough data
        },

        // Health zones
        health: {
          healthy:  '#22c55e',
          caution:  '#f59e0b',
          atrisk:   '#ef4444',
        },

        // Semantic
        accent: {
          blue:    '#3b82f6',
          violet:  '#8b5cf6',
          emerald: '#10b981',
          amber:   '#f59e0b',
          rose:    '#f43f5e',
        },
      },

      // ================================================================
      // TYPOGRAPHY
      // ================================================================
      fontFamily: {
        display: ['"DM Sans"', 'system-ui', 'sans-serif'],
        body:    ['"Source Sans 3"', 'system-ui', 'sans-serif'],
        mono:    ['"JetBrains Mono"', '"Fira Code"', 'monospace'],
      },

      fontSize: {
        'display-xl': ['2.5rem',  { lineHeight: '1.1', letterSpacing: '-0.025em', fontWeight: '700' }],
        'display-lg': ['2rem',    { lineHeight: '1.15', letterSpacing: '-0.02em', fontWeight: '700' }],
        'display-md': ['1.5rem',  { lineHeight: '1.2', letterSpacing: '-0.015em', fontWeight: '600' }],
        'display-sm': ['1.25rem', { lineHeight: '1.25', letterSpacing: '-0.01em', fontWeight: '600' }],
        'body-lg':    ['1.0625rem', { lineHeight: '1.6' }],
        'body-md':    ['0.9375rem', { lineHeight: '1.6' }],
        'body-sm':    ['0.8125rem', { lineHeight: '1.5' }],
        'caption':    ['0.75rem',   { lineHeight: '1.4' }],
        'overline':   ['0.6875rem', { lineHeight: '1.3', letterSpacing: '0.05em', fontWeight: '600' }],
      },

      // ================================================================
      // SPACING & LAYOUT
      // ================================================================
      spacing: {
        'sidebar-collapsed': '3.5rem',     // 56px
        'sidebar-expanded':  '16rem',      // 256px
        'sidebar-wide':      '20rem',      // 320px
        'topbar':            '3.5rem',      // 56px
        'statusbar':         '1.75rem',     // 28px
      },

      // ================================================================
      // EFFECTS
      // ================================================================
      backdropBlur: {
        'glass': '12px',
      },

      boxShadow: {
        'glass':    '0 4px 30px rgba(0, 0, 0, 0.1)',
        'panel':    '0 1px 3px rgba(0, 0, 0, 0.3), 0 1px 2px rgba(0, 0, 0, 0.2)',
        'elevated': '0 4px 6px rgba(0, 0, 0, 0.3), 0 2px 4px rgba(0, 0, 0, 0.2)',
        'modal':    '0 20px 60px rgba(0, 0, 0, 0.5)',
        'glow-inde': '0 0 20px rgba(99, 102, 241, 0.15)',
      },

      // ================================================================
      // ANIMATIONS
      // ================================================================
      keyframes: {
        'fade-in': {
          from: { opacity: '0' },
          to:   { opacity: '1' },
        },
        'slide-in-left': {
          from: { transform: 'translateX(-100%)' },
          to:   { transform: 'translateX(0)' },
        },
        'slide-in-right': {
          from: { transform: 'translateX(100%)' },
          to:   { transform: 'translateX(0)' },
        },
        'slide-up': {
          from: { transform: 'translateY(8px)', opacity: '0' },
          to:   { transform: 'translateY(0)', opacity: '1' },
        },
        'pulse-gentle': {
          '0%, 100%': { opacity: '1' },
          '50%': { opacity: '0.7' },
        },
        'shimmer': {
          '0%':   { backgroundPosition: '-200% 0' },
          '100%': { backgroundPosition: '200% 0' },
        },
      },
      animation: {
        'fade-in':        'fade-in 0.2s ease-out',
        'slide-in-left':  'slide-in-left 0.25s ease-out',
        'slide-in-right': 'slide-in-right 0.25s ease-out',
        'slide-up':       'slide-up 0.2s ease-out',
        'pulse-gentle':   'pulse-gentle 2s ease-in-out infinite',
        'shimmer':        'shimmer 2s linear infinite',
      },

      // ================================================================
      // BORDER RADIUS
      // ================================================================
      borderRadius: {
        'panel': '0.75rem',
        'card':  '0.625rem',
        'badge': '9999px',
        lg: 'var(--radius)',
        md: 'calc(var(--radius) - 2px)',
        sm: 'calc(var(--radius) - 4px)',
      },
    },
  },
  plugins: [
    require('@tailwindcss/typography'),
  ],
}
