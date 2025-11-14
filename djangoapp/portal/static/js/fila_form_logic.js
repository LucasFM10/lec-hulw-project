/**
 * Lógica de JavaScript para o formulário unificado de Fila (fila_form.html).
 *
 * Este script trata:
 * 1. Inicialização de campos Select2 com busca via AJAX.
 * 2. Lógica de campos dependentes (ex: Procedimento depende de Especialidade).
 * 3. Lógica de UI para campos secundários (mostrar/esconder).
 * 4. Lógica de UI para campos judiciais (mostrar/esconder).
 * 5. Validação client-side básica para campos obrigatórios.
 */
$(function () {

    // ----------------------------------------
    //  Configurações do Select2
    // ----------------------------------------

    // Traduções (i18n) para o Select2 em Português do Brasil
    const s2pt = {
        inputTooShort: a => `Digite pelo menos ${a.minimum} caractere(s)…`,
        errorLoading: () => 'Erro ao carregar os resultados.',
        loadingMore: () => 'Carregando mais resultados…',
        noResults: () => 'Nenhum resultado encontrado.',
        searching: () => 'Buscando…',
        removeAllItems: () => 'Limpar seleção'
    };

    /**
     * Mapeia a resposta da API (que pode ter formatos diferentes)
     * para o formato { results: [ { id: ..., text: ... } ] }
     * que o Select2 espera.
     */
    const mapResults = (data) => ({
        results: (data?.results ?? data ?? []).map(it => ({
            id: String(it.id ?? it.codigo ?? it.cod_especialidade ?? it.matricula ?? ''),
            text: String(it.text ?? it.nome ?? it.nome_especialidade ?? '')
        })),
        pagination: {
            more: !!(data?.pagination && data.pagination.more)
        }
    });

    /**
     * Função "Factory" para inicializar um Select2 com AJAX.
     * Lê a URL da API diretamente do atributo 'data-autocomplete-url'
     * do elemento <select> (injetado pelo Django no forms.py).
     *
     * @param {jQuery} $el - O elemento jQuery do <select>.
     * @param {object} options - Configurações (placeholder, dependsOn, getParams).
     */
    function makeAjaxSelect2($el, { placeholder, getParams, dependsOn }) {

        // Lê a URL do atributo data-* (a "ponte" HTML/JS)
        const ajaxUrl = $el.data('autocomplete-url');

        if (!ajaxUrl) {
            console.error("Select2: Atributo 'data-autocomplete-url' não encontrado no elemento:", $el);
            return;
        }

        $el.select2({
            placeholder,
            allowClear: true,
            width: '100%',
            language: s2pt,
            ajax: {
                url: ajaxUrl, // URL lida do atributo data-*
                dataType: 'json',
                delay: 300,
                // Impede a requisição AJAX se o campo 'dependsOn' (se existir) não estiver preenchido
                transport: (p, ok, fail) => (dependsOn && !dependsOn.val()) ? null : $.ajax(p).then(ok).catch(fail),
                // Monta os parâmetros da query (termo, paginação, etc)
                data: p => getParams ? getParams(p) : ({
                    term: p.term,
                    page: p.page || 1,
                    limit: 10
                }),
                processResults: mapResults,
                cache: true
            }
        });
    }

    /**
     * Habilita/desabilita um Select2 dependente e atualiza seu placeholder.
     * @param {boolean} enabled - Se o campo deve ser habilitado.
     * @param {jQuery} $sel - O elemento jQuery do Select2 dependente.
     */
    const setProcEnabled = (enabled, $sel) => {
        $sel.prop('disabled', !enabled).trigger('change.select2');
        const $ph = $sel.next('.select2-container').find('.select2-selection__placeholder');
        if ($ph.length) {
            $ph.text(enabled ? 'Digite para buscar procedimento…' : 'Selecione uma especialidade primeiro…');
        }
    };


    // ----------------------------------------
    //  Inicialização dos Campos Principais
    // ----------------------------------------
    const $esp = $('#id_especialidade_api');
    const $proc = $('#id_procedimento_api');
    const $med = $('#id_medico_api');
    const $pac = $('#id_prontuario');

    // Especialidade (Principal)
    if ($esp.length) {
        makeAjaxSelect2($esp, {
            placeholder: 'Digite para buscar especialidade…',
            getParams: p => ({ term: p.term, page: p.page || 1, limit: 10 })
        });
    }

    // Procedimento (Principal) - Depende de Especialidade
    if ($proc.length) {
        makeAjaxSelect2($proc, {
            placeholder: 'Selecione uma especialidade primeiro…',
            dependsOn: $esp,
            getParams: p => ({
                term: p.term,
                page: p.page || 1,
                limit: 10,
                especialidade_id: $esp.val() || ''
            })
        });

        // Lógica de dependência:
        // 1. Define o estado inicial do campo (habilitado/desabilitado)
        if ($esp.length) setProcEnabled(!!$esp.val(), $proc);
        // 2. Quando a especialidade muda, limpa e reavalia o estado do procedimento
        $esp.on('change', () => {
            $proc.val(null).trigger('change');
            setProcEnabled(!!$esp.val(), $proc);
        });
    }

    // Médico
    if ($med.length) {
        makeAjaxSelect2($med, {
            placeholder: 'Digite para buscar médico…',
            getParams: p => ({ term: p.term, page: p.page || 1, limit: 10 })
        });
    }

    // Paciente (Prontuário)
    if ($pac.length) {
        makeAjaxSelect2($pac, {
            placeholder: 'Digite nº ou nome do paciente…',
            getParams: p => ({ term: p.term, page: p.page || 1, limit: 10 })
        });
    }


    // ----------------------------------------
    //  Lógica da Seção Secundária (Opcional)
    // ----------------------------------------
    const $esp2 = $('#id_especialidade_secundario_api');
    const $proc2 = $('#id_procedimento_secundario_api');
    const $hiddenOpen = $('#id_secondary_section_open'); // Campo oculto

    if ($esp2.length || $proc2.length) {

        // 1. Injeta o botão "toggle" e o container da seção
        const $wrapProc = $proc.closest('div'); // Onde injetar
        const $ui = $(`
      <div id="secondary-ui" class="mt-2">
        <button type="button" id="toggle-secondary" class="btn-ghost-xs inline-flex items-center gap-1">
          <span id="ico">+</span> Proc. secundário
        </button>
        <div id="secondary-block" class="hidden mt-2">
          <div class="grid grid-cols-1 md:grid-cols-2 gap-4" id="secondary-grid"></div>
          <p class="text-xs text-gray-500 mt-1">Opcional, filtrado pela especialidade selecionada.</p>
        </div>
      </div>`);
        $wrapProc.append($ui);

        // 2. Move os campos (Especialidade 2, Procedimento 2) para dentro do container
        const moveWrap = ($el) => {
            if ($el.length) {
                $el.closest('div').appendTo('#secondary-grid');
            }
        };
        moveWrap($esp2);
        moveWrap($proc2);

        // 3. Inicializa os Select2 dos campos secundários (com mesma lógica de dependência)
        if ($esp2.length) {
            makeAjaxSelect2($esp2, {
                placeholder: 'Digite para buscar especialidade (sec.)…',
                getParams: p => ({ term: p.term, page: p.page || 1, limit: 10 })
            });
        }
        if ($proc2.length) {
            makeAjaxSelect2($proc2, {
                placeholder: 'Selecione uma especialidade primeiro…',
                dependsOn: $esp2,
                getParams: p => ({
                    term: p.term,
                    page: p.page || 1,
                    limit: 10,
                    especialidade_id: $esp2.val() || ''
                })
            });
            setProcEnabled(!!$esp2.val(), $proc2);
            $esp2.on('change', () => {
                $proc2.val(null).trigger('change');
                setProcEnabled(!!$esp2.val(), $proc2);
            });
        }

        // 4. Lógica de "Acordeão" (abrir/fechar)
        const $block = $('#secondary-block'), $ico = $('#ico');
        function openSec() {
            $block.removeClass('hidden'); $ico.text('–');
            if ($hiddenOpen.length) $hiddenOpen.val('on');
        }
        function closeSec() {
            $block.addClass('hidden'); $ico.text('+');
            if ($hiddenOpen.length) $hiddenOpen.val('');
        }
        $('#toggle-secondary').on('click', () => $block.hasClass('hidden') ? openSec() : closeSec());

        // 5. Define o estado inicial (abre se o campo oculto estiver marcado ou se houver valores)
        const shouldOpen = ($hiddenOpen.length && ($hiddenOpen.val() === 'on')) || ($esp2.length && $esp2.val()) || ($proc2.length && $proc2.val());
        if (shouldOpen) openSec();
    }


    // ----------------------------------------
    //  Lógica da Seção Judicial
    // ----------------------------------------
    const $checkboxJudicial = $('#id_medida_judicial');
    const $judicialBlock = $('#judicial-fields-block-full');
    const $judicialGrid = $('#judicial-grid');

    // Lista dos campos que devem ser movidos para o bloco judicial
    const judicialFields = [
        $('#id_judicial_numero'),
        $('#id_judicial_descricao'),
        $('#id_judicial_anexos')
    ];

    if ($checkboxJudicial.length && $judicialBlock.length) {

        // 1. Move os campos (e seus wrappers/labels) para dentro do container
        judicialFields.forEach(function ($field) {
            if ($field.length) {
                // Encontra o 'div' pai (field-wrapper) e o move
                const $wrapper = $field.closest('div');
                $wrapper.appendTo($judicialGrid);
            }
        });

        // 2. Função de toggle (mostrar/esconder) baseada no checkbox
        function updateJudicialVisibility() {
            if ($checkboxJudicial.is(':checked')) {
                $judicialBlock.removeClass('hidden');
            } else {
                $judicialBlock.addClass('hidden');
            }
        }

        // 3. Aplica placeholders (melhoria de UI)
        $('#judicial-grid #id_judicial_numero').attr('placeholder', 'Insira o número do processo...');
        $('#judicial-grid #id_judicial_descricao').attr('placeholder', 'Descreva o teor da medida judicial...');

        // 4. Define o estado inicial ao carregar a página
        $checkboxJudicial.on('change', updateJudicialVisibility);
        updateJudicialVisibility();

        // 5. Mostra os campos (eles iniciam com 'hidden' no HTML)
        judicialFields.forEach(function ($field) {
            if ($field.length) {
                $field.closest('div').removeClass('hidden');
            }
        });
    }


    // ----------------------------------------
    //  Validação Client-side (Básica)
    // ----------------------------------------

    // Remove o feedback de erro
    // Remove o feedback de erro (usa .siblings())
    function clearErrorFor($el) {
        if ($el.hasClass('select2-hidden-accessible')) {
            const $c = $el.next('.select2-container'); 
            $c.removeClass('error');
            // MODIFICADO: usa .siblings() para encontrar o erro
            $c.siblings('.field-error').remove(); 
        } else { 
            $el.removeClass('error-ring');
            // MODIFICADO: usa .siblings() para encontrar o erro
            $el.siblings('.field-error').remove(); 
        }
    }

    // Adiciona o feedback de erro (usa .siblings())
    function showError($el, msg) {
        if ($el.hasClass('select2-hidden-accessible')) {
            const $c = $el.next('.select2-container'); 
            $c.addClass('error'); 
            // MODIFICADO: usa .siblings() para verificar se o erro já existe
            if (!$c.siblings('.field-error').length) { 
                $('<p class="field-error">' + msg + '</p>').insertAfter($c); 
            }
        } else { 
            $el.addClass('error-ring'); 
            // MODIFICADO: usa .siblings() para verificar se o erro já existe
            if (!$el.siblings('.field-error').length) { 
                $('<p class="field-error">' + msg + '</p>').insertAfter($el); 
            } 
        }
    }

    // Encontra todos os campos 'required' que estão visíveis e habilitados
    function getRequiredFields() {
        return $('#lec-form').find('select[required], input[required], textarea[required]').filter(function () {
            return !this.disabled;
        });
    }

    // Verifica se um campo está vazio
    function isEmpty($el) {
        if ($el.is(':checkbox')) return !$el.is(':checked');
        if ($el.is(':radio')) return $(`input[name="${$el.attr('name')}"]:checked`).length === 0;
        const v = $el.val();
        return Array.isArray(v) ? v.length === 0 : (!v || String(v).trim() === '');
    }

    // (Não utilizado no submit, mas limpa o erro ao digitar)
    function bindValidation() {
        getRequiredFields().each(function () {
            const $el = $(this);
            if ($el.hasClass('select2-hidden-accessible')) $el.off('.v').on('select2:select.v select2:clear.v change.v', () => clearErrorFor($el));
            else if ($el.is(':checkbox,:radio')) $(`input[name="${$el.attr('name')}"]`).off('.v').on('change.v', () => clearErrorFor($el));
            else $el.off('.v').on('input.v change.v', () => clearErrorFor($el));
        });
    }
    // bindValidation(); // Descomente se quiser limpeza de erro "on-the-fly"

    // Intercepta o 'submit' do formulário
    $('#lec-form').on('submit', function (e) {
        console.log("Validação client-side iniciada...");
        let ok = true;
        getRequiredFields().each(function () {
            const $el = $(this);
            clearErrorFor($el);
            if (isEmpty($el)) {
                showError($el, 'Campo obrigatório');
                ok = false;
            }
        });

        // Se 'ok' for falso, previne o envio e foca no primeiro erro
        if (!ok) {
            e.preventDefault();
            const $first = $('.field-error').first();
            if ($first.length) {
                $('html,body').animate({ scrollTop: $first.offset().top - 120 }, 250);
            }
        }
    });

    // ==========================================================
    // LÓGICA DE VALIDAÇÃO CONDICIONAL (JUSTIFICATIVA)
    // ==========================================================
    const $prioridade = $('#id_prioridade');
    const $justificativa = $('#id_prioridade_justificativa');
    const $justificativaWrapper = $justificativa.closest('div[id^="field-wrapper"]');

    if ($prioridade.length && $justificativa.length) {

        function updateJustificativaRequired() {
            const prioridadeVal = $prioridade.val();

            // Valores que NÃO exigem justificativa
            const naoExige = ['SEM', ''];

            if (naoExige.includes(prioridadeVal)) {
                // 1. Remove o 'required' (para o JS)
                $justificativa.prop('required', false);

                // 2. Opcional: esconde o campo para uma UI mais limpa
                $justificativaWrapper.addClass('hidden');

                // 3. Remove o feedback de erro se houver
                clearErrorFor($justificativa);

            } else {
                // (ex: "Paciente Oncológico", "Prioritário", etc.)
                // 1. Adiciona o 'required' (para o JS)
                $justificativa.prop('required', true);

                // 2. Opcional: garante que o campo está visível
                $justificativaWrapper.removeClass('hidden');
            }
        }

        // 3. Escuta por mudanças no dropdown de Prioridade
        $prioridade.on('change', updateJustificativaRequired);

        // 4. Roda a verificação uma vez quando a página carrega
        updateJustificativaRequired();
    }
});