/** @type {import('tailwindcss').Config} */

/*
 * Brand palette. See `docs/DESIGN.md` for usage rules.
 *
 *   brand   — the primary blue (#2563a8 at 600). Buttons, links, active states.
 *             A desaturated blue-600; the full ramp is hsl(212, 64%, L) so every
 *             shade index that Tailwind's own `blue` offered still has a match.
 *   accent  — olive-green from the Osteosarcoma Now mark. Section eyebrows, the
 *             `Match` chip, one stat figure. Small type only, never large fills.
 *   surface — warm off-white section backgrounds and the neutral chip tint.
 *   line    — hairline rules and borders (warm, unlike Tailwind's cool gray-200).
 *
 * Headings use `gray-900` (#111827) and body copy `gray-500` (#6b7280) — those are
 * Tailwind defaults that already match the palette, so they need no token here.
 *
 * Tailwind's own `blue`/`green`/`yellow`/`red` ramps stay untouched: the semantic
 * recruitment-status badges in `utils/formatters.ts` map to real
 * ClinicalTrials.gov states and are deliberately not brand-coloured.
 *
 * NOTE: this file is read once when Vite starts. After editing the palette you
 * must restart `npm run dev`, or the new classes compile to nothing and elements
 * like the primary button render as white-on-transparent.
 */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        brand: {
          50:  '#eaf1fa',
          100: '#d5e4f6',
          200: '#abcaed',
          300: '#82afe3',
          400: '#5895da',
          500: '#2e7ad1',
          600: '#2563a8',
          700: '#1e518a',
          800: '#194271',
          900: '#133358',
        },
        accent: {
          50:  '#f0f5e8',
          600: '#8a9a3f',
          700: '#7a9a2e',
          800: '#607623',
        },
        surface: {
          DEFAULT: '#fbfaf8',
          muted:   '#f2f2f1',
        },
        line: {
          DEFAULT: '#e8e6e6',
          soft:    '#eeeeee',
        },
      },
      // Bare `border`, `border-b`, `border-r` … default to Tailwind's cool
      // gray-200. Point them at the warm hairline so they match `border-line`.
      borderColor: {
        DEFAULT: '#e8e6e6',
      },
      // The mobile filter sheet slides up from the bottom edge.
      keyframes: {
        'sheet-up': {
          from: { transform: 'translateY(100%)' },
          to:   { transform: 'translateY(0)' },
        },
      },
      animation: {
        'sheet-up': 'sheet-up 0.22s ease-out',
      },
    },
  },
  plugins: [],
}
