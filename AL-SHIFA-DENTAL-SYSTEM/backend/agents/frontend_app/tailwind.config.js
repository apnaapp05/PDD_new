/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        medical: {
          50: '#eef8ff',
          100: '#dcf0ff',
          200: '#b3e2ff',
          300: '#70cbff',
          400: '#24adff',
          500: '#0091ff',
          600: '#0077B6', // Primary Brand Color
          700: '#005f96',
          800: '#00517d',
          900: '#054366',
        }
      }
    },
  },
  plugins: [],
}