/* Atende AI — dashboard (SVG inline, sem bibliotecas) */
(function (AT) {
  'use strict';
  const U = AT.U, M = AT.M;
  const S = () => AT.S;
  const f = { periodo: '30', status: '' };
  const DIA = 86400000;

  function base() {
    const ini = f.periodo === 'todos' ? 0 : Date.now() - (+f.periodo) * DIA;
    return S().ticketsSeg().filter((t) => t.criado >= ini && (!f.status || t.status === f.status));
  }
  const passou = (t, st) => t.historico.some((h) => h.status === st);

  function kpis(l) {
    const orc = l.filter((t) => passou(t, 'Orçado')), apr = l.filter((t) => passou(t, 'Aprovado'));
    const resp = l.length ? l.reduce((a, t) => a + (t.tempoRespostaSeg || 0), 0) / l.length : 0;
    const concl = l.filter((t) => t.prontoEm), noPrazo = concl.filter((t) => t.prontoEm <= t.prazo);
    const estourados = l.filter((t) => !t.prontoEm && t.prazo < Date.now());
    const slaDen = concl.length + estourados.length;
    const abertos = l.filter((t) => ['Orçado', 'Aprovado', 'Em serviço', 'Pronto'].includes(t.status));
    const previsto = abertos.reduce((a, t) => a + M.valorMedio(t), 0);
    const entregues = l.filter((t) => t.status === 'Entregue');
    const realizado = entregues.reduce((a, t) => a + (t.valorFinal || M.valorMedio(t)), 0);
    const notas = l.filter((t) => t.nps != null).map((t) => t.nps);
    const nps = notas.length ? Math.round(((notas.filter((n) => n >= 9).length - notas.filter((n) => n <= 6).length) / notas.length) * 100) : null;
    const auto = l.filter((t) => !t.humano).length;
    return [
      ['Atendimentos', String(l.length), auto + ' resolvidos sem atendente'],
      ['Taxa de aprovação', orc.length ? Math.round((apr.length / orc.length) * 100) + '%' : '—', apr.length + ' de ' + orc.length + ' orçamentos'],
      ['Tempo médio de 1ª resposta', l.length ? U.tempoResp(resp) : '—', 'meta: até ' + S().st.sla[S().seg()].media.respostaMin + ' min'],
      ['SLA cumprido', slaDen ? Math.round((noPrazo.length / slaDen) * 100) + '%' : '—', noPrazo.length + ' no prazo · ' + (slaDen - noPrazo.length) + ' fora'],
      ['Faturamento previsto', U.brl(previsto), abertos.length + ' pedidos em aberto (valor médio)'],
      ['Faturamento realizado', U.brl(realizado), entregues.length + ' entregues'],
      ['Ticket médio', entregues.length ? U.brl(realizado / entregues.length) : '—', 'pedidos entregues'],
      ['NPS', nps == null ? '—' : String(nps), notas.length + ' respostas de pós-venda']
    ];
  }

  function barrasH(dados, fmt, cor) {
    if (!dados.length) return '<p class="muted pequeno">Sem dados no filtro.</p>';
    const max = Math.max(...dados.map((d) => d.valor), 1), h = 34, W = 480, L = 180;
    const linhas = dados.map((d, i) => {
      const w = Math.max(2, ((W - L - 70) * d.valor) / max); const y = i * h + 6;
      const rot = d.rotulo.length > 22 ? d.rotulo.slice(0, 21) + '…' : d.rotulo;
      return '<text x="0" y="' + (y + 16) + '">' + U.esc(rot) + '</text><rect x="' + L + '" y="' + (y + 2) + '" width="' + w + '" height="20" rx="5" fill="' + (d.cor || cor) + '"/><text class="val" x="' + (L + w + 8) + '" y="' + (y + 16) + '">' + U.esc(fmt(d.valor, d)) + '</text>';
    }).join('');
    return '<svg viewBox="0 0 ' + W + ' ' + (dados.length * h + 8) + '" role="img" aria-label="' + U.esc(dados.map((d) => d.rotulo + ': ' + fmt(d.valor, d)).join('; ')) + '">' + linhas + '</svg>';
  }
  function colunasDia(l) {
    const dias = f.periodo === 'todos' ? 30 : Math.min(+f.periodo, 90);
    const hoje = new Date(); hoje.setHours(0, 0, 0, 0);
    const serie = []; for (let i = dias - 1; i >= 0; i--) { const d = hoje.getTime() - i * DIA; serie.push({ d, n: 0, ap: 0 }); }
    l.forEach((t) => { const d0 = new Date(t.criado); d0.setHours(0, 0, 0, 0); const s = serie.find((x) => x.d === d0.getTime()); if (s) { s.n++; if (passou(t, 'Aprovado')) s.ap++; } });
    const W = 560, H = 200, P = 26, max = Math.max(2, ...serie.map((s) => s.n)); const bw = (W - P) / serie.length;
    const passo = Math.ceil(serie.length / 8);
    let svg = '<line x1="' + P + '" y1="' + (H - 22) + '" x2="' + W + '" y2="' + (H - 22) + '" stroke="#24314F"/>';
    for (let k = 0; k <= max; k += Math.max(1, Math.ceil(max / 4))) { const y = H - 22 - (k / max) * (H - 40); svg += '<text x="0" y="' + (y + 4) + '">' + k + '</text><line x1="' + P + '" x2="' + W + '" y1="' + y + '" y2="' + y + '" stroke="#1a2440" stroke-dasharray="3 4"/>'; }
    serie.forEach((s, i) => {
      const x = P + i * bw + 2, hh = (s.n / max) * (H - 40), ha = (s.ap / max) * (H - 40);
      if (s.n) svg += '<rect x="' + x + '" y="' + (H - 22 - hh) + '" width="' + Math.max(2, bw - 4) + '" height="' + hh + '" rx="3" fill="#8B86B8"><title>' + U.dataCurta(s.d) + ': ' + s.n + ' atendimento(s), ' + s.ap + ' aprovado(s)</title></rect>';
      if (s.ap) svg += '<rect x="' + x + '" y="' + (H - 22 - ha) + '" width="' + Math.max(2, bw - 4) + '" height="' + ha + '" rx="3" fill="#6EA8FF"/>';
      if (i % passo === 0 || i === serie.length - 1) svg += '<text x="' + (x + bw / 2 - 14) + '" y="' + (H - 4) + '">' + U.dataCurta(s.d) + '</text>';
    });
    const total = serie.reduce((a, s) => a + s.n, 0);
    return '<svg viewBox="0 0 ' + W + ' ' + H + '" role="img" aria-label="Atendimentos por dia: ' + total + ' no período">' + svg + '</svg><div class="legenda"><span><i style="background:#8B86B8"></i>Atendimentos</span><span><i style="background:#6EA8FF"></i>Aprovados</span></div>';
  }

  function desenhar(main) {
    const l = base();
    main.querySelector('#db-kpis').innerHTML = kpis(l).map(([r, v, s]) => '<div class="kpi"><div class="kpi__rot">' + r + '</div><div class="kpi__val">' + v + '</div><div class="kpi__sub">' + s + '</div></div>').join('');
    main.querySelector('#db-dias').innerHTML = colunasDia(l);
    const funil = S().dados.status.map((st) => ({ rotulo: st, valor: l.filter((t) => passou(t, st)).length }));
    const topo = funil[0].valor || 1;
    main.querySelector('#db-funil').innerHTML = barrasH(funil, (v) => v + ' (' + Math.round((v / topo) * 100) + '%)', '#6EA8FF');
    const cont = {}; l.forEach((t) => (t.itens || []).forEach((i) => { cont[i.nome] = (cont[i.nome] || 0) + 1; }));
    const top = Object.entries(cont).sort((a, b) => b[1] - a[1]).slice(0, 7).map(([rotulo, valor]) => ({ rotulo, valor }));
    main.querySelector('#db-serv').innerHTML = barrasH(top, (v) => v + 'x', '#8B86B8');
    const est = { ok: 0, atencao: 0, erro: 0 };
    l.forEach((t) => { const s = M.slaEstado(t); est[s.cls]++; });
    main.querySelector('#db-sla').innerHTML = barrasH([
      { rotulo: 'No prazo / cumprido', valor: est.ok, cor: '#4ADE80' }, { rotulo: 'Atenção (<25% do prazo)', valor: est.atencao, cor: '#FBBF24' }, { rotulo: 'Estourado', valor: est.erro, cor: '#F87171' }
    ], (v) => String(v), '#6EA8FF');
    const risco = l.filter((t) => { const s = M.slaEstado(t); return s.ativo && s.cls !== 'ok'; }).sort((a, b) => a.prazo - b.prazo);
    main.querySelector('#db-risco').innerHTML = risco.length ? '<div class="tabela-wrap"><table><thead><tr><th>Pedido</th><th>Cliente</th><th>Status</th><th>SLA</th></tr></thead><tbody>' +
      risco.map((t) => { const s = M.slaEstado(t); return '<tr><td><a href="#/pedidos/' + encodeURIComponent(t.id) + '">' + U.esc(t.id) + '</a></td><td>' + U.esc(t.cliente) + '</td><td>' + U.esc(t.status) + '</td><td><span class="chip chip--' + s.cls + '">' + U.esc(s.texto) + '</span></td></tr>'; }).join('') + '</tbody></table></div>'
      : '<p class="muted pequeno">Nenhum pedido em risco no filtro. 👏</p>';
    main.querySelector('#db-legenda').textContent = l.length + ' pedido(s) no filtro · ' + (S().vivoAtivo() ? 'dados ao vivo do bot de teste' : l.filter((t) => t.exemplo).length + ' de exemplo');
  }

  function csv() {
    const l = base(); const rot = S().segDef().rotulos;
    const cab = ['pedido', 'exemplo', 'canal', 'aberto_em', 'cliente', 'telefone', 'veiculo', 'placa', 'entrega', 'relato', 'servicos', 'status', 'prioridade', 'total_min', 'total_max', 'valor_cobrado', 'prazo_sla', 'sla', 'primeira_resposta_seg', 'atendente_humano', 'nps'];
    const q = (v) => '"' + String(v == null ? '' : v).replace(/"/g, '""') + '"';
    const linhas = l.map((t) => [t.id, t.exemplo ? 'sim' : 'não', t.canal || '', new Date(t.criado).toLocaleString('pt-BR'), t.cliente, t.telefone, t.veiculo, t.placa, t.bairro, t.problema,
      (t.itens || []).map((i) => i.nome).join(' + '), t.status, t.prioridade, t.total ? t.total.min : '', t.total ? t.total.max : '', t.valorFinal || '', new Date(t.prazo).toLocaleString('pt-BR'), M.slaEstado(t).texto, t.tempoRespostaSeg, t.humano ? 'sim' : 'não', t.nps == null ? '' : t.nps].map(q).join(';'));
    U.baixar('atende-ai-' + S().seg() + '-pedidos.csv', '\ufeff' + cab.join(';') + '\n' + linhas.join('\n'), 'text/csv;charset=utf-8');
    U.toast('CSV exportado (' + l.length + ' linhas). ' + rot.pecas + '/' + rot.mao + ' somados no total.');
  }

  function render(main) {
    main.innerHTML = `
      <div class="cab"><div><div class="olho">Passo 4 · Gestão</div><h1>Dashboard de ${S().seg() === 'oficina' ? 'atendimento da oficina' : 'atendimento da loja'}</h1><p id="db-legenda"></p></div>
        <button type="button" class="btn" id="db-csv">⬇️ Exportar CSV</button></div>
      ${U.faixaVivo()}
      <div class="filtros">
        <label class="campo">Período<select class="inp" id="db-periodo">${[['7', 'Últimos 7 dias'], ['30', 'Últimos 30 dias'], ['90', 'Últimos 90 dias'], ['todos', 'Tudo']].map(([v, r]) => '<option value="' + v + '"' + (f.periodo === v ? ' selected' : '') + '>' + r + '</option>').join('')}</select></label>
        <label class="campo">Status<select class="inp" id="db-status"><option value="">Todos</option>${S().dados.status.map((s) => '<option' + (f.status === s ? ' selected' : '') + '>' + s + '</option>').join('')}</select></label>
      </div>
      <section aria-label="Indicadores"><div class="kpis" id="db-kpis"></div></section>
      <div class="graficos">
        <section class="card grafico"><h2>Atendimentos por dia</h2><div id="db-dias"></div></section>
        <section class="card grafico"><h2>Funil do atendimento</h2><div id="db-funil"></div></section>
        <section class="card grafico"><h2>Serviços mais pedidos</h2><div id="db-serv"></div></section>
        <section class="card grafico"><h2>Situação do SLA</h2><div id="db-sla"></div></section>
      </div>
      <section class="card" style="margin-top:16px"><h2>Pedidos em risco de SLA</h2><div id="db-risco"></div></section>`;
    main.querySelector('#db-periodo').addEventListener('change', (e) => { f.periodo = e.target.value; desenhar(main); });
    main.querySelector('#db-status').addEventListener('change', (e) => { f.status = e.target.value; desenhar(main); });
    main.querySelector('#db-csv').addEventListener('click', csv);
    desenhar(main);
    AT.V.dashboard._tick = () => { if (document.body.contains(main.querySelector('#db-kpis'))) desenhar(main); };
  }
  AT.V = AT.V || {};
  AT.V.dashboard = { titulo: 'Dashboard', render };
})(window.AT);
