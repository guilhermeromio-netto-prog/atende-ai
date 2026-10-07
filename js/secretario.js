/* Atende AI — Secretário do dono (#/secretario): uma mensagem do dono vira várias tarefas, com confirmação e prova.
   Mesmo comportamento do bot (bot/secretario.py), simulado no navegador. Base: docs/secretario/. */
(function (AT) {
  'use strict';
  const U = AT.U; const S = () => AT.S;
  const DIA = 86400000; const HORA_PADRAO = 18;
  const STATUS = ['rascunho', 'aguardando_dado', 'aguardando_ok', 'executada', 'falhou', 'cancelada'];
  const STATUS_TXT = { rascunho: 'Rascunho', aguardando_dado: 'Aguardando dado', aguardando_ok: 'Aguardando seu ok', executada: 'Executada', falhou: 'Falhou', cancelada: 'Cancelada' };
  const PREFIXO = { 'agenda.criar': 'AG', 'lembrete.criar': 'LB', 'financeiro.pagar': 'CT', 'estoque.repor': 'RP', 'cliente.ligar': 'LG' };
  const TIPO_TXT = { 'agenda.criar': '📅 Agenda', 'lembrete.criar': '⏰ Lembrete', 'financeiro.pagar': '🧾 Conta a pagar', 'estoque.repor': '📦 Repor estoque', 'cliente.ligar': '📞 Ligar para cliente' };
  const DIAS = ['dom', 'seg', 'ter', 'qua', 'qui', 'sex', 'sáb'];
  const SEM = { domingo: 0, segunda: 1, terca: 2, quarta: 3, quinta: 4, sexta: 5, sabado: 6 };
  const PERIODO = { manha: 9, tarde: 15, noite: 20 };
  const VERBOS = '(?:me\\s+)?(?:agend|marc|pag|lembr|repor|rep[oô]e|reabastec|encomend|comprar\\s+mais|lig|retorn)';
  const DATA_RX = /(?:hoje|amanh[ãa]|depois\s+de\s+amanh[ãa]|(?:na\s+|no\s+|pr[oó]xim[ao]\s+)?(?:segunda|ter[çc]a|quarta|quinta|sexta|s[áa]bado|domingo)(?:-feira)?|dia\s+\d{1,2}(?:\/\d{1,2})?|\d{1,2}\/\d{1,2})/gi;
  const HORA_RX = /(?:(?:[àa]s?\s+)?\d{1,2}\s*(?:h|:)\s*\d{0,2}(?:\s*min)?|[àa]s\s+\d{1,2}\b|meio[\s-]dia|(?:de|à|a|pela)\s+(?:manh[ãa]|tarde|noite))/gi;
  const n = (s) => U.norm(s);
  const iso = (d) => d.getFullYear() + '-' + String(d.getMonth() + 1).padStart(2, '0') + '-' + String(d.getDate()).padStart(2, '0');
  const deIso = (s) => { const [a, m, d] = s.split('-').map(Number); return new Date(a, m - 1, d); };
  const meiaNoite = (d) => { const x = new Date(d); x.setHours(0, 0, 0, 0); return x; };

  function acharData(txt, agora) {
    const t = txt.toLowerCase(); const hoje = meiaNoite(agora);
    const mais = (k) => new Date(hoje.getFullYear(), hoje.getMonth(), hoje.getDate() + k);
    if (/depois\s+de\s+amanh[ãa]/.test(t)) return mais(2);
    if (/\bamanh[ãa]/.test(t)) return mais(1);
    if (/\bhoje\b/.test(t)) return hoje;
    let m = t.match(/\b(?:dia\s+)?(\d{1,2})\/(\d{1,2})\b/);
    if (m) { let x = new Date(hoje.getFullYear(), +m[2] - 1, +m[1]); if (x.getDate() !== +m[1]) return null; if (x < hoje) x = new Date(hoje.getFullYear() + 1, +m[2] - 1, +m[1]); return x; }
    m = t.match(/\bdia\s+(\d{1,2})\b/);
    if (m) { for (let k = 0; k < 3; k++) { const x = new Date(hoje.getFullYear(), hoje.getMonth() + k, +m[1]); if (x.getDate() === +m[1] && x >= hoje) return x; } return null; }
    m = n(t).match(/\b(segunda|terca|quarta|quinta|sexta|sabado|domingo)\b/);
    if (m) { const delta = ((SEM[m[1]] - hoje.getDay()) + 7) % 7 || 7; return mais(delta); }
    return null;
  }
  function acharHora(txt) {
    const t = txt.toLowerCase();
    if (/meio[\s-]dia/.test(t)) return [12, 0, false];
    for (const rx of [/\b(\d{1,2})\s*:\s*(\d{2})\b/, /\b(\d{1,2})\s*h\s*(\d{2})\b/, /\b(\d{1,2})\s*h(?:oras?)?\b/, /\b[àa]s\s+(\d{1,2})\b(?!\s*\/)/]) {
      const m = t.match(rx);
      if (m) { let h = +m[1]; const mi = m[2] ? +m[2] : 0; if (/\b(da\s+tarde|da\s+noite)\b/.test(t) && h < 12) h += 12; return h <= 23 && mi <= 59 ? [h, mi, false] : null; }
    }
    const m = n(t).match(/\b(manha|tarde|noite)\b/);
    return m ? [PERIODO[m[1]], 0, true] : null;
  }
  const tsDe = (d, hm) => new Date(d.getFullYear(), d.getMonth(), d.getDate(), hm[0], hm[1]).getTime();
  const fmtHora = (h, mi) => (mi ? h + 'h' + String(mi).padStart(2, '0') : h + 'h');
  function fmtDia(d, agora) {
    const hoje = meiaNoite(agora || new Date()); const x = meiaNoite(d); const dif = Math.round((x - hoje) / DIA);
    return dif === 0 ? 'hoje' : dif === 1 ? 'amanhã' : DIAS[x.getDay()] + ', ' + String(x.getDate()).padStart(2, '0') + '/' + String(x.getMonth() + 1).padStart(2, '0');
  }
  const fmtQuando = (ms) => { const d = new Date(ms); return fmtDia(d) + ' às ' + fmtHora(d.getHours(), d.getMinutes()); };
  const horaDe = (s) => s.split(':').map(Number);
  const padrao = (agora) => { const d = meiaNoite(agora); if (agora.getHours() >= HORA_PADRAO) d.setDate(d.getDate() + 1); return tsDe(d, [HORA_PADRAO, 0]); };
  function limpar(s) {
    return s.replace(DATA_RX, ' ').replace(HORA_RX, ' ').replace(/\b(vence|vencimento)\b.*$/i, ' ').replace(/r\$\s*\d[\d.]*(?:,\d{1,2})?/gi, ' ').replace(/\s+/g, ' ').replace(/^[\s,.;:-]+|[\s,.;:-]+$/g, '');
  }
  function pessoaDe(txt) {
    const m = txt.match(/\b(?:com|pro|pra|para|ao|à|a)\s+(?:o\s+|a\s+|seu\s+|sr\.?\s+|sra\.?\s+)?(?:cliente\s+)?([A-Za-zÀ-ú][\wÀ-ú']+(?:\s+(?!hoje|amanh|dia\b|às|as\b|de\b|da\b|do\b|no\b|na\b|e\b)[A-ZÀ-Ú][\wÀ-ú']+){0,2})/);
    if (!m) return null;
    if (['hoje', 'amanha', 'cliente', 'fornecedor', 'dia', 'reuniao', 'conta', 'do', 'da', 'de'].includes(n(m[1])) || /^(EC|OF|LJ)$/i.test(m[1])) return null;
    return m[1].split(/\s+/).map(U.cap).join(' ');
  }
  function tipoDe(c) {
    const t = n(c);
    if (/r\$\s*\d/.test(t) && /\b\d+\s*(h|min|hora|horas)\b|\bestoque\b|\bentrega\b|\ba\s+\d+/.test(t) && !/\b(lembr|agend|marcar|pagar|pague|repor|ligar)/.test(t)) return null;
    if (/\blembr|nao esquecer/.test(t)) return 'lembrete.criar';
    if (/\b(agendar|agende|agenda|marcar|marque|marca)\s+(?:uma?\s+|o\s+|a\s+)?(reuni|visita|consulta|compromisso|horario|encontro|call|conversa|almoco|cafe|com\b|\w+\s+com\b)/.test(t) || /\breuniao\b|\bcompromisso\b/.test(t)) return 'agenda.criar';
    if (/\bpag(ar|o|ue)\b|\bboleto\b|\bfatura\b|\bconta de\b|\bvence\b/.test(t)) return 'financeiro.pagar';
    if (/\b(repor|repoe|reabastec\w*|encomend\w*|comprar mais|pedir mais|reposicao)\b/.test(t)) return 'estoque.repor';
    if (/\b(ligar|retornar|telefonar)\b/.test(t)) return 'cliente.ligar';
    return null;
  }
  function quebrar(texto, juntar) {
    const partes = texto.trim().split(new RegExp('[;\\n]+|,\\s*|\\.\\s+|\\s+e\\s+(?=' + VERBOS + ')|\\s+tamb[ée]m\\s+', 'i'));
    const out = [];
    partes.forEach((p) => {
      p = (p || '').replace(/^[\s.]+|[\s.]+$/g, ''); if (!p) return;
      if (juntar !== false && out.length && !tipoDe(p) && !new RegExp('^(?:e\\s+)?' + VERBOS, 'i').test(p)) out[out.length - 1] += ', ' + p;
      else out.push(p.replace(/^e\s+/i, ''));
    });
    return out;
  }
  function slotsDe(tipo, c, agora) {
    const s = {}; const d = acharData(c, agora); const h = acharHora(c);
    if (tipo === 'agenda.criar') {
      const m = c.match(/\b(?:agendar|marcar|agende|marque|agenda|marca)\s+(?:uma?\s+)?([a-zà-ú]+)/i);
      s.assunto = m && !['com', 'pra', 'para', 'hoje', 'amanha'].includes(n(m[1])) ? m[1].toLowerCase() : (/reuni/i.test(c) ? 'reunião' : 'compromisso');
      const p = pessoaDe(c); if (p) s.pessoa = p;
      if (d) s.data = iso(d);
      if (h) s.hora = String(h[0]).padStart(2, '0') + ':' + String(h[1]).padStart(2, '0');
    } else if (tipo === 'financeiro.pagar') {
      let cr = limpar(c.trim().replace(/^(?:me\s+)?(?:pagar|pague|pago|paga)\s+(?:a\s+|o\s+|as\s+|os\s+)?/i, ''));
      if (cr) s.credor = /^(conta|boleto|fatura)/i.test(cr) ? cr.toLowerCase() : cr;
      const v = c.match(/r\$\s*(\d[\d.]*(?:,\d{1,2})?)/i); if (v) s.valor = parseFloat(v[1].replace(/\./g, '').replace(',', '.'));
      if (d && /venc|dia\s+\d|\d\/\d|amanh|hoje|segunda|ter|quarta|quinta|sexta|sábado|sabado|domingo/i.test(c)) s.vencimento = iso(d);
    } else {
      let it;
      if (tipo === 'lembrete.criar') it = c.replace(/^.*?\b(?:lembrar|lembre|lembra|lembrete|n[ãa]o\s+esquecer)\w*\s+(?:-?me\s+)?(?:de\s+|da\s+|do\s+|que\s+)?/i, '');
      else if (tipo === 'estoque.repor') {
        it = c.replace(/^.*?\b(?:repor|rep[oô]e|reabastecer|encomendar|comprar mais|pedir mais|pedir)\s+(?:o\s+|a\s+|os\s+|as\s+)?(?:estoque\s+d[eoa]\s+)?/i, '').replace(/\s+(ao|pro|para o)\s+fornecedor.*$/i, '');
        const q = it.match(/\b(\d{1,4})\s*(?:un\w*|pe[çc]as?|caixas?|x)?\b/); if (q && !/\d\s*h|\d:\d/.test(it)) { s.quantidade = +q[1]; it = it.replace(q[0], ' '); }
      } else {
        it = '';
        const p = pessoaDe(c); const tid = c.match(/\b((?:OF|LJ|EC)-\d+)\b/i);
        if (tid) s.pedido = tid[1].toUpperCase();
        if (p) s.pessoa = p; else if (tid) s.pessoa = 'cliente do ' + tid[1].toUpperCase();
      }
      it = limpar(it);
      if (tipo !== 'cliente.ligar' && it) s.item = it.slice(0, 80);
      if (tipo === 'estoque.repor' && s.item) {
        const cat = S().catalogo() || []; const ni = n(s.item);
        const c2 = cat.find((x) => n(x.nome).includes(ni) || ni.includes(n(x.nome))) || cat.find((x) => ni.split(' ').filter((w) => w.length > 3).some((w) => n(x.nome).includes(w)));
        if (c2) { s.produto = c2.nome; if (c2.estoque != null) s.estoqueAtual = c2.estoque; }
      }
      if (d || h) { s.quando = tsDe(d || meiaNoite(agora), h ? h : [HORA_PADRAO, 0]); s.quandoDeclarado = !h ? 'padrao' : (h[2] ? 'periodo' : false); if (s.quando < agora.getTime()) s.quando += DIA; }
    }
    return s;
  }
  const REQ = { 'agenda.criar': ['pessoa', 'data', 'hora'], 'financeiro.pagar': ['credor', 'vencimento'], 'lembrete.criar': ['item'], 'estoque.repor': ['item'], 'cliente.ligar': ['pessoa'] };
  const FALTA = { pessoa: 'com quem', data: 'dia', hora: 'hora', credor: 'qual conta', vencimento: 'vencimento', item: 'o quê' };
  const faltando = (tipo, s) => REQ[tipo].filter((k) => !s[k]);
  const faltaTxt = (f) => { const w = f.map((x) => FALTA[x]); return w.join('|') === 'dia|hora' ? 'falta dia e hora' : 'falta ' + (w.length > 1 ? w.slice(0, -1).join(', ') + ' e ' + w[w.length - 1] : w[0]); };
  function titulo(t) {
    const s = t.slots;
    if (t.tipo === 'agenda.criar') return U.cap(s.assunto || 'compromisso') + (s.pessoa ? ' com ' + s.pessoa : '');
    if (t.tipo === 'financeiro.pagar') return U.cap(s.credor || 'conta');
    if (t.tipo === 'lembrete.criar') return U.cap(s.item || 'lembrete');
    if (t.tipo === 'estoque.repor') return 'Repor ' + (s.produto || s.item || 'estoque') + (s.quantidade ? ' (' + s.quantidade + ' un.)' : '');
    return 'Ligar para ' + (s.pessoa || 'cliente');
  }
  function chaves(t) {
    const s = t.slots; const stop = ['conta', 'de', 'da', 'do', 'comprar', 'pagar', 'repor', 'ligar', 'para', 'pro', 'cliente', 'boleto', 'fatura'];
    return new Set(n([s.pessoa, s.credor, s.item, s.produto].filter(Boolean).join(' ')).match(/[a-z0-9]+/g)?.filter((w) => w.length >= 3 && !stop.includes(w)) || []);
  }

  // ------------------------------------------------------------ estado
  function st() {
    const x = S().st;
    if (!x.secretario) x.secretario = { seq: 0, tarefas: [], chat: [], lote: null };
    if (!x.secretario.chat.length) x.secretario.chat.push({ de: 'bot', ts: Date.now(), texto: 'Olá! Sou o Secretário do dono, do Atende AI. Escreva vários pedidos numa mensagem só: eu separo as tarefas, pergunto só o que falta e confirmo cada uma com prova. Contas nunca viram “pagas” sem o seu ok.' });
    return x.secretario;
  }
  const doSeg = () => st().tarefas.filter((t) => t.seg === S().seg());
  function mudar(t, status, extra) { t.status = status; t.atualizado = Date.now(); Object.assign(t, extra || {}); (t.historico = t.historico || []).push({ status, ts: t.atualizado }); }
  function avaliar(t) {
    const s = t.slots; const f = faltando(t.tipo, s); t.falta = f;
    if (f.length) { if (t.status !== 'aguardando_dado') mudar(t, 'aguardando_dado'); return; }
    const agora = Date.now();
    if (t.tipo === 'agenda.criar') { s.inicio = tsDe(deIso(s.data), horaDe(s.hora)); t.disparo = s.inicio > agora ? Math.max(s.inicio - 30 * 60000, agora + 60000) : null; t.disparado = false; mudar(t, 'executada'); }
    else if (t.tipo === 'financeiro.pagar') { t.disparo = Math.max(tsDe(deIso(s.vencimento), [9, 0]), agora + 60000); t.disparado = false; if (t.status !== 'aguardando_ok') mudar(t, 'aguardando_ok'); }
    else { if (!s.quando) { s.quando = padrao(new Date()); s.quandoDeclarado = 'padrao'; } t.disparo = s.quando; t.disparado = false; if (t.status !== 'executada') mudar(t, 'executada'); }
  }
  function linhaLista(t) {
    const s = t.slots;
    if (t.falta.length) return titulo(t) + ' — ' + faltaTxt(t.falta) + '.';
    if (t.tipo === 'agenda.criar') return titulo(t) + ' — ' + fmtDia(deIso(s.data)) + ' às ' + fmtHora(...horaDe(s.hora)) + '.';
    if (t.tipo === 'financeiro.pagar') return titulo(t) + ' — vence ' + fmtDia(deIso(s.vencimento)) + '; pagamento só com o seu ok.';
    return titulo(t) + ' — posso lembrar ' + fmtQuando(s.quando) + '.';
  }
  function card(t) {
    const s = t.slots; const pid = '<strong>#' + t.id + '</strong>'; const tt = U.esc(titulo(t));
    if (t.status === 'aguardando_dado') return '<p>⏳ ' + pid + ' · ' + tt + ' — ' + faltaTxt(t.falta) + '. Aguardando sua resposta.</p>';
    if (t.status === 'cancelada') return '<p>🚫 ' + pid + ' · ' + tt + ' cancelada.</p>';
    if (t.tipo === 'agenda.criar') return '<p>✅ <strong>Tarefa concluída:</strong> ' + U.esc(titulo(t).charAt(0).toLowerCase() + titulo(t).slice(1)) + ' agendada para ' + fmtDia(deIso(s.data)) + ' às ' + fmtHora(...horaDe(s.hora)) + '.</p><p>Prova: ' + pid + ' (agenda do Atende AI' + (t.disparo ? '; aviso 30 min antes' : '') + ').</p>';
    if (t.tipo === 'financeiro.pagar') return t.pagoEm ? '<p>✅ ' + pid + ' · ' + tt + ' marcada como paga por você.</p>'
      : '<p>🧾 <strong>' + tt + '</strong> registrada' + (s.valor ? ' (' + AT.E.brlC(s.valor) + ')' : '') + ', vence ' + fmtDia(deIso(s.vencimento)) + '. O pagamento espera a sua confirmação.</p><p>Não pago nada sem o seu ok: o Atende AI não movimenta dinheiro. Vou te lembrar ' + fmtQuando(t.disparo) + '.</p><p>Prova: ' + pid + ' · status: aguardando seu ok</p>';
    const nome = { 'lembrete.criar': 'Lembrete criado', 'estoque.repor': 'Reposição anotada', 'cliente.ligar': 'Ligação anotada' }[t.tipo];
    const extra = t.tipo === 'estoque.repor' && s.estoqueAtual != null ? ' Estoque atual: ' + s.estoqueAtual + ' un.' : (t.tipo === 'cliente.ligar' && s.pedido ? ' Pedido ' + U.esc(s.pedido) + '.' : '');
    return '<p>✅ <strong>' + nome + ':</strong> ' + U.esc(titulo(t).charAt(0).toLowerCase() + titulo(t).slice(1)) + ' ' + fmtQuando(s.quando) + ({ padrao: ' (horário padrão, America/Sao_Paulo)', periodo: ' (horário do período: manhã 9h, tarde 15h, noite 20h)', true: ' (horário padrão, America/Sao_Paulo)' }[s.quandoDeclarado] || '') + '.' + extra + '</p><p>Prova: ' + pid + '</p>';
  }
  function bot(html, extra) { st().chat.push(Object.assign({ de: 'bot', ts: Date.now(), html }, extra || {})); }
  function exemplo(t) {
    if (t.tipo === 'agenda.criar') return (t.slots.pessoa || 'com o Pedro') + ' amanhã 15h';
    if (t.tipo === 'financeiro.pagar') return ([...chaves(t)][0] || 'conta') + ' vence dia 12';
    return (t.slots.item || 'isso') + ' hoje 18h';
  }

  function completar(txt, lote) {
    const agora = new Date(); const mexidas = [];
    (lote.length > 1 ? quebrar(txt, false) : [txt]).forEach((c) => {
      const ws = new Set(n(c).match(/[a-z0-9]+/g) || []);
      let alvo = lote.find((t) => [...chaves(t)].some((k) => ws.has(k)));
      if (!alvo) {
        const ab = lote.filter((t) => t.status === 'aguardando_dado');
        if (ab.length === 1) alvo = ab[0]; else if (/venc/i.test(c)) alvo = ab.find((t) => t.tipo === 'financeiro.pagar'); else if (acharHora(c)) alvo = ab.find((t) => t.tipo === 'agenda.criar');
      }
      if (!alvo) return;
      const novo = slotsDe(alvo.tipo, alvo.tipo === 'financeiro.pagar' && !/venc/i.test(c) ? 'vence ' + c : c, agora); const s = alvo.slots; let mudou = false;
      ['data', 'hora', 'vencimento', 'valor', 'quando', 'quandoDeclarado'].forEach((k) => { if (novo[k] != null && novo[k] !== s[k]) { s[k] = novo[k]; mudou = true; } });
      if (alvo.tipo === 'agenda.criar' && !s.pessoa && novo.pessoa) { s.pessoa = novo.pessoa; mudou = true; }
      if (mudou) { if (novo.quando) { alvo.disparo = s.quando; alvo.disparado = false; } avaliar(alvo); if (!mexidas.includes(alvo)) mexidas.push(alvo); }
    });
    if (!mexidas.length) return false;
    mexidas.forEach((t) => bot(card(t), { cartao: t.id }));
    const rest = lote.filter((t) => t.status === 'aguardando_dado');
    if (rest.length) bot('<p>Ainda falta: ' + rest.map((t) => U.esc(faltaTxt(t.falta).replace('falta ', '') + ' de “' + titulo(t) + '” (#' + t.id + ')')).join('; ') + '.</p>');
    return true;
  }

  /** processa uma mensagem do dono; devolve true se virou tarefa(s) */
  function processar(txt) {
    const E = st(); const agora = Date.now();
    E.chat.push({ de: 'dono', ts: agora, texto: txt });
    const lote = E.lote && agora - E.lote.ts < 6 * 3600000 ? E.tarefas.filter((t) => E.lote.ids.includes(t.id) && t.status !== 'cancelada') : [];
    if (lote.length && completar(txt, lote)) { S().salvar(); return true; }
    const itens = quebrar(txt).map((c) => ({ c, tipo: tipoDe(c) }));
    const ok = itens.filter((x) => x.tipo); const ign = itens.filter((x) => !x.tipo);
    if (!ok.length) { bot('<p>Não encontrei um pedido nessa mensagem. Experimente: <em>Agendar reunião com João, pagar conta de luz, lembrar de comprar leite</em>.</p>'); S().salvar(); return false; }
    const tks = ok.map((x) => {
      E.seq += 1;
      const t = { id: PREFIXO[x.tipo] + '-' + String(E.seq).padStart(4, '0'), seg: S().seg(), tipo: x.tipo, slots: slotsDe(x.tipo, x.c, new Date()), origem: txt, trecho: x.c, status: 'rascunho', criado: agora, atualizado: agora, historico: [{ status: 'rascunho', ts: agora }] };
      avaliar(t); E.tarefas.push(t); return t;
    });
    E.lote = { ids: tks.map((t) => t.id), ts: agora };
    let h = '<p>📝 <strong>Encontrei ' + tks.length + ' pedido' + (tks.length > 1 ? 's' : '') + ':</strong></p><ol class="sec-lista">' + tks.map((t) => '<li>' + U.esc(linhaLista(t)) + '</li>').join('') + '</ol>';
    if (ign.length) h += '<p>Não entendi: ' + ign.map((x) => '“' + U.esc(x.c.slice(0, 60)) + '”').join('; ') + '.</p>';
    const falt = tks.filter((t) => t.falta.length);
    h += falt.length ? '<p>Para concluir, me responda <strong>numa mensagem só</strong>: ' + falt.map((t) => U.esc(faltaTxt(t.falta).replace('falta ', '') + ' de “' + titulo(t) + '”')).join('; ') + '.<br>Ex.: <em>' + U.esc(falt.map(exemplo).join(', ')) + '</em></p>' : '<p>Tudo claro: confira os cartões abaixo.</p>';
    bot(h, { lista: true });
    tks.forEach((t) => bot(card(t), { cartao: t.id }));
    S().salvar(); return true;
  }
  function acao(id, qual) {
    const t = st().tarefas.find((x) => x.id === id); if (!t) return;
    if (qual === 'cancelar' && t.status !== 'cancelada' && !t.pagoEm) { mudar(t, 'cancelada'); t.disparo = null; bot(card(t), { cartao: t.id }); }
    if (qual === 'pago' && t.tipo === 'financeiro.pagar' && t.status === 'aguardando_ok') { mudar(t, 'executada', { pagoEm: Date.now() }); t.disparo = null; bot(card(t), { cartao: t.id }); }
    if (qual === 'disparar' && t.disparo && !t.disparado) { t.disparo = Date.now() - 1; vigiar(); return; }
    S().salvar();
  }
  /** dispara lembretes vencidos (chamado a cada 30 s e pelo botão "Simular horário") */
  function vigiar() {
    const E = S().st.secretario; if (!E) return 0; const agora = Date.now(); let k = 0;
    E.tarefas.forEach((t) => {
      if (!t.disparo || t.disparado || t.disparo > agora || !['executada', 'aguardando_ok'].includes(t.status)) return;
      const s = t.slots; let h;
      if (t.tipo === 'agenda.criar') h = '<p>⏰ <strong>Daqui a pouco:</strong> ' + U.esc(titulo(t)) + ' às ' + fmtHora(...horaDe(s.hora)) + ' (#' + t.id + ').</p>';
      else if (t.tipo === 'financeiro.pagar') h = '<p>⏰ <strong>Conta a pagar:</strong> ' + U.esc(titulo(t)) + ' vence ' + fmtDia(deIso(s.vencimento)) + ' (#' + t.id + '). Continua aguardando o seu ok; eu não pago nada sozinho.</p>';
      else h = '<p>⏰ <strong>Lembrete:</strong> ' + U.esc(titulo(t)) + ' (#' + t.id + ').</p>';
      t.disparado = true; t.disparadoEm = agora; k++;
      E.chat.push({ de: 'auto', ts: agora, html: h });
      U.toast('⏰ ' + titulo(t) + ' (#' + t.id + ')');
    });
    if (k) S().salvar();
    return k;
  }

  // ------------------------------------------------------------ modo conectado: /api/secretario
  let vivo = null; let vivoErro = null;
  async function lerVivo() {
    const cx = S().conexao(); if (!cx) { vivo = null; return; }
    try {
      const r = await fetch(cx.api + '/api/secretario?negocio=' + encodeURIComponent(cx.negocio), { headers: { 'X-Atende-Chave': cx.chave }, cache: 'no-store' });
      if (!r.ok) throw new Error('HTTP ' + r.status);
      vivo = await r.json(); vivoErro = null;
    } catch (e) { vivo = null; vivoErro = e.message; }
  }
  const tarefasPainel = () => (vivo ? vivo.tarefas.map((t) => Object.assign({}, t, { slots: Object.assign({}, t.slots, t.slots.quando_declarado != null ? { quandoDeclarado: t.slots.quando_declarado } : {}), _vivo: true })) : doSeg());

  function painel(lista, compacto) {
    const col = (stt) => lista.filter((t) => t.status === stt);
    const grupos = [['aguardando_dado', '⏳'], ['aguardando_ok', '🧾'], ['executada', '✅'], ['falhou', '⚠️'], ['cancelada', '🚫']];
    if (!lista.length) return '<p class="muted">Nenhuma tarefa ainda. Mande um pedido para o Secretário' + (compacto ? ' em <a href="#/secretario">Secretário</a>' : '') + '.</p>';
    return '<div class="sec-cols">' + grupos.filter(([g]) => !compacto || col(g).length).map(([g, ic]) => '<section class="sec-col" aria-labelledby="sec-c-' + g + '"><h3 id="sec-c-' + g + '" class="h3">' + ic + ' ' + STATUS_TXT[g] + ' <span class="chip">' + col(g).length + '</span></h3>' +
      col(g).slice(-8).reverse().map((t) => {
        const s = t.slots; let quando = '';
        if (t.tipo === 'agenda.criar' && s.data && s.hora) quando = fmtDia(deIso(s.data)) + ' às ' + fmtHora(...horaDe(s.hora));
        else if (t.tipo === 'financeiro.pagar' && s.vencimento) quando = 'vence ' + fmtDia(deIso(s.vencimento)) + (t.pagoEm ? ' · paga ✅' : '');
        else if (s.quando) quando = fmtQuando(s.quando) + (t.disparado ? ' · avisado' : '');
        else if (t.falta && t.falta.length) quando = faltaTxt(t.falta);
        const acoes = compacto || t._vivo ? '' : (t.status === 'aguardando_ok' ? '<button type="button" class="btn btn--p btn--pri" data-sec="pago" data-id="' + t.id + '">✅ Já paguei</button>' : '') +
          (t.disparo && !t.disparado && ['executada', 'aguardando_ok'].includes(t.status) ? '<button type="button" class="btn btn--p" data-sec="disparar" data-id="' + t.id + '" title="Simula que chegou o horário do aviso">⏰ Simular horário</button>' : '') +
          (!['cancelada'].includes(t.status) && !t.pagoEm ? '<button type="button" class="btn btn--p btn--perigo" data-sec="cancelar" data-id="' + t.id + '" aria-label="Cancelar ' + U.esc(t.id) + '">Cancelar</button>' : '');
        return '<article class="sec-card"><div class="sec-card__topo"><code>#' + U.esc(t.id) + '</code><span class="pequeno muted">' + TIPO_TXT[t.tipo] + '</span></div><strong>' + U.esc(titulo(t)) + '</strong>' +
          (quando ? '<div class="pequeno">' + U.esc(quando) + '</div>' : '') + (acoes ? '<div class="sec-card__acoes">' + acoes + '</div>' : '') + '</article>';
      }).join('') + (col(g).length ? '' : '<p class="pequeno muted">—</p>') + '</section>').join('') + '</div>';
  }
  function resumoPorStatus(lista) { return STATUS.map((s) => [s, lista.filter((t) => t.status === s).length]); }

  async function render(main) {
    const seg = S().seg(); const canal = AT.Canais.atual();
    const exemplos = ['Agendar reunião com João, pagar conta de luz, lembrar de comprar leite', 'João amanhã 15h, luz vence dia 12, leite hoje à noite'].concat(
      seg === 'ecommerce' ? ['Repor fone bluetooth 20 unidades, ligar pro cliente Ana amanhã 10h'] : seg === 'oficina' ? ['Ligar pro cliente do Onix amanhã 9h, repor pastilha de freio 10 unidades'] : ['Repor tinta acrílica 12 latas, ligar pro cliente Bia amanhã 10h']);
    main.innerHTML = `
      <div class="cab"><div><div class="olho">Para o dono · ${U.esc(S().segDef().rotulo)}</div><h1>Secretário do dono</h1>
        <p>Uma mensagem com vários pedidos vira tarefas separadas: agenda, lembretes, contas a pagar e tarefas do negócio. O Secretário pergunta só o que falta, numa mensagem, e confirma cada item com prova. Contas nunca são marcadas como pagas sem o seu ok.</p></div>
        <button type="button" class="btn btn--p" id="sec-limpar">Recomeçar a simulação</button></div>
      ${vivoErro ? '<div class="vivo vivo--erro" role="status">⚠️ Não foi possível ler /api/secretario (' + U.esc(vivoErro) + '). Mostrando a simulação.</div>' : vivo ? '<div class="vivo" role="status"><strong>🟢 Modo conectado</strong> · o painel mostra as tarefas reais do bot (' + U.esc(vivo.negocio.nome) + '). A conversa ao lado continua sendo simulação.</div>' : ''}
      <div class="duas duas--chat">
        ${AT.Chat.moldura({ id: 'sec-chat', avatar: 'S', nome: 'Atende AI · Secretário', status: 'bot · modo dono · ' + S().negocio().nome, label: 'Mensagem para o Secretário', placeholder: 'Ex.: Agendar reunião com João, pagar conta de luz…', canal })}
        <div class="lateral">
          <section class="card" aria-labelledby="sec-p-t"><h2 id="sec-p-t">Tarefas por status ${vivo ? '<span class="chip chip--ok">ao vivo</span>' : '<span class="chip chip--exemplo">simulação</span>'}</h2><div id="sec-painel"></div></section>
          <section class="card"><h2>Regras (critérios de aceite)</h2><ul class="pequeno muted" style="margin:0;padding-left:18px">
            <li>Três pedidos geram três cartões, cada um com prova (#AG, #CT, #LB…).</li>
            <li>Reunião só entra na agenda com pessoa, data e hora.</li>
            <li>Conta fica em “aguardando seu ok”; só vira paga pelo botão.</li>
            <li>Lembrete sem hora: hoje às 18h (ou amanhã, se já passou), declarado.</li>
            <li>No Telegram, áudio recebe um pedido educado para escrever: não fingimos transcrição.</li></ul></section>
        </div>
      </div>`;
    const box = main.querySelector('#sec-chat'); const log = box.querySelector('.cv__log'); const ops = box.querySelector('.cv__opcoes');
    const form = box.querySelector('form'); const inp = form.querySelector('input');
    const usados = new Set(); let ocupado = false;
    function desenhar() {
      AT.Chat.render(log, st().chat, ['dono'], canal);
      AT.Chat.opcoes(ops, exemplos.filter((e) => !usados.has(e)), (o) => { usados.add(o); enviar(o); });
      main.querySelector('#sec-painel').innerHTML = painel(tarefasPainel());
    }
    function enviar(txt) {
      txt = String(txt || '').trim(); if (!txt || ocupado) return; ocupado = true;
      st().chat.push({ de: 'dono', ts: Date.now(), texto: txt }); AT.Chat.render(log, st().chat, ['dono'], canal); st().chat.pop();
      AT.Chat.digitando(log, true);
      setTimeout(() => { AT.Chat.digitando(log, false); processar(txt); ocupado = false; desenhar(); }, AT.Chat.atraso());
    }
    form.addEventListener('submit', (e) => { e.preventDefault(); const v = inp.value; inp.value = ''; enviar(v); });
    main.querySelector('#sec-painel').addEventListener('click', (e) => { const b = e.target.closest('[data-sec]'); if (!b) return; acao(b.dataset.id, b.dataset.sec); desenhar(); });
    main.querySelector('#sec-limpar').addEventListener('click', () => { const E = st(); E.tarefas = E.tarefas.filter((t) => t.seg !== S().seg()); E.chat = []; E.lote = null; S().salvar(); usados.clear(); desenhar(); U.toast('Simulação do Secretário recomeçada.'); });
    desenhar();
    if (S().conexao() && !vivo && !vivoErro) { await lerVivo(); if (vivo || vivoErro) render(main); }
    AT.V.secretario._tick = async () => { if (!document.body.contains(box)) return; if (S().conexao()) await lerVivo(); desenhar(); };
  }

  AT.Sec = { processar, acao, vigiar, extrair: (t) => quebrar(t).map((c) => ({ tipo: tipoDe(c), slots: tipoDe(c) ? slotsDe(tipoDe(c), c, new Date()) : null, trecho: c })), titulo, painel, resumoPorStatus, lerVivo,
    tarefas: () => tarefasPainel(), vivo: () => vivo, STATUS, STATUS_TXT };
  AT.V = AT.V || {};
  AT.V.secretario = { titulo: 'Secretário do dono', render };
})(window.AT);
