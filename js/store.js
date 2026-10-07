/* Atende AI — estado local (localStorage) semeado a partir de dados.json */
(function (AT) {
  'use strict';
  const U = AT.U;
  const CHAVE = 'atendeai.v1';
  const S = { dados: null, st: null, ouvintes: [] };

  S.carregar = async function () {
    const r = await fetch('dados.json', { cache: 'no-cache' });
    if (!r.ok) throw new Error('Falha ao carregar dados.json');
    S.dados = await r.json();
    S.lerConexaoDaUrl();
    let salvo = null;
    try { salvo = JSON.parse(localStorage.getItem(CHAVE) || 'null'); } catch (e) { salvo = null; }
    if (salvo && salvo.versao === S.dados.versao && Array.isArray(salvo.tickets)) S.st = salvo;
    else S.st = S.semear();
    S.salvar();
  };

  S.semear = function () {
    const D = S.dados; const agora = Date.now();
    const st = {
      versao: D.versao, segmento: 'oficina', canal: 'telegram', seq: 2000,
      negocios: {}, catalogos: {}, automacoes: JSON.parse(JSON.stringify(D.automacoes)), sla: JSON.parse(JSON.stringify(D.sla)),
      tickets: [], conversas: {}, onboarding: {},
      politicas: { ecommerce: JSON.parse(JSON.stringify(D.segmentos.ecommerce.politicas)) },
      metricas: JSON.parse(JSON.stringify(D.metricasExemplo || {}))
    };
    Object.keys(D.segmentos).forEach((k) => {
      st.negocios[k] = JSON.parse(JSON.stringify(D.segmentos[k].negocio));
      st.catalogos[k] = JSON.parse(JSON.stringify(D.segmentos[k].catalogo));
    });
    S.st = st;
    D.ticketsExemplo.forEach((x) => st.tickets.push(S.ticketDeExemplo(x, agora)));
    return st;
  };

  /** Monta um ticket completo (chat, orçamento, automações) a partir do descritor compacto */
  S.ticketDeExemplo = function (x, agora) {
    if (x.seg === 'ecommerce') return S.ticketEcom(x, agora);
    const seg = x.seg; const M = AT.M;
    const criado = agora - x.criadoHaMin * 60000;
    const segDef = S.dados.segmentos[seg];
    const intent = segDef.intents.find((i) => i.id === x.intent);
    const t = {
      id: x.id, seg, exemplo: true, canal: 'telegram', cliente: x.cliente, telefone: x.telefone, veiculo: x.veiculo || '', placa: x.placa || '', bairro: x.bairro || '',
      problema: x.problema, intent: x.intent, servicos: x.servicos.slice(), opcionais: [], prioridade: x.prioridade, status: 'Novo',
      criado, humano: !!x.humano, tempoRespostaSeg: x.humano ? x.respostaHumanoSeg : x.respostaSeg, chat: [], eventos: [], historico: [{ status: 'Novo', ts: criado }]
    };
    const orc = M.orcamento(seg, t.servicos, t.veiculo, S.st.catalogos[seg]);
    t.itens = orc.itens; t.total = orc.total; t.ajuste = orc.ajuste;
    t.prazo = x.prazoEmMin != null ? agora + x.prazoEmMin * 60000 : M.calcPrazo(seg, t.prioridade, criado, orc.duracao);
    const s = t.tempoRespostaSeg * 1000;
    t.chat.push({ de: 'cliente', texto: x.problema, ts: criado });
    if (t.humano) {
      t.chat.push({ de: 'bot', texto: 'Entendi: ' + (intent ? intent.rotulo.toLowerCase() : 'seu problema') + '. Como você pediu, chamei um atendente da equipe.', ts: criado + 4000 });
      t.chat.push({ de: 'atendente', texto: 'Oi, ' + U.primeiroNome(t.cliente) + '! Aqui é o Wagner, da ' + S.st.negocios[seg].nome + '. Me manda sua localização que vejo se conseguimos um guincho.', ts: criado + s });
    } else {
      t.chat.push({ de: 'bot', texto: (intent ? intent.explicacao : 'Entendi.') + ' Vou montar seu orçamento.', ts: criado + s });
    }
    const ordem = S.dados.status; const alvo = ordem.indexOf(x.status);
    const total = t.prazo - criado;
    // linha do tempo distribuída entre a criação e agora
    const marcos = {
      'Orçado': criado + Math.max(s, 60000) + 30000,
      'Aprovado': criado + Math.min(total * 0.12, 3 * 3600000),
      'Em serviço': criado + Math.min(total * 0.3, 20 * 3600000),
      'Pronto': x.atrasou ? t.prazo + 50 * 60000 : criado + total * 0.8,
      'Entregue': (x.atrasou ? t.prazo + 50 * 60000 : criado + total * 0.8) + 2 * 3600000
    };
    for (let i = 1; i <= alvo; i++) {
      const st = ordem[i];
      let ts = Math.min(marcos[st], agora - (alvo - i + 1) * 4 * 60000);
      if (ts < criado) ts = criado + i * 60000;
      M.mudarStatus(t, st, ts, { silencioso: true });
    }
    if (x.status === 'Entregue') {
      t.nps = x.nps;
      t.valorFinal = Math.round(((t.total.min + t.total.max) / 2) * (0.95 + ((x.nps || 5) % 3) * 0.04));
      t.chat.push({ de: 'cliente', texto: 'Nota ' + x.nps + '. ' + (x.nps >= 9 ? 'Atendimento rápido, recomendo!' : x.nps >= 7 ? 'Bom, mas demorou um pouco.' : 'Resolveu, mas atrasou.'), ts: Math.min(agora, t.entregueEm + 26 * 3600000) });
    }
    return t;
  };

  /** Loja virtual: pedido (carrinho → pagamento → envio) ou troca, a partir do descritor compacto */
  S.ticketEcom = function (x, agora) {
    const E = AT.E, M = AT.M; const criado = agora - x.criadoHaMin * 60000;
    const pol = S.st.politicas.ecommerce; const cat = S.st.catalogos.ecommerce; const hor = S.st.negocios.ecommerce.horario;
    const carrinho = {}; (x.itens || []).forEach(([id, q]) => { carrinho[id] = q; });
    const regiao = E.regiaoCep(x.cep, x.uf);
    const r = E.resumo(cat, carrinho, pol, x.tipo === 'pedido' ? regiao : null, x.pagamento);
    const t = {
      id: x.id, seg: 'ecommerce', tipo: x.tipo, exemplo: true, canal: 'telegram', cliente: x.cliente, telefone: x.telefone || '', veiculo: '', placa: '', bairro: '',
      problema: x.problema, intent: x.intent, servicos: r.itens.map((i) => i.id), opcionais: [], itens: r.itens, prioridade: x.prioridade || 'media', status: 'Novo',
      criado, humano: !!x.humano, tempoRespostaSeg: x.respostaSeg || 5, chat: [], eventos: [], historico: [{ status: 'Novo', ts: criado }]
    };
    const s = t.tempoRespostaSeg * 1000;
    t.chat.push({ de: 'cliente', texto: x.problema, ts: criado });
    if (x.tipo === 'troca') {
      Object.assign(t, { motivo: x.motivo, pedidoRef: x.pedidoRef || '', total: { min: 0, max: 0 } });
      t.prazo = E.somaDiasUteis(criado, 2, hor);
      t.chat.push({ de: 'bot', texto: 'Abri a solicitação ' + t.id + ' (' + x.motivo + (x.pedidoRef ? ', pedido ' + x.pedidoRef : '') + '). Nossa política: ' + pol.troca, ts: criado + s });
      const ordemT = M.statusDe('ecommerce', 'troca');
      for (let i = 1; i <= ordemT.indexOf(x.status); i++) M.mudarStatus(t, ordemT[i], Math.min(agora - 60000, criado + i * 50 * 60000), { silencioso: true });
      if (x.status !== 'Novo') t.chat.push({ de: 'atendente', texto: 'Oi, ' + U.primeiroNome(t.cliente) + '! Já vi aqui. Vou te mandar a etiqueta de devolução e enviamos o tamanho certo assim que chegar.', ts: Math.min(agora - 50000, criado + 52 * 60000) });
      return t;
    }
    Object.assign(t, {
      subtotal: r.subtotal, frete: r.frete.valor, freteGratis: r.frete.gratis, freteDias: r.frete.dias, desconto: r.desconto, totalFinal: r.total, total: { min: r.total, max: r.total },
      pagamento: x.pagamento, cep: x.cep, cidade: x.cidade || '', uf: x.uf || '', regiao, endereco: x.endereco || 'Endereço de exemplo', rastreio: ''
    });
    t.prazo = E.somaDiasUteis(criado, E.envioDias(pol, t) + 1, hor);
    t.chat.push({ de: 'bot', texto: 'Encontrei: ' + E.itensTexto(r.itens) + '. Total com frete' + (r.desconto ? ' e desconto Pix' : '') + ': ' + E.brlC(r.total) + '.', ts: criado + s });
    const ordem = M.statusDe('ecommerce'); const alvo = ordem.indexOf(x.status);
    let ts = criado + Math.max(s, 60000) + 120000;
    for (let i = 1; i <= alvo; i++) {
      const st = ordem[i];
      if (st === 'Pago') ts = criado + Math.min(3 * 3600000, (agora - criado) * 0.15);
      if (st === 'Separando') ts = t.aprovadoEm + Math.min(4 * 3600000, (agora - t.aprovadoEm) * 0.3);
      if (st === 'Enviado') { t.rastreio = x.rastreio || M.rastreioExemplo(); ts = x.atrasou ? t.prazo + 3 * 3600000 : Math.min(t.prazo - 3600000, t.aprovadoEm + (t.prazo - t.aprovadoEm) * 0.6); }
      if (st === 'Entregue') ts += (t.freteDias || 4) * 86400000;
      ts = Math.min(ts, agora - (alvo - i + 1) * 4 * 60000); if (ts < criado) ts = criado + i * 60000;
      M.mudarStatus(t, st, ts, { silencioso: true });
    }
    if (x.prazoEmMin != null && !t.prontoEm) t.prazo = agora + x.prazoEmMin * 60000;
    if (x.status === 'Entregue') {
      t.nps = x.nps; t.valorFinal = t.totalFinal;
      t.chat.push({ de: 'cliente', texto: 'Nota ' + x.nps + '. ' + (x.nps >= 9 ? 'Chegou rápido e bem embalado!' : 'Chegou certinho, só demorou um pouco.'), ts: Math.min(agora, t.entregueEm + 26 * 3600000) });
    }
    return t;
  };

  /* ---------- modo conectado: lê pedidos ao vivo da API do bot de teste ---------- */
  const CHAVE_CX = 'atendeai.conexao';
  S.vivo = null; S.vivoErro = null;
  S.conexao = function () { try { return JSON.parse(localStorage.getItem(CHAVE_CX) || 'null'); } catch (e) { return null; } };
  S.lerConexaoDaUrl = function () {
    const q = new URLSearchParams(location.search);
    if (q.get('api') && q.get('negocio') && q.get('chave')) {
      localStorage.setItem(CHAVE_CX, JSON.stringify({ api: q.get('api').replace(/\/+$/, ''), negocio: q.get('negocio'), chave: q.get('chave') }));
      history.replaceState(null, '', location.pathname + location.hash); // tira a chave da barra de endereço
    }
  };
  S.conectar = function (cx) { localStorage.setItem(CHAVE_CX, JSON.stringify(cx)); return S.atualizarVivo(); };
  S.desconectar = function () { localStorage.removeItem(CHAVE_CX); S.vivo = null; S.vivoErro = null; };
  S.atualizarVivo = async function () {
    const cx = S.conexao(); if (!cx) { S.vivo = null; return false; }
    try {
      const r = await fetch(cx.api + '/api/export?negocio=' + encodeURIComponent(cx.negocio), { headers: { 'X-Atende-Chave': cx.chave }, cache: 'no-store' });
      if (!r.ok) throw new Error(r.status === 401 ? 'chave ou negócio inválidos' : 'HTTP ' + r.status);
      const d = await r.json();
      d.pedidos.forEach((t) => { t.seg = d.negocio.segmento; t.vivo = true; t.chat = t.chat || []; t.eventos = t.eventos || []; t.historico = t.historico || []; });
      const primeira = !S.vivo;
      S.vivo = d; S.vivoErro = null;
      if (primeira) S.st.segmento = d.negocio.segmento;
      return true;
    } catch (e) { S.vivoErro = e.message || 'falha de rede'; S.vivo = null; return false; }
  };
  S.vivoAtivo = (seg) => !!(S.vivo && S.vivo.negocio.segmento === (seg || S.st.segmento));

  S.salvar = function () {
    try { localStorage.setItem(CHAVE, JSON.stringify(S.st)); } catch (e) { U.toast('Não consegui salvar no navegador.'); }
    S.ouvintes.forEach((f) => f());
  };
  S.resetar = function () { localStorage.removeItem(CHAVE); S.st = S.semear(); S.salvar(); };
  S.seg = () => S.st.segmento;
  S.segDef = (seg) => S.dados.segmentos[seg || S.st.segmento];
  S.negocio = (seg) => S.st.negocios[seg || S.st.segmento];
  S.catalogo = (seg) => S.st.catalogos[seg || S.st.segmento];
  S.ticketsSeg = (seg) => (S.vivoAtivo(seg) ? S.vivo.pedidos : S.st.tickets.filter((t) => t.seg === (seg || S.st.segmento)));
  S.ticket = (id) => (S.vivo && S.vivo.pedidos.find((t) => t.id === id)) || S.st.tickets.find((t) => t.id === id);
  S.novoId = (seg) => { S.st.seq += 1; return ({ loja: 'LJ-', ecommerce: 'EC-' }[seg] || 'OF-') + S.st.seq; };
  /** métricas de carrinho da loja virtual (ao vivo, quando conectado) */
  S.metricasSeg = (seg) => (S.vivoAtivo(seg) ? S.vivo.metricas || {} : (S.st.metricas || {})[seg || S.st.segmento] || {});
  AT.S = S;
})(window.AT);
