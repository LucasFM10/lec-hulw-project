// 1) Carrega Chart.js se ainda não estiver presente
(function ensureChartJS(cb) {
    if (window.Chart) return cb();
    var s = document.createElement('script');
    s.onload = cb;
    s.onerror = function () { console.error("Chart.js não pôde ser carregado."); };
    document.head.appendChild(s);
})(initDashboardCharts);

// 2) Utilitário seguro p/ ler <script type="application/json" id="...">
function getJSON(id, fallback) {
    var el = document.getElementById(id);
    if (!el) return fallback;
    try {
        var txt = (el.textContent || "").trim();
        if (!txt) return fallback;
        var parsed = JSON.parse(txt);
        return (parsed === null ? fallback : parsed);
    } catch (e) { return fallback; }
}

function initDashboardCharts() {
    const COLORS = (window.indicadoresColors && window.indicadoresColors.length)
        ? window.indicadoresColors
        : ["#3B82F6", "#10B981", "#F59E0B", "#EF4444", "#8B5CF6", "#06B6D4", "#84CC16", "#F472B6", "#F97316", "#22C55E"];

    const labels = getJSON('labels_json', []);
    const data = getJSON('data_json', []);
    const percentages = getJSON('percentages_json', []);
    const labelsBar = getJSON('labels_bar_json', []);
    const dataBar = getJSON('data_bar_json', []);
    const labelsProcCnt = getJSON('labels_proc_count_json', []);
    const dataProcCnt = getJSON('data_proc_count_json', []);
    const labelsProcWait = getJSON('labels_proc_wait_json', []);
    const dataProcWait = getJSON('data_proc_wait_json', []);

    const commonOptions = {
        responsive: true, maintainAspectRatio: false,
        plugins: {
            legend: { labels: { color: '#374151', font: { size: 12 } } },
            tooltip: {
                backgroundColor: '#111827', titleColor: '#F9FAFB', bodyColor: '#D1D5DB',
                borderColor: '#6B7280', borderWidth: 1
            }
        },
        scales: {
            x: { ticks: { color: '#6B7280' }, grid: { color: '#E5E7EB' } },
            y: { ticks: { color: '#6B7280' }, grid: { color: '#E5E7EB' } },
        }
    };

    // Pie// Pie
    if (labels.length && data.length) {
      const el = document.getElementById('pieChart');
      if (el) {

        // Geramos e armazenamos as cores originais do gráfico de pizza
        // Isso é necessário para que possamos restaurar a opacidade total no 'onLeave'
        const pieChartColors = labels.map((_, i) => COLORS[i % COLORS.length]);

        /**
         * Callback para o 'onHover' da legenda (quando o mouse passa sobre um item).
         * Ele aplica transparência (alpha '4D') a todas as fatias, *exceto*
         * à fatia correspondente ao item da legenda.
         */
        const handleLegendHover = (evt, item, legend) => {
          const chart = legend.chart;
          const dataset = chart.data.datasets[0];

          // Mapeia as cores: aplica '4D' (aprox. 30% opacidade) se o índice
          // NÃO for o do item que está sofrendo o hover.
          dataset.backgroundColor = pieChartColors.map((color, index) => {
            return (index === item.index) ? color : color + '4D';
          });

          chart.update();
        };

        /**
         * Callback para o 'onLeave' da legenda (quando o mouse sai).
         * Restaura todas as fatias para suas cores originais (opacidade total).
         */
        const handleLegendLeave = (evt, item, legend) => {
          const chart = legend.chart;
          const dataset = chart.data.datasets[0];
          
          // Restaura o array de cores original
          dataset.backgroundColor = pieChartColors;
          chart.update();
        };

        // Instancia o gráfico de Pizza
        new Chart(el, {
          type: 'pie',
          data: {
            labels,
            datasets: [{
              data,
              backgroundColor: pieChartColors, // Define as cores iniciais
              borderWidth: 1,
              borderColor: '#ffffff',
              hoverOffset: 8 // Efeito "saltar" ao passar o mouse na fatia
            }]
          },
          options: {
            layout: {
              padding: 10 // Adiciona 10px de espaço interno para a animação
            },
            plugins: {
              ...commonOptions.plugins,
              legend: {
                ...commonOptions.plugins.legend, // Herda estilos de labels da legenda
                onHover: handleLegendHover,
                onLeave: handleLegendLeave
              },
              tooltip: {
                ...commonOptions.plugins.tooltip,
                callbacks: {
                  // Tooltip customizado para exibir: "Rótulo: Valor (Pct%)"
                  label: (ctx) => {
                    const pct = percentages[ctx.dataIndex] ?? 0;
                    return `${ctx.label}: ${ctx.parsed} (${pct}%)`;
                  }
                }
              }
            }
          }
        });
      }
    }

    // Barras (entradas criadas)
    if (labelsBar.length && dataBar.length) {
        const el = document.getElementById('barChart');
        if (el) new Chart(el, {
            type: 'bar',
            data: {
                labels: labelsBar,
                datasets: [{ label: 'Entradas criadas', data: dataBar, backgroundColor: '#3B82F6', borderRadius: 6 }]
            },
            options: {
                ...commonOptions,
                scales: {
                    y: { beginAtZero: true, ticks: { precision: 0, color: '#6B7280' }, grid: { color: '#E5E7EB' } },
                    x: { ticks: { color: '#6B7280' }, grid: { display: false } }
                }
            }
        });
    }

    // Top-10 por quantidade (ativos)
    if (labelsProcCnt.length && dataProcCnt.length) {
        const el = document.getElementById('procCountChart');
        if (el) new Chart(el, {
            type: 'bar',
            data: {
                labels: labelsProcCnt,
                datasets: [{ label: 'Pacientes (ativos)', data: dataProcCnt, backgroundColor: '#10B981', borderRadius: 6 }]
            },
            options: {
                ...commonOptions,
                indexAxis: 'y',
                scales: {
                    x: { beginAtZero: true, ticks: { precision: 0, color: '#6B7280' }, grid: { color: '#E5E7EB' } },
                    y: { ticks: { color: '#6B7280' }, grid: { display: false } }
                }
            }
        });
    }

    // Top-10 por espera (ativos)
    if (labelsProcWait.length && dataProcWait.length) {
        const el = document.getElementById('procWaitChart');
        if (el) new Chart(el, {
            type: 'bar',
            data: {
                labels: labelsProcWait,
                datasets: [{ label: 'Dias de espera (ativos)', data: dataProcWait, backgroundColor: '#F59E0B', borderRadius: 6 }]
            },
            options: {
                ...commonOptions,
                indexAxis: 'y',
                scales: {
                    x: { beginAtZero: true, ticks: { precision: 0, color: '#6B7280' }, grid: { color: '#E5E7EB' } },
                    y: { ticks: { color: '#6B7280' }, grid: { display: false } }
                }
            }
        });
    }
}