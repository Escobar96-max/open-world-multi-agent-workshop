/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        orion: {
          50: '#fffbeb',
          500: '#f59e0b',
          600: '#d97706',
          900: '#78350f',
        },
        nova: {
          50: '#fdf2f8',
          400: '#f472b6',
          500: '#ec4899',
          600: '#db2777',
        }
      }
    },
  },
  plugins: [],
}
