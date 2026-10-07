/* Atende AI — tela de atendimento do cliente final (simulação de canal; Telegram principal) */
(function (AT) {
  'use strict';
  const U = AT.U;
  const S = () => AT.S;
  const ETAPAS = { problema: 'Entendendo o problema', pergunta: 'Coletando dados', orcado: 'Orçamento enviado', agendar: 'Aprovado · escolhendo horário', fim: 'Agendado', humano: 'Com atendente humano' };

  function seletorCanais(atual) {
    return '<div class="canais" role="group" aria-label="Canal de atendimento">' + Object.values(AT.Canais.lista).map((c) =>
      '<button type="button" class="canal" data-canal="' + c.id + '" aria-pressed="' + (c.id === atual) + '"' + (c.disponivel ? '' : ' aria-disabled="true"') + '>' +
      '<span aria-hidden="true">' + c.icone + '</span>' + U.esc(c.nome) + (c.disponivel ? '' : ' <span class="breve">em breve</span>') + '</button>').join('') + '</div>';
  }

  function render(main) {
    const seg = S().seg(); const neg = S().negocio(); const canal = AT.Canais.atual();
    const conv = AT.Conversa.estado(seg);
    main.innerHTML = `
      <div class="cab"><div><div class="olho">Passo 2 · Visão do cliente final</div><h1>Atendimento automático no ${U.esc(canal.nome)}</h1>
      <p>Faça o papel do cliente: descreva o problema como ele escreveria. O assistente (simulado por regras) identifica o serviço, pergunta o que falta, gera o orçamento com o seu catálogo, define o prazo e abre o pedido.</p></div>
      ${seletorCanais(canal.id)}</div>
      <div class="duas duas--chat">
        ${AT.Chat.moldura({ id: 'at-chat', avatar: neg.nome.charAt(0), nome: neg.nome, status: 'bot · ' + AT.Chat.botUser(neg.nome), label: 'Mensagem do cliente', placeholder: seg === 'oficina' ? 'Ex.: meu carro tá fazendo barulho ao frear' : 'Ex.: quero pintar meu quarto' })}
        <div class="lateral">
          <section class="card ficha" aria-labelledby="h-ficha" aria-live="polite">
            <div class="linha" style="justify-content:space-between"><h2 id="h-ficha" style="margin:0">O que o assistente entendeu</h2><button type="button" class="btn btn--p" id="at-nova">🔁 Nova conversa</button></div>
            <p class="pequeno muted" style="margin:6px 0 12px">Simulação: palavras-chave e regras do <code>dados.json</code>, sem IA real.</p>
            <div id="at-ficha"></div>
          </section>
          <section class="card">
            <h2>Experimente</h2>
            <ul class="pequeno muted" style="margin:0;padding-left:18px">
              ${seg === 'oficina'
                ? '<li>"Meu Onix 2019 placa FTR4B21 tá fazendo barulho ao frear"</li><li>"O carro não liga, é urgente"</li><li>Escreva "quero falar com atendente" a qualquer momento</li>'
                : '<li>"Quero pintar o quarto, é pro Cambuí"</li><li>"A torneira da cozinha está vazando"</li><li>Escreva "quero falar com atendente" a qualquer momento</li>'}
            </ul>
          </section>
        </div>
      </div>`;
    const box = main.querySelector('#at-chat'); const log = box.querySelector('.cv__log'); const ops = box.querySelector('.cv__opcoes');
    const form = box.querySelector('form'); const inp = form.querySelector('input');
    let ocupado = false;

    function desenhar() {
      const c = AT.Conversa.estado(seg);
      AT.Chat.render(log, AT.Conversa.msgs(c), ['cliente'], canal);
      AT.Chat.opcoes(ops, c.opcoes, (o) => enviar(o));
      ficha(c);
    }
    function ficha(c) {
      const t = AT.Conversa.ticket(c); const d = c.dados; const P = S().dados.prioridades;
      const item = (k, v) => '<dt>' + k + '</dt><dd>' + (v ? U.esc(v) : '<span class="muted">—</span>') + '</dd>';
      let html = '<dl>' + item('Canal', canal.nome + ' · ' + AT.Chat.botUser(neg.nome)) + item('Etapa', ETAPAS[c.etapa] || c.etapa) +
        '<dt>Intenção</dt><dd>' + (c.intent ? U.esc(c.intent.rotulo) + ' <span class="chip chip--azul">' + Math.round(c.confianca * 100) + '% de confiança</span>' : '<span class="muted">aguardando a descrição</span>') + '</dd>' +
        item('Cliente', d.cliente) + (seg === 'oficina' ? item('Veículo', d.veiculo) + item('Placa', d.placa === '' ? 'não informada' : d.placa) : item('Entrega', d.bairro)) +
        item('Urgência', d.urgencia ? P[d.urgencia] : '') + '</dl>';
      if (t) {
        const sla = AT.M.slaEstado(t);
        html += '<hr style="border:0;border-top:1px solid var(--borda);margin:14px 0">' +
          '<div class="linha"><strong>Pedido ' + U.esc(t.id) + '</strong><span class="chip chip--azul">' + U.esc(t.status) + '</span><span class="chip chip--' + sla.cls + '">⏱️ ' + U.esc(sla.texto) + '</span>' + (t.humano ? '<span class="chip chip--atencao">🙋 atendente</span>' : '') + '</div>' +
          (t.itens.length ? '<p class="pequeno" style="margin:8px 0 4px">Serviços: ' + t.itens.map((i) => U.esc(i.nome)).join(' + ') + '</p>' : '') +
          (t.status !== 'Novo' ? '<p class="pequeno" style="margin:0 0 8px">Total: <strong>' + U.faixa(t.total.min, t.total.max) + '</strong> · prazo ' + U.dataHora(t.prazo) + '</p>' : '') +
          '<a class="btn btn--p" href="#/pedidos/' + encodeURIComponent(t.id) + '">Abrir em Pedidos →</a>';
      }
      main.querySelector('#at-ficha').innerHTML = html;
    }
    function enviar(texto, valor) {
      texto = String(texto || '').trim(); if (!texto || ocupado) return;
      if (valor === 'nova') { AT.Conversa.iniciar(seg); desenhar(); inp.focus(); return; }
      ocupado = true;
      AT.Conversa.receber(seg, texto); desenhar(); AT.Chat.digitando(log, true);
      setTimeout(() => { AT.Conversa.processar(seg, texto, valor); AT.Chat.digitando(log, false); desenhar(); ocupado = false; }, AT.Chat.atraso());
    }
    AT.Chat.ligarTeclado(log, (valor, rotulo) => enviar(rotulo, valor));
    form.addEventListener('submit', (e) => { e.preventDefault(); const v = inp.value; inp.value = ''; enviar(v); });
    main.querySelector('#at-nova').addEventListener('click', () => { AT.Conversa.iniciar(seg); desenhar(); inp.focus(); });
    main.querySelectorAll('.canal').forEach((b) => b.addEventListener('click', () => {
      const c = AT.Canais.get(b.dataset.canal);
      if (!c.disponivel) { U.toast(c.nome + ' chega depois, como segundo adaptador do mesmo motor. Hoje o canal ativo é o Telegram.'); return; }
      S().st.canal = c.id; S().salvar(); render(main);
    }));
    desenhar();
    AT.V.atendimento._tick = () => { if (document.body.contains(main.querySelector('#at-ficha'))) ficha(AT.Conversa.estado(seg)); };
  }
  AT.V = AT.V || {};
  AT.V.atendimento = { titulo: 'Atendimento', render };
})(window.AT);
