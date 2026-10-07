/* Atende AI — pedidos (kanban/lista), SLA e cadeia de automações */
(function (AT) {
  'use strict';
  const U = AT.U, M = AT.M;
  const S = () => AT.S;
  const filtro = { busca: '', prio: '', sla: '', modo: 'kanban' };
  let mainRef = null, abertoDe = null;

  const slaChip = (t) => { const s = M.slaEstado(t); return '<span class="chip chip--' + s.cls + '" data-sla="' + U.esc(t.id) + '">⏱️ ' + U.esc(s.texto) + '</span>'; };
  const prioChip = (p) => '<span class="chip' + (p === 'alta' ? ' chip--erro' : p === 'media' ? ' chip--atencao' : '') + '">' + S().dados.prioridades[p] + '</span>';
  const servicos = (t) => (t.itens && t.itens.length ? t.itens.map((i) => i.nome).join(' + ') : t.problema);

  function filtrados() {
    const b = U.norm(filtro.busca);
    return S().ticketsSeg().filter((t) => {
      if (filtro.prio && t.prioridade !== filtro.prio) return false;
      if (filtro.sla && M.slaEstado(t).cls !== filtro.sla) return false;
      if (b && !U.norm([t.id, t.cliente, t.placa, t.veiculo, t.problema, servicos(t)].join(' ')).includes(b)) return false;
      return true;
    });
  }

  function cartao(t) {
    const s = M.slaEstado(t);
    return '<li><button type="button" class="tk' + (t._novo ? ' tk--novo' : '') + '" data-id="' + U.esc(t.id) + '" aria-label="Pedido ' + U.esc(t.id) + ', ' + U.esc(t.cliente) + ', ' + U.esc(t.status) + ', ' + U.esc(s.texto) + '">' +
      '<span class="tk__top"><span>' + U.esc(t.id) + (t.vivo ? ' · ao vivo' : t.exemplo ? ' · exemplo' : ' · novo') + '</span><span>' + U.dataCurta(t.criado) + ' ' + U.hora(t.criado) + '</span></span>' +
      '<span class="tk__nome">' + U.esc(t.cliente) + (t.humano ? ' 🙋' : '') + '</span>' +
      '<span class="tk__serv">' + U.esc(servicos(t)) + (t.veiculo ? ' · ' + U.esc(t.veiculo) : '') + '</span>' +
      '<span class="tk__rod">' + slaChip(t) + '<strong class="pequeno">' + (t.total && t.total.max ? U.brl(t.valorFinal || M.valorMedio(t)) : '—') + '</strong></span></button></li>';
  }

  function desenharQuadro() {
    const lista = filtrados(); const area = mainRef.querySelector('#pd-area');
    mainRef.querySelector('#pd-total').textContent = lista.length + ' pedido(s)';
    if (filtro.modo === 'kanban') {
      area.innerHTML = '<div class="kanban">' + S().dados.status.map((st) => {
        const col = lista.filter((t) => t.status === st);
        return '<section class="coluna" aria-label="' + st + '"><h2>' + st + ' <span class="chip">' + col.length + '</span></h2><ol>' + (col.map(cartao).join('') || '<li class="pequeno muted" style="padding:6px">Nenhum pedido</li>') + '</ol></section>';
      }).join('') + '</div>';
    } else {
      area.innerHTML = '<div class="tabela-wrap"><table><thead><tr><th>Pedido</th><th>Cliente</th><th>Serviço</th><th>Status</th><th>Prioridade</th><th>SLA</th><th class="num">Valor</th><th><span class="sr">Abrir</span></th></tr></thead><tbody>' +
        lista.map((t) => '<tr><td>' + U.esc(t.id) + (t.exemplo ? ' <span class="chip chip--exemplo">exemplo</span>' : '') + '</td><td>' + U.esc(t.cliente) + '</td><td>' + U.esc(servicos(t)) + '</td><td>' + U.esc(t.status) + '</td><td>' + prioChip(t.prioridade) + '</td><td>' + slaChip(t) + '</td><td class="num">' + (t.total && t.total.max ? U.faixa(t.total.min, t.total.max) : '—') + '</td><td><button type="button" class="btn btn--p tk-abrir" data-id="' + U.esc(t.id) + '">Detalhes</button></td></tr>').join('') +
        '</tbody></table></div>';
    }
    area.querySelectorAll('[data-id]').forEach((b) => b.addEventListener('click', () => abrir(b.dataset.id, b)));
    S().st.tickets.forEach((t) => { delete t._novo; });
  }

  function linhaTempo(t) {
    const regras = S().st.automacoes[t.seg] || [];
    return '<ol class="linha-tempo">' + regras.map((r) => {
      const ev = t.eventos.filter((e) => e.regra === r.id).pop();
      let cls = '', est;
      if (!r.ativo && !ev) { cls = 'desligado'; est = 'regra desligada'; }
      else if (ev && ev.estado === 'enviado') { cls = 'enviado'; est = 'enviada ' + U.dataHora(ev.ts); }
      else if (ev && ev.estado === 'agendado') { cls = 'agendado'; est = 'programada para ' + U.dataHora(ev.ts); }
      else est = 'aguardando status "' + r.gatilho + '"';
      return '<li class="' + cls + '"><div class="t">' + U.esc(r.nome) + '</div><div class="pequeno muted">' + U.esc(est) + ' · ' + U.esc(r.quando) + '</div>' + (ev ? '<div class="q">' + U.esc(ev.texto) + '</div>' : '') + '</li>';
    }).join('') + '</ol>';
  }

  function corpoGaveta(t) {
    const def = S().segDef(t.seg); const rot = def.rotulos; const ordem = S().dados.status; const i = ordem.indexOf(t.status);
    const prox = M.proximoStatus(t);
    const pos = t.eventos.find((e) => e.regra === 'posvenda' && e.estado === 'agendado');
    const acao = t.vivo ? null : prox ? '▶ Simular avanço para "' + prox + '"' : pos ? '▶ Simular envio do pós-venda agora' : null;
    const canal = AT.Canais.get(t.canal);
    const dd = (k, v) => (v ? '<dt>' + k + '</dt><dd>' + U.esc(v) + '</dd>' : '');
    return `
      <div class="gaveta__cab"><div><h2 id="gv-titulo">Pedido ${U.esc(t.id)}</h2>
        <div class="linha">${t.vivo ? '<span class="chip chip--ok">ao vivo · Telegram</span>' : t.exemplo ? '<span class="chip chip--exemplo">dados de exemplo</span>' : '<span class="chip chip--azul">criado nesta demonstração</span>'}${prioChip(t.prioridade)}${slaChip(t)}</div></div>
        <button type="button" class="btn btn--p fechar" aria-label="Fechar detalhes">✕</button></div>
      <div class="gaveta__corpo">
        <section><h3>Etapa</h3><div class="pipeline">${ordem.map((s, k) => '<span class="' + (k < i ? 'feito' : k === i ? 'atual' : '') + '">' + s + '</span>').join('')}</div>
          <div class="linha" style="margin-top:10px">${acao ? '<button type="button" class="btn btn--pri" id="gv-avancar">' + acao + '</button>' : '<span class="muted pequeno">' + (t.vivo ? 'Pedido real do bot (somente leitura): avance pelos botões do dono no Telegram.' : 'Ciclo completo: entregue e pós-venda enviado.') + '</span>'}</div>
          <p class="pequeno muted" style="margin:6px 0 0">Cada avanço dispara as automações ativas daquela etapa, como faria o servidor da fase 2.</p></section>
        <section class="ficha"><h3>Cliente</h3><dl>
          ${dd('Nome', t.cliente)}${dd('Canal', canal.nome)}${dd('Telefone', t.telefone)}${dd('Veículo', t.veiculo)}${dd('Placa', t.placa)}${dd('Entrega', t.bairro)}
          ${dd('Relato', t.problema)}${dd('Aberto', U.dataHora(t.criado))}${dd('Prazo (SLA)', U.dataHora(t.prazo))}${t.agendamento ? dd('Agendado', U.dataHora(t.agendamento)) : ''}
          ${dd('1ª resposta', U.tempoResp(t.tempoRespostaSeg || 0) + (t.humano ? ' (atendente)' : ' (automática)'))}${t.nps != null ? dd('NPS', String(t.nps)) : ''}</dl></section>
        <section><h3>Orçamento</h3>${t.itens && t.itens.length ? '<div class="tabela-wrap"><table><thead><tr><th>Item</th><th class="num">' + U.esc(rot.pecas) + '</th><th class="num">' + U.esc(rot.mao) + '</th></tr></thead><tbody>' +
          t.itens.map((it) => '<tr><td>' + U.esc(it.nome) + '</td><td class="num">' + U.faixaT(it.pecasMin, it.pecasMax) + '</td><td class="num">' + U.faixaT(it.maoMin, it.maoMax) + '</td></tr>').join('') +
          '<tr><td><strong>Total</strong></td><td class="num" colspan="2"><strong>' + U.faixa(t.total.min, t.total.max) + '</strong>' + (t.valorFinal ? '<br><span class="pequeno muted">cobrado: ' + U.brl(t.valorFinal) + '</span>' : '') + '</td></tr></tbody></table></div>' : '<p class="muted pequeno">Sem orçamento ainda (aguardando atendente).</p>'}</section>
        <section><h3>Cadeia de mensagens automáticas</h3>${linhaTempo(t)}</section>
        <section><h3>Conversa completa (${U.esc(canal.nome)})</h3><div class="mini-chat ${canal.classe}" id="gv-chat" role="log" aria-label="Histórico da conversa"></div></section>
      </div>`;
  }

  function abrir(id, origem) {
    const t = S().ticket(id); if (!t) return;
    abertoDe = origem || document.activeElement;
    const raiz = document.getElementById('gaveta-raiz');
    raiz.innerHTML = '<div class="veu" data-fechar></div><aside class="gaveta" role="dialog" aria-modal="true" aria-labelledby="gv-titulo"></aside>';
    const gv = raiz.querySelector('.gaveta');
    const pintar = () => {
      gv.innerHTML = corpoGaveta(t);
      const chat = gv.querySelector('#gv-chat');
      AT.Chat.render(chat, t.chat, ['cliente'], AT.Canais.get(t.canal));
      chat.querySelectorAll('.tecla').forEach((b) => { b.disabled = true; });
      gv.querySelector('.fechar').addEventListener('click', fechar);
      const av = gv.querySelector('#gv-avancar');
      if (av) av.addEventListener('click', () => { avancar(t); pintar(); gv.querySelector('#gv-avancar, .fechar').focus(); desenharQuadro(); });
    };
    pintar();
    raiz.querySelector('[data-fechar]').addEventListener('click', fechar);
    gv.addEventListener('keydown', (e) => {
      if (e.key === 'Escape') { e.preventDefault(); fechar(); }
      if (e.key === 'Tab') {
        const f = gv.querySelectorAll('button:not([disabled]), a[href], input, select, textarea, [tabindex]:not([tabindex="-1"])');
        if (!f.length) return; const a = f[0], z = f[f.length - 1];
        if (e.shiftKey && document.activeElement === a) { e.preventDefault(); z.focus(); }
        else if (!e.shiftKey && document.activeElement === z) { e.preventDefault(); a.focus(); }
      }
    });
    gv.querySelector('.fechar').focus();
    if (location.hash !== '#/pedidos/' + id) history.replaceState(null, '', '#/pedidos/' + encodeURIComponent(id));
  }
  function fechar() {
    document.getElementById('gaveta-raiz').innerHTML = '';
    if (/^#\/pedidos\//.test(location.hash)) history.replaceState(null, '', '#/pedidos');
    if (abertoDe && document.body.contains(abertoDe)) abertoDe.focus();
    else if (mainRef) { const b = mainRef.querySelector('[data-id]'); if (b) b.focus(); }
  }
  function avancar(t) {
    const prox = M.proximoStatus(t);
    if (prox) {
      M.mudarStatus(t, prox);
      if (prox === 'Entregue' && !t.exemplo) t.valorFinal = Math.round(M.valorMedio(t));
      U.toast(t.id + ' → ' + prox + ' · automações disparadas');
    } else {
      const ev = t.eventos.find((e) => e.regra === 'posvenda' && e.estado === 'agendado');
      if (ev) {
        ev.estado = 'enviado'; ev.ts = Date.now();
        t.chat.push({ de: 'auto', regra: 'posvenda', texto: ev.texto, ts: Date.now() });
        t.nps = 9; t.chat.push({ de: 'cliente', texto: 'Nota 9! Resolveram rápido. (resposta simulada)', ts: Date.now() + 1000 });
        U.toast('Pós-venda enviado e NPS registrado (simulado)');
      }
    }
    S().salvar();
  }

  function render(main, param) {
    mainRef = main; const seg = S().seg();
    main.innerHTML = `
      <div class="cab"><div><div class="olho">Passo 3 · Operação</div><h1>Pedidos e SLA</h1>
        <p>Todo atendimento vira um pedido com prazo. Os cartões mudam de cor quando o SLA entra em atenção (menos de 25% do prazo) ou estoura. Abra um pedido para ver a conversa e simular as próximas etapas.</p></div>
        <div class="linha"><span class="muted pequeno" id="pd-total"></span><a class="btn btn--tg btn--p" href="#/atendimento">+ Novo atendimento</a></div></div>
      ${U.faixaVivo()}
      <div class="filtros">
        <label class="campo">Buscar<input class="inp" id="pd-busca" type="search" placeholder="Nome, pedido, placa…" value="${U.esc(filtro.busca)}"></label>
        <label class="campo">Prioridade<select class="inp" id="pd-prio"><option value="">Todas</option>${Object.entries(S().dados.prioridades).map(([k, v]) => '<option value="' + k + '"' + (filtro.prio === k ? ' selected' : '') + '>' + v + '</option>').join('')}</select></label>
        <label class="campo">SLA<select class="inp" id="pd-sla"><option value="">Todos</option><option value="ok"${filtro.sla === 'ok' ? ' selected' : ''}>No prazo</option><option value="atencao"${filtro.sla === 'atencao' ? ' selected' : ''}>Atenção</option><option value="erro"${filtro.sla === 'erro' ? ' selected' : ''}>Estourado</option></select></label>
        <div class="seg" role="group" aria-label="Modo de visualização" style="margin-left:auto">
          <button type="button" class="seg__btn" data-modo="kanban" aria-pressed="${filtro.modo === 'kanban'}">Kanban</button>
          <button type="button" class="seg__btn" data-modo="lista" aria-pressed="${filtro.modo === 'lista'}">Lista</button></div>
      </div>
      <div id="pd-area"></div>
      <p class="pequeno muted" style="margin-top:12px">Pedidos marcados como "exemplo" são fictícios. ${seg === 'oficina' ? 'Oficina' : 'Loja'}: troque o segmento no topo para ver o outro quadro.</p>`;
    main.querySelector('#pd-busca').addEventListener('input', U.debounce((e) => { filtro.busca = e.target.value; desenharQuadro(); }, 200));
    main.querySelector('#pd-prio').addEventListener('change', (e) => { filtro.prio = e.target.value; desenharQuadro(); });
    main.querySelector('#pd-sla').addEventListener('change', (e) => { filtro.sla = e.target.value; desenharQuadro(); });
    main.querySelectorAll('[data-modo]').forEach((b) => b.addEventListener('click', () => {
      filtro.modo = b.dataset.modo; main.querySelectorAll('[data-modo]').forEach((x) => x.setAttribute('aria-pressed', x === b)); desenharQuadro();
    }));
    desenharQuadro();
    if (param) { const t = S().ticket(decodeURIComponent(param)); if (t) abrir(t.id); }
  }
  let assinatura = '';
  function tick() {
    if (mainRef && document.body.contains(mainRef.querySelector('#pd-area')) && AT.S.vivoAtivo()) {
      const a = JSON.stringify(AT.S.vivo.pedidos.map((t) => t.id + t.status + (t.chat || []).length));
      if (a !== assinatura) { assinatura = a; const f = document.activeElement; desenharQuadro(); if (f && f.id && document.getElementById(f.id)) document.getElementById(f.id).focus(); }
    }
    document.querySelectorAll('[data-sla]').forEach((el) => {
      const t = S().ticket(el.dataset.sla); if (!t) return; const s = M.slaEstado(t);
      el.className = 'chip chip--' + s.cls; el.textContent = '⏱️ ' + s.texto;
    });
  }
  AT.V = AT.V || {};
  AT.V.pedidos = { titulo: 'Pedidos', render, _tick: tick };
})(window.AT);
