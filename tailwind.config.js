/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    './djangoapp/portal/templates/**/*.html',
    './djangoapp/fila_cirurgica/templates/**/*.html',
    './djangoapp/externo/templates/**/*.html',
    './djangoapp/portal/static/js/**/*.js'
  ],
  theme: {
    extend: {}
  },
  plugins: []
};
