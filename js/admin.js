/* Atende AI — Modo plataforma (#/admin): visão do dono da plataforma sobre todas as lojas */
(function (AT) {
  'use strict';
  const U = AT.U;
  const CHAVE = 'atende-ai-admin-cx';
  const DIA = 86400000;
  const SEG = { oficina: ['🔧', 'Oficina'], loja: ['🏬', 'Loja'], ecommerce: ['🛒', 'Loja virtual'] };
  const A = { dados: null, erro: null, vivo: false, carregando: false };

  // link do bot (/admin_conectar): ?api=...&admin=CHAVE#/admin → guarda e tira a chave da barra de endereço
  (function lerUrl() {
    const q = new URLSearchParams(location.search);
    if (q.get('api') && q.get('admin')) {
      localStorage.setItem(CHAVE, JSON.stringify({ api: q.get('api').replace(/\/+$/, ''), chave: q.get('admin') }));
      history.replaceState(null, '', location.pathname + (location.hash || '#/admin'));
    }
  })();
  const conexao = () => { try { return JSON.parse(localStorage.getItem(CHAVE) || 'null'); } catch (e) { return null; } };

  async function atualizar() {
    const cx = conexao();
    if (!cx) { A.vivo = false; A.erro = null; A.dados = demo(); return; }
    A.carregando = true;
    try {
      const r = await fetch(cx.api + '/api/admin/export', { headers: { 'X-Atende-Admin': cx.chave }, cache: 'no-store' });
      if (!r.ok) throw new Error(r.status === 401 ? 'chave de administrador inválida' : 'HTTP ' + r.status);
      A.dados = await r.json(); A.vivo = true; A.erro = null;
    } catch (e) {
      A.vivo = false; A.erro = e.message === 'Failed to fetch' ? 'servidor de teste fora do ar ou endereço antigo' : e.message; A.dados = demo();
    } finally { A.carregando = false; }
  }

  // ------------------------------------------------------------ dados de demonstração (fictícios)
  function demo() {
    const agora = Date.now();
    let semente = 7;
    const rnd = () => { semente = (semente * 9301 + 49297) % 233280; return semente / 233280; };
    const base = [
      { id: 'loja-do-mano', nome: 'Loja do Mano', segmento: 'ecommerce', piloto: true, donos: 1, dias: 18, conv: 214, ped: 61, cvt: 37, fat: 9480, resp: 2, nps: [41, 12], antes: { respostaMin: 150, vendasMes: 7200, pedidosMes: 28 } },
      { id: 'auto-center-silva', nome: 'Auto Center Silva', segmento: 'oficina', piloto: true, donos: 2, dias: 25, conv: 168, ped: 74, cvt: 49, fat: 31650, resp: 3, nps: [33, 8], antes: { respostaMin: 95, vendasMes: 26800, pedidosMes: 52 } },
      { id: 'bella-moda-online', nome: 'Bella Moda Online', segmento: 'ecommerce', piloto: false, donos: 1, dias: 9, conv: 96, ped: 22, cvt: 11, fat: 2310, resp: 2, nps: [8, 3], antes: {} },
      { id: 'casa-forte', nome: 'Casa Forte Materiais', segmento: 'loja', piloto: false, donos: 1, dias: 30, conv: 131, ped: 58, cvt: 31, fat: 14920, resp: 4, nps: [19, 6], antes: {} },
      { id: 'pet-shop-amigo', nome: 'Pet Shop Amigo', segmento: 'loja', piloto: false, donos: 0, dias: 3, conv: 12, ped: 4, cvt: 1, fat: 180, resp: 3, nps: [0, 0], antes: {}, parada: true },
      { id: 'loja-exemplo-online', nome: 'Loja Exemplo Online', segmento: 'ecommerce', exemplo: true, piloto: false, donos: 0, dias: 30, conv: 47, ped: 9, cvt: 0, fat: 0, resp: 1, nps: [0, 0], antes: {} }
    ];
    const lojas = base.map((b, i) => {
      const atividade = {};
      for (let d = 29; d >= 0; d--) {
        if (b.parada && d < 9) continue;
        const ativo = d < b.dias && rnd() > 0.15;
        if (!ativo) continue;
        const k = new Date(agora - d * DIA).toISOString().slice(0, 10);
        atividade[k] = { cli: Math.round(b.conv / b.dias * (0.6 + rnd()) * 3), dono: Math.round(rnd() * 9) };
      }
      const msgs = Object.values(atividade).reduce((s, v) => s + v.cli + v.dono, 0);
      const st = { ecommerce: ['Aguardando pagamento', 'Pago', 'Separando', 'Enviado', 'Entregue'], oficina: ['Orçado', 'Aprovado', 'Em serviço', 'Pronto', 'Entregue'], loja: ['Orçado', 'Aprovado', 'Em serviço', 'Pronto', 'Entregue'] }[b.segmento];
      const pref = { ecommerce: 'EC-', oficina: 'OF-', loja: 'LJ-' }[b.segmento];
      const recentes = b.ped ? Array.from({ length: 6 }, (_, j) => ({ id: pref + (4100 + i * 40 + 6 - j), tipo: 'pedido', status: st[Math.floor(rnd() * st.length)], criado: agora - (j * 7 + rnd() * 5) * 3600000,
        valor: Math.round((b.fat / Math.max(1, b.cvt)) * (0.5 + rnd())), sla: rnd() > 0.85 ? 'atencao' : 'ok', humano: rnd() > 0.8, nps5: rnd() > 0.7 ? 5 : null, canal: 'telegram' })) : [];
      const n = b.nps[0] + b.nps[1];
      const nps = n ? { n, nps: Math.round(((b.nps[0] * 0.75) - b.nps[1] * 0.5) / n * 100), media: Math.round((4.2 + rnd() * 0.6) * 10) / 10 } : { n: 0, nps: null, media: null };
      const ult = Object.keys(atividade).sort().pop();
      return { id: b.id, nome: b.nome, segmento: b.segmento, exemplo: !!b.exemplo, piloto: b.piloto, donos: b.donos, criado: agora - b.dias * DIA, conversas: b.conv, pedidos: b.ped, convertidos: b.cvt,
        conversao: b.conv ? Math.round(b.cvt / b.conv * 100) : null, faturamento: b.fat, tempoRespostaSeg: b.resp, ultimaAtividade: ult ? new Date(ult + 'T12:00:00').getTime() + Math.round(rnd() * 5 * 3600000) : agora - 12 * DIA,
        termoAceitoEm: b.exemplo || !b.donos ? null : agora - b.dias * DIA, exclusaoSolicitadaEm: null, nps,
        saude: { piloto: b.piloto, inicio: agora - Math.min(b.dias, 21) * DIA, dias: Math.min(b.dias, 21), dias_ativos: Object.keys(atividade).filter((k) => k >= new Date(agora - Math.min(b.dias, 21) * DIA).toISOString().slice(0, 10)).length,
          mensagens: msgs, mensagens_dia: Math.round(msgs / Math.max(1, Math.min(b.dias, 30)) * 10) / 10, pedidos: b.ped, convertidos: b.cvt, nps, antes: b.antes,
          depois: { respostaBotSeg: b.resp, respostaHumanaMin: Math.round((6 + rnd() * 20) * 10) / 10, vendas30d: b.fat, pedidos30d: b.ped } },
        recentes, atividade };
    });
    return { plataforma: agregar(lojas, agora), lojas, geradoEm: agora, demo: true };
  }
  function agregar(lojas, agora) {
    const reais = lojas.filter((l) => !l.exemplo);
    const conv = lojas.reduce((s, l) => s + l.conversas, 0), cvt = lojas.reduce((s, l) => s + l.convertidos, 0);
    const resp = lojas.filter((l) => l.tempoRespostaSeg != null);
    const n = lojas.reduce((s, l) => s + (l.nps.n || 0), 0);
    return { lojas: lojas.length, lojas_reais: reais.length, lojas_ativas_7d: lojas.filter((l) => l.ultimaAtividade >= agora - 7 * DIA).length, pilotos: lojas.filter((l) => l.piloto).length,
      conversas: conv, pedidos: lojas.reduce((s, l) => s + l.pedidos, 0), convertidos: cvt, conversao: conv ? Math.round(cvt / conv * 100) : null,
      faturamento_intermediado: lojas.reduce((s, l) => s + l.faturamento, 0), faturamento_lojas_reais: reais.reduce((s, l) => s + l.faturamento, 0),
      tempoRespostaSeg: resp.length ? Math.round(resp.reduce((s, l) => s + l.tempoRespostaSeg, 0) / resp.length) : null,
      nps: { n, nps: n ? Math.round(lojas.reduce((s, l) => s + (l.nps.nps || 0) * (l.nps.n || 0), 0) / n) : null }, geradoEm: agora };
  }

  // ------------------------------------------------------------ formatação
  const brl2 = new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' });
  const din = (v) => brl2.format(v || 0);
  const pct = (v) => (v == null ? '—' : v + '%');
  const seg = (s) => (SEG[s] || ['🏬', s]);
  const resp = (s) => (s == null ? '—' : U.tempoResp(s));
  const npsTxt = (n) => (n && n.nps != null ? String(n.nps) : '—');
  const dec = (v) => (v == null ? '—' : String(v).replace('.', ','));
  const kpi = (r, v, s) => '<div class="kpi"><div class="kpi__rot">' + r + '</div><div class="kpi__val">' + v + '</div><div class="kpi__sub">' + s + '</div></div>';

  function faixa() {
    const cx = conexao();
    if (A.vivo && cx) return '<div class="vivo" role="status"><strong>🟢 Modo plataforma ao vivo</strong> · dados do bot de teste ' + U.esc(cx.api.replace('https://', '')) + ' · atualizado às ' + U.hora(A.dados.geradoEm) + ' (a cada 30 s) · <button type="button" class="link-btn" id="adm-sair">desconectar</button></div>';
    if (cx && A.erro) return '<div class="vivo vivo--erro" role="status"><strong>⚠️ Não foi possível ler a API de administração</strong> (' + U.esc(A.erro) + '). Mostrando <strong>dados de demonstração</strong>. Peça <code>/admin_conectar</code> de novo no bot · <button type="button" class="link-btn" id="adm-sair">desconectar</button></div>';
    return '<div class="vivo vivo--demo" role="status"><strong>🧪 Dados de demonstração (fictícios).</strong> Para ver as lojas reais: no <a href="https://t.me/Applojas10_bot">@Applojas10_bot</a> envie <code>/admin SEU_CÓDIGO</code> e depois <code>/admin_conectar</code>, ou preencha abaixo.</div>';
  }

  function tabelaLojas(lojas, sel) {
    const ord = lojas.slice().sort((a, b) => (b.piloto - a.piloto) || (b.ultimaAtividade - a.ultimaAtividade));
    return '<div class="tabela-wrap"><table class="adm-tab"><caption class="sr">Todas as lojas da plataforma</caption><thead><tr><th scope="col">Loja</th><th scope="col">Segmento</th><th scope="col" class="num">Donos</th><th scope="col" class="num">Conversas</th><th scope="col" class="num">Pedidos</th><th scope="col" class="num">Conversão</th><th scope="col" class="num">Faturamento</th><th scope="col">Última atividade</th><th scope="col"><span class="sr">Ações</span></th></tr></thead><tbody>' +
      ord.map((l) => '<tr' + (l.id === sel ? ' aria-current="true" class="sel"' : '') + '><th scope="row"><strong>' + U.esc(l.nome) + '</strong><div class="pequeno muted"><code>' + U.esc(l.id) + '</code>' +
        (l.piloto ? ' <span class="chip chip--azul">🧪 piloto</span>' : '') + (l.exemplo ? ' <span class="chip chip--exemplo">exemplo</span>' : '') + (l.exclusaoSolicitadaEm ? ' <span class="chip chip--erro">exclusão pedida</span>' : '') + '</div></th>' +
        '<td>' + seg(l.segmento).join(' ') + '</td><td class="num">' + l.donos + '</td><td class="num">' + l.conversas + '</td><td class="num">' + l.pedidos + '</td><td class="num">' + pct(l.conversao) + '</td><td class="num">' + din(l.faturamento) + '</td>' +
        '<td>' + U.dataHora(l.ultimaAtividade) + (Date.now() - l.ultimaAtividade > 7 * DIA ? ' <span class="chip chip--atencao">parada</span>' : '') + '</td>' +
        '<td><a class="btn btn--p" href="#/admin/' + encodeURIComponent(l.id) + '" aria-label="Ver detalhes de ' + U.esc(l.nome) + '">Ver</a></td></tr>').join('') + '</tbody></table></div>';
  }

  function barras(atividade) {
    const dias = []; const agora = Date.now();
    for (let d = 29; d >= 0; d--) { const k = new Date(agora - d * DIA).toISOString().slice(0, 10); const v = atividade[k] || { cli: 0, dono: 0 }; dias.push([k, v.cli + v.dono]); }
    const max = Math.max(1, ...dias.map((x) => x[1]));
    return '<div class="adm-barras" role="img" aria-label="Mensagens por dia nos últimos 30 dias; máximo de ' + max + ' em um dia">' +
      dias.map(([k, v]) => '<span style="--h:' + Math.round(v / max * 100) + '%" title="' + k.split('-').reverse().slice(0, 2).join('/') + ': ' + v + ' mensagens"></span>').join('') + '</div><div class="pequeno muted adm-eixo"><span>há 30 dias</span><span>hoje</span></div>';
  }

  function detalhe(l) {
    const s = l.saude || {}; const a = s.antes || {}; const d = s.depois || {};
    const ganhoResp = a.respostaMin != null && d.respostaBotSeg != null ? Math.round((a.respostaMin * 60) / Math.max(1, d.respostaBotSeg)) : null;
    const ganhoVendas = a.vendasMes ? Math.round((d.vendas30d - a.vendasMes) / a.vendasMes * 100) : null;
    return '<section class="card adm-det" aria-labelledby="adm-det-t" id="adm-det"><div class="cab cab--p"><div><div class="olho">' + seg(l.segmento).join(' ') + (l.piloto ? ' · 🧪 piloto' : '') + '</div><h2 id="adm-det-t">' + U.esc(l.nome) + '</h2>' +
      '<p class="pequeno">Slug <code>' + U.esc(l.id) + '</code> · criada ' + U.dataCurta(l.criado || Date.now()) + ' · donos: ' + l.donos + ' · termo do piloto: ' + (l.termoAceitoEm ? 'aceito em ' + U.dataHora(l.termoAceitoEm) : 'não aceito') + '</p></div>' +
      '<a class="btn btn--p" href="#/admin">Fechar</a></div>' +
      '<div class="kpis">' + kpi('Conversas', l.conversas, 'clientes que falaram com o bot') + kpi('Pedidos', l.pedidos, l.convertidos + ' convertidos · ' + pct(l.conversao)) + kpi('Faturamento', din(l.faturamento), l.segmento === 'ecommerce' ? 'pedidos pagos' : 'serviços entregues') + kpi('1ª resposta', resp(l.tempoRespostaSeg), 'média do bot') + '</div>' +
      '<h3>Saúde do piloto</h3><div class="kpis">' + kpi('Dias ativos', (s.dias_ativos || 0) + '/' + (s.dias || 0), 'desde ' + U.dataCurta(s.inicio || Date.now())) + kpi('Mensagens/dia', dec(s.mensagens_dia), (s.mensagens || 0) + ' no período') + kpi('Pedidos no piloto', s.pedidos || 0, (s.convertidos || 0) + ' convertidos') + kpi('NPS', npsTxt(s.nps), s.nps && s.nps.n ? s.nps.n + ' avaliações · média ' + dec(s.nps.media) + '/5' : 'sem avaliações ainda') + '</div>' +
      barras(l.atividade || {}) +
      '<h3>Antes × depois (para o case)</h3><div class="tabela-wrap"><table><caption class="sr">Comparação antes e depois do Atende AI</caption><thead><tr><th scope="col">Indicador</th><th scope="col">Antes (informado pelo dono)</th><th scope="col">Com o Atende AI</th></tr></thead><tbody>' +
      '<tr><th scope="row">Tempo para responder um cliente</th><td>' + (a.respostaMin != null ? U.dur(a.respostaMin) : '<span class="muted">não informado</span>') + '</td><td>' + resp(d.respostaBotSeg) + ' (bot) · ' + (d.respostaHumanaMin != null ? dec(d.respostaHumanaMin) + ' min (equipe, quando chamada)' : 'equipe: —') + (ganhoResp ? ' <span class="chip chip--ok">' + ganhoResp + '× mais rápido</span>' : '') + '</td></tr>' +
      '<tr><th scope="row">Vendas por mês</th><td>' + (a.vendasMes != null ? din(a.vendasMes) : '<span class="muted">não informado</span>') + '</td><td>' + din(d.vendas30d) + ' (últimos 30 dias)' + (ganhoVendas != null ? ' <span class="chip ' + (ganhoVendas >= 0 ? 'chip--ok' : 'chip--atencao') + '">' + (ganhoVendas >= 0 ? '+' : '') + ganhoVendas + '%</span>' : '') + '</td></tr>' +
      '<tr><th scope="row">Pedidos por mês</th><td>' + (a.pedidosMes != null ? a.pedidosMes : '<span class="muted">não informado</span>') + '</td><td>' + (d.pedidos30d || 0) + ' (últimos 30 dias)</td></tr></tbody></table></div>' +
      '<p class="pequeno muted">O dono preenche o “antes” no bot com <code>/antes resposta 2h vendas R$ 8.000 pedidos 40</code>. Marcar como piloto: <code>/piloto ' + U.esc(l.id) + '</code>.</p>' +
      '<h3>Pedidos recentes</h3>' + ((l.recentes || []).length ? '<div class="tabela-wrap"><table><caption class="sr">Pedidos recentes, sem dados pessoais</caption><thead><tr><th scope="col">Pedido</th><th scope="col">Tipo</th><th scope="col">Status</th><th scope="col" class="num">Valor</th><th scope="col">Aberto</th><th scope="col">SLA</th></tr></thead><tbody>' +
        l.recentes.map((t) => '<tr><th scope="row">' + U.esc(t.id) + '</th><td>' + U.esc(t.tipo) + (t.humano ? ' · 🙋' : '') + '</td><td>' + U.esc(t.status) + '</td><td class="num">' + (t.valor ? din(t.valor) : '—') + '</td><td>' + U.dataHora(t.criado) + '</td><td><span class="chip chip--' + (t.sla === 'erro' ? 'erro' : t.sla === 'atencao' ? 'atencao' : 'ok') + '">' + ({ ok: 'no prazo', atencao: 'atenção', erro: 'estourado' }[t.sla] || t.sla) + '</span></td></tr>').join('') + '</tbody></table></div>' : '<p class="muted">Nenhum pedido ainda.</p>') +
      '<p class="pequeno muted">Minimização de dados (LGPD): o operador da plataforma vê números, status e valores. Nomes, contatos, endereços e mensagens dos clientes ficam só com a loja.</p></section>';
  }

  function csv() {
    const q = (v) => '"' + String(v == null ? '' : v).replace(/"/g, '""') + '"';
    const cab = ['loja', 'slug', 'segmento', 'exemplo', 'piloto', 'donos', 'conversas', 'pedidos', 'convertidos', 'conversao_pct', 'faturamento', 'primeira_resposta_seg', 'ultima_atividade', 'termo_aceito_em', 'piloto_inicio', 'dias_ativos', 'mensagens_dia', 'nps', 'antes_resposta_min', 'antes_vendas_mes', 'antes_pedidos_mes', 'depois_vendas_30d', 'depois_pedidos_30d'];
    const linhas = A.dados.lojas.map((l) => { const s = l.saude || {}; const a = s.antes || {}; const d = s.depois || {}; return [l.nome, l.id, l.segmento, l.exemplo ? 'sim' : 'não', l.piloto ? 'sim' : 'não', l.donos, l.conversas, l.pedidos, l.convertidos, l.conversao, String(l.faturamento).replace('.', ','), l.tempoRespostaSeg,
      new Date(l.ultimaAtividade).toLocaleString('pt-BR'), l.termoAceitoEm ? new Date(l.termoAceitoEm).toLocaleString('pt-BR') : '', s.inicio ? new Date(s.inicio).toLocaleDateString('pt-BR') : '', s.dias_ativos, String(s.mensagens_dia == null ? '' : s.mensagens_dia).replace('.', ','), s.nps ? s.nps.nps : '', a.respostaMin, a.vendasMes, a.pedidosMes, d.vendas30d, d.pedidos30d].map(q).join(';'); });
    U.baixar('atende-ai-plataforma-lojas' + (A.dados.demo ? '-demonstracao' : '') + '.csv', '\ufeff' + cab.join(';') + '\n' + linhas.join('\n'), 'text/csv;charset=utf-8');
    U.toast('CSV exportado (' + linhas.length + ' lojas' + (A.dados.demo ? ', dados de demonstração' : '') + ').');
  }

  function desenhar(main, slug) {
    const p = A.dados.plataforma; const lojas = A.dados.lojas;
    main.querySelector('#adm-faixa').innerHTML = faixa();
    main.querySelector('#adm-kpis').innerHTML = kpi('Lojas ativas (7 dias)', p.lojas_ativas_7d + '/' + p.lojas, p.lojas_reais + ' reais · ' + p.pilotos + ' em piloto') + kpi('Conversas', p.conversas, 'clientes atendidos pelo bot') +
      kpi('Pedidos', p.pedidos, p.convertidos + ' convertidos') + kpi('Conversão', pct(p.conversao), 'conversa → pedido pago/aprovado') +
      kpi('Faturamento intermediado', din(p.faturamento_intermediado), 'lojas reais: ' + din(p.faturamento_lojas_reais)) + kpi('1ª resposta média', resp(p.tempoRespostaSeg), 'tempo do bot') +
      kpi('NPS', npsTxt(p.nps), (p.nps && p.nps.n) ? p.nps.n + ' avaliações' : 'sem avaliações') + kpi('Pilotos', p.pilotos, 'lojas acompanhadas para o case');
    main.querySelector('#adm-lojas').innerHTML = tabelaLojas(lojas, slug);
    const l = slug && lojas.find((x) => x.id === slug);
    main.querySelector('#adm-det-raiz').innerHTML = l ? detalhe(l) : (slug ? '<p class="card" role="alert">Loja <code>' + U.esc(slug) + '</code> não encontrada nestes dados.</p>' : '');
    const sair = main.querySelector('#adm-sair');
    if (sair) sair.addEventListener('click', async () => { localStorage.removeItem(CHAVE); await atualizar(); desenhar(main, slug); U.toast('Modo plataforma desconectado.'); });
    main.querySelector('#adm-form').hidden = A.vivo;
  }

  async function render(main, slug) {
    slug = slug ? decodeURIComponent(slug) : '';
    main.innerHTML = `
      <div class="cab"><div><div class="olho">Plataforma · byGui</div><h1>Modo plataforma</h1><p>Visão de quem opera o Atende AI: todas as lojas, indicadores globais e a saúde dos pilotos. Só abre dados reais com a chave de administrador.</p></div>
        <button type="button" class="btn" id="adm-csv">⬇️ Exportar CSV</button></div>
      <div id="adm-faixa"></div>
      <form class="card adm-form" id="adm-form" hidden>
        <h2 class="h3">Conectar à API de administração</h2>
        <div class="adm-form__campos">
          <label class="campo">Endereço da API<input class="inp" id="adm-api" type="url" placeholder="https://….trycloudflare.com" autocomplete="off" required></label>
          <label class="campo">Chave de administrador<input class="inp" id="adm-chave" type="password" autocomplete="off" required></label>
          <button class="btn btn--pri" type="submit">Conectar</button>
        </div>
        <p class="pequeno muted">O jeito mais fácil é tocar no link que o bot manda em <code>/admin_conectar</code>. A chave fica só neste navegador.</p>
      </form>
      <section aria-label="Indicadores globais"><div class="kpis" id="adm-kpis"></div></section>
      <section class="card" aria-labelledby="adm-lojas-t"><h2 id="adm-lojas-t">Lojas</h2><div id="adm-lojas"></div></section>
      <div id="adm-det-raiz"></div>`;
    if (!A.dados || A.vivo !== !!conexao() || (conexao() && A.erro)) await atualizar();
    desenhar(main, slug);
    if (slug) { const d = main.querySelector('#adm-det'); if (d) d.scrollIntoView({ block: 'start', behavior: U.reduzMov() ? 'auto' : 'smooth' }); }
    main.querySelector('#adm-csv').addEventListener('click', csv);
    main.querySelector('#adm-form').addEventListener('submit', async (e) => {
      e.preventDefault();
      localStorage.setItem(CHAVE, JSON.stringify({ api: main.querySelector('#adm-api').value.trim().replace(/\/+$/, ''), chave: main.querySelector('#adm-chave').value.trim() }));
      await atualizar(); desenhar(main, slug);
      U.toast(A.vivo ? 'Conectado: dados reais da plataforma.' : 'Não conectou: ' + A.erro);
    });
    AT.V.admin._tick = async () => { if (!document.body.contains(main.querySelector('#adm-kpis'))) return; if (conexao() || A.vivo) { await atualizar(); desenhar(main, slug); } };
  }
  AT.V = AT.V || {};
  AT.V.admin = { titulo: 'Modo plataforma', render };
  AT.Admin = { demo, agregar };
})(window.AT);
