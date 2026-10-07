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
      tickets: [], conversas: {}, onboarding: {}
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
  S.novoId = (seg) => { S.st.seq += 1; return (seg === 'loja' ? 'LJ-' : 'OF-') + S.st.seq; };
  AT.S = S;
})(window.AT);
