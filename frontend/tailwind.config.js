/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        // CPCB National AQI Standards Palette
        naqi: {
          good: "#00B050",          // 0 - 50: Green
          satisfactory: "#92D050",  // 51 - 100: Light Green
          moderate: "#FFFF00",      // 101 - 200: Yellow
          poor: "#FF9900",          // 201 - 300: Orange
          veryPoor: "#FF0000",      // 301 - 400: Red
          severe: "#C00000",        // 401 - 500: Dark Red / Maroon
        },
        brand: {
          50: '#F0FDF4',
          100: '#DCFCE7',
          500: '#15803D',
          600: '#166534',
          700: '#14532D',
          800: '#0F3C21',
          900: '#052E16',
        }
      }
    },
  },
  plugins: [],
}
