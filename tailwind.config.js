/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ["./App.{js,jsx,ts,tsx}", "./src/**/*.{js,jsx,ts,tsx}"],
  presets: [require("nativewind/preset")],
  theme: {
    extend: {
      colors: {
        vortex: {
          obsidian: "#050505",
          surface: "#0A0A0A",
          saffron: "#FF9933",
          blue: "#0070FF",
          textSecondary: "#A0A0A0",
        }
      }
    },
  },
  plugins: [],
}
