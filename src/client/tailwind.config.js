/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        cortex: {
          ink: "#172027",
          muted: "#66737f",
          line: "#d9e1e6",
          panel: "#ffffff",
          bg: "#f5f7f9",
          teal: "#0f766e",
          tealDark: "#115e59",
          amber: "#a15c07",
          green: "#157347",
          red: "#b42318",
        },
      },
      boxShadow: {
        panel: "0 16px 40px rgba(28, 42, 56, 0.09)",
      },
    },
  },
  plugins: [],
};
