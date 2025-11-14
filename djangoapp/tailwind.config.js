// tailwind.config.js
module.exports = {
  darkMode: 'selector',
  content: [
    "./templates/**/*.html",            
    "./**/templates/**/*.html",        
    "./**/*.js",
    "./**/*.ts",
  ],
  theme: {
    extend: {},
  },plugins: [
    require('@tailwindcss/forms'),
  ],
}
