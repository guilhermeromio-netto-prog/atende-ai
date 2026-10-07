/* Atende AI — "motor" de regras: orçamento, SLA, automações e parsers.
   IMPORTANTE: não há IA real aqui. Tudo é simulado com regras e palavras-chave (dados.json). */
(function (AT) {
  'use strict';
  const U = AT.U;
  const M = {};
  const S = () => AT.S;

  /* ---------- orçamento e SLA ---------- */
  M.orcamento = function (seg, servicos, veiculo, catalogo) {
    const def = S().segDef(seg);
    const cat = catalogo || S().catalogo(seg);
    let fator = 1, ajuste = null;
    const v = U.norm(veiculo);
    (def.ajustes || []).forEach((a) => { if (v && a.palavras.some((p) => new RegExp('\\b' + p + '\\b').test(v))) { fator = a.fator; ajuste = a.rotulo; } });
    const itens = servicos.map((id) => cat.find((c) => c.id === id)).filter(Boolean).map((c) => ({
      id: c.id, nome: c.nome,
      pecasMin: Math.round(c.pecasMin * fator), pecasMax: Math.round(c.pecasMax * fator),
      maoMin: c.maoMin, maoMax: c.maoMax, duracao: c.duracao
    }));
    const total = itens.reduce((a, i) => ({ min: a.min + i.pecasMin + i.maoMin, max: a.max + i.pecasMax + i.maoMax }), { min: 0, max: 0 });
    const duracao = itens.reduce((a, i) => a + (+i.duracao || 0), 0);
    return { itens, total, duracao, ajuste };
  };
  M.calcPrazo = function (seg, prio, inicio, duracao) {
    const sla = S().st.sla[seg][prio] || S().st.sla[seg].media;
    const minutos = Math.max(sla.conclusaoHoras * 60, duracao || 0);
    return U.somaUteis(inicio, minutos, S().negocio(seg).horario);
  };
  M.slaEstado = function (t, agora) {
    agora = agora || Date.now();
    if (t.prontoEm) {
      const ok = t.prontoEm <= t.prazo;
      return { cls: ok ? 'ok' : 'erro', texto: ok ? 'SLA cumprido' : 'SLA estourado', cumprido: ok, ativo: false };
    }
    const resta = t.prazo - agora, janela = Math.max(t.prazo - t.criado, 1);
    if (resta < 0) return { cls: 'erro', texto: U.restante(resta), cumprido: false, ativo: true };
    if (resta < janela * 0.25) return { cls: 'atencao', texto: U.restante(resta), ativo: true };
    return { cls: 'ok', texto: U.restante(resta), ativo: true };
  };
  M.valorMedio = (t) => (t.total ? (t.total.min + t.total.max) / 2 : 0);

  const minusc = (s) => (/^[A-ZÁÉÍÓÚ]{2}/.test(s) ? s : s.charAt(0).toLowerCase() + s.slice(1));
  M.vars = function (t) {
    const rot = S().segDef(t.seg).rotulos;
    return {
      cliente: U.primeiroNome(t.cliente),
      servico: (t.itens || []).map((i) => minusc(i.nome)).join(' + ') || 'o serviço',
      prazo: U.dataHora(t.prazo),
      valor: t.total ? U.faixa(t.total.min, t.total.max) : 'a confirmar',
      negocio: S().negocio(t.seg).nome,
      veiculo: t.veiculo || 'seu ' + rot.objeto,
      placa: t.placa || ''
    };
  };

  /* ---------- automações (cadeia de mensagens) ---------- */
  M.mudarStatus = function (t, status, ts, opts) {
    ts = ts || Date.now(); opts = opts || {};
    t.status = status;
    t.historico.push({ status, ts });
    if (status === 'Aprovado') t.aprovadoEm = ts;
    if (status === 'Pronto') t.prontoEm = ts;
    if (status === 'Entregue') { t.entregueEm = ts; if (!t.prontoEm) t.prontoEm = ts; if (!t.valorFinal) t.valorFinal = Math.round(M.valorMedio(t)); }
    if (status === 'Em serviço') {
      t.eventos.filter((e) => e.regra === 'lembrete' && e.estado === 'agendado').forEach((e) => { e.estado = 'enviado'; e.ts = ts - 5 * 60000; });
    }
    const regras = (S().st.automacoes[t.seg] || []).filter((r) => r.gatilho === status && r.ativo);
    const vars = M.vars(t);
    regras.forEach((r, i) => {
      const texto = U.template(r.template, vars);
      let estado = 'enviado', quando = ts + i * 1000;
      if (r.id === 'lembrete') estado = 'agendado';
      if (r.id === 'posvenda') { quando = ts + 24 * 3600000; estado = quando <= Date.now() ? 'enviado' : 'agendado'; }
      t.eventos.push({ regra: r.id, nome: r.nome, ts: quando, estado, texto });
      if (estado === 'enviado' && !(opts.pularChat || []).includes(r.id)) t.chat.push({ de: 'auto', regra: r.id, texto, ts: quando });
    });
  };
  M.proximoStatus = (t) => { const o = S().dados.status; const i = o.indexOf(t.status); return i >= 0 && i < o.length - 1 ? o[i + 1] : null; };

  /* ---------- atendimento: intenção e entidades ---------- */
  M.detectar = function (seg, texto) {
    const n = U.norm(texto); const def = S().segDef(seg);
    let melhor = null, pts = 0;
    def.intents.forEach((it) => {
      let s = 0; it.palavras.forEach((p) => { const q = U.norm(p); if (n.includes(q)) s += q.split(' ').length + 0.5; });
      if (s > pts) { pts = s; melhor = it; }
    });
    let melhorCat = null, ptsCat = 0;
    S().catalogo(seg).forEach((c) => {
      let s = 0;
      const termos = (c.palavras || []).concat(U.norm(c.nome).split(' ').filter((w) => w.length >= 5));
      termos.forEach((p) => { const q = U.norm(p); if (q && n.includes(q)) s += q.split(' ').length; });
      if (s > ptsCat) { ptsCat = s; melhorCat = c; }
    });
    if (melhor && pts >= ptsCat) return { intent: melhor, confianca: Math.min(0.97, 0.6 + pts * 0.1) };
    if (melhorCat) return { intent: { id: 'cat-' + melhorCat.id, rotulo: melhorCat.nome, servicos: [melhorCat.id], opcionais: [], prioridade: 'media', explicacao: 'Temos "' + melhorCat.nome + '" no catálogo, com duração média de ' + U.dur(melhorCat.duracao) + '.' }, confianca: Math.min(0.9, 0.55 + ptsCat * 0.1) };
    return null;
  };
  M.extrair = function (seg, texto) {
    const out = {}; const n = U.norm(texto); const def = S().segDef(seg);
    const pl = texto.match(/\b([a-zA-Z]{3})-?(\d[a-zA-Z]\d{2}|\d{4})\b/);
    if (pl) out.placa = (pl[1] + pl[2]).toUpperCase();
    const mod = (def.modelos || []).find((m) => new RegExp('(^|[^a-z0-9])' + m.replace(/[-]/g, '\\-') + '([^a-z0-9]|$)').test(n));
    if (mod) {
      const ano = n.match(/\b(19[89]\d|20[0-3]\d)\b/);
      out.veiculo = (/\d/.test(mod) ? mod.toUpperCase() : mod.split('-').map(U.cap).join('-')) + (ano ? ' ' + ano[1] : '');
    }
    if (/urgent|socorro|guincho|parado|agora|hoje|preciso ja/.test(n)) out.urgencia = 'alta';
    else if (/sem pressa|quando der|qualquer dia|tranquilo/.test(n)) out.urgencia = 'baixa';
    else if (/semana|amanha/.test(n)) out.urgencia = 'media';
    const nm = texto.match(/(?:meu nome é|meu nome e|me chamo|aqui é o|aqui é a|sou o|sou a)\s+([A-Za-zÀ-ú]{2,}(?:\s+[A-Za-zÀ-ú]{2,})?)/i);
    if (nm) out.cliente = nm[1].split(/\s+/).map(U.cap).join(' ');
    return out;
  };
  M.urgenciaDeResposta = function (txt) {
    const n = U.norm(txt);
    if (/urgent|hoje|agora|ja|socorro|🚨/.test(n) || txt.includes('🚨')) return 'alta';
    if (/semana|amanha|📅/.test(n) || txt.includes('📅')) return 'media';
    if (/pressa|quando|tranquil|qualquer/.test(n) || txt.includes('🙂')) return 'baixa';
    return null;
  };

  /* ---------- onboarding: extração de dados do dono ---------- */
  const NUM = '(\\d{1,3}(?:\\.\\d{3})+(?:,\\d{1,2})?|\\d+(?:,\\d{1,2})?)';
  const preco = (s) => (s ? parseFloat(String(s).replace(/\./g, '').replace(',', '.')) : null);
  const DIA = { dom: 0, seg: 1, ter: 2, qua: 3, qui: 4, sex: 5, sab: 6 };
  const ehHorario = (n) => /\b(seg|segunda|ter|terca|qua|quarta|qui|quinta|sex|sexta|sab|sabado|dom|domingo|feriado)/.test(n) && (/\d{1,2}\s*(h|:)/.test(n) || /fechad/.test(n));
  const PECA = /oleo|filtro|pastilha|disco|bateria|pneu|peca|lampada|palheta|correia|vela|tinta|chuveiro|torneira|cimento|kit|produto|material/;

  M.parseHorario = function (chunk) {
    const n = U.norm(chunk).replace(/[àá]/g, 'a');
    let dias = [];
    const rg = n.match(/\b(seg|ter|qua|qui|sex|sab|dom)\w*\.?\s*(?:a|ate|-|–)\s*(seg|ter|qua|qui|sex|sab|dom)/);
    if (rg) { let i = DIA[rg[1]]; const f = DIA[rg[2]]; let g = 0; while (g++ < 8) { dias.push(i); if (i === f) break; i = (i + 1) % 7; } }
    else { const re = /\b(seg|ter|qua|qui|sex|sab|dom)/g; let m; while ((m = re.exec(n))) dias.push(DIA[m[1]]); }
    if (/\b(fechad|nao abr)/.test(n)) return dias.length ? { dias, fechado: true } : null;
    const h = n.match(/(\d{1,2})(?:h|:)?(\d{2})?\s*h?\s*(?:as|a|ate|-|–)\s*(\d{1,2})(?:h|:)?(\d{2})?/);
    if (!dias.length || !h) return null;
    const ab = U.fromMin(+h[1] * 60 + (+h[2] || 0)), fe = U.fromMin(+h[3] * 60 + (+h[4] || 0));
    if (U.toMin(fe) <= U.toMin(ab)) return null;
    return { dias, abre: ab, fecha: fe };
  };

  M.parseServico = function (chunk, seg) {
    let resto = ' ' + chunk + ' ';
    const out = { pecasMin: 0, pecasMax: 0, maoMin: 0, maoMax: 0, duracao: 0 };
    let achouPreco = false;
    // duração
    const rd = /(\d+(?:[.,]\d+)?)\s*(?:horas|hora|hrs|hr|hs|h)(?![a-zà-ú])\s*(?:e\s*)?(\d{1,2})?\s*(?:minutos|min)?|(\d+)\s*(?:min|mins|minutos)\b|(\d+)\s*(?:dia|dias)\b/i;
    const d = resto.match(rd);
    if (d) {
      if (d[1]) out.duracao = Math.round(parseFloat(d[1].replace(',', '.')) * 60) + (+d[2] || 0);
      else if (d[3]) out.duracao = +d[3];
      else if (d[4]) out.duracao = +d[4] * 600; // dia útil de 10h
      resto = resto.replace(d[0], ' ');
    }
    const faixa = (rot) => new RegExp(rot + '\\s*(?:de|:|=)?\\s*(?:r\\$\\s*)?' + NUM + '(?:\\s*(?:a|até|ate|-|–)\\s*(?:r\\$\\s*)?' + NUM + ')?', 'i');
    const rp = resto.match(faixa('(?:peças|pecas|peça|peca|produtos?|material|materiais)'));
    if (rp) { out.pecasMin = preco(rp[1]); out.pecasMax = preco(rp[2]) || out.pecasMin; resto = resto.replace(rp[0], ' '); achouPreco = true; }
    const rm = resto.match(faixa('(?:mão de obra|mao de obra|mão-de-obra|instalação|instalacao|serviço|servico|montagem)'));
    if (rm) { out.maoMin = preco(rm[1]); out.maoMax = preco(rm[2]) || out.maoMin; resto = resto.replace(rm[0], ' '); achouPreco = true; }
    const temP = !!rp, temM = !!rm;
    if (!(temP && temM)) {
      let g = resto.match(new RegExp('r\\$\\s*' + NUM + '(?:\\s*(?:a|até|ate|-|–)\\s*(?:r\\$\\s*)?' + NUM + ')?', 'i'));
      if (!g) g = resto.match(new RegExp('\\b' + NUM + '\\s*(?:reais)?(?:\\s*(?:a|até|ate|-|–)\\s*' + NUM + ')?\\s*(?:reais)?', 'i'));
      if (g) {
        const a = preco(g[1]), b = preco(g[2]) || a;
        if (a >= 5) {
          const nomeN = U.norm(resto);
          if (temM) { out.pecasMin = a; out.pecasMax = b; }
          else if (temP) { out.maoMin = a; out.maoMax = b; }
          else if (PECA.test(nomeN) || seg === 'loja' && !/instala|entrega|frete|corte|montag/.test(nomeN)) { out.pecasMin = a; out.pecasMax = b; }
          else { out.maoMin = a; out.maoMax = b; }
          resto = resto.replace(g[0], ' '); achouPreco = true;
        }
      }
    }
    if (!achouPreco && !out.duracao) return null;
    let nome = resto.replace(/r\$/gi, ' ')
      .replace(/\b(reais|custa|custando|cobro|cobramos|valor|preço|preco|por volta de|cerca de|em média|em media|leva|demora|dura|tempo|aprox\.?|aproximadamente|mais)\b/gi, ' ')
      .replace(/[:=|•·()]/g, ' ').replace(/\s[-–]\s/g, ' ').replace(/\s+/g, ' ').trim()
      .replace(/^(e|a|o|de|faço|faco|fazemos|temos|vendo|vendemos|também|tambem)\s+/i, '')
      .replace(/\s+(de|por|a|e|com|em|no|na)$/i, '').replace(/[,.;-]+$/, '').trim();
    if (nome.length < 3) return null;
    out.nome = U.cap(nome);
    out.palavras = U.norm(nome).split(' ').filter((w) => w.length >= 4);
    return out;
  };

  M.parseDono = function (texto, seg) {
    const res = { nome: null, servicos: [], horarios: [] };
    const nm = texto.match(/(?:se chama|chama-se|nome (?:dela |dele |do negócio |da empresa |da loja |da oficina )?(?:é|e)|^\s*nome\s*:)\s*["“']?([^"”'\n;.!]+)/i);
    if (nm) res.nome = nm[1].trim().replace(/\s+/g, ' ');
    const blocos = texto.split(/\n|;/).map((s) => s.trim()).filter(Boolean);
    blocos.forEach((b) => {
      const n = U.norm(b);
      if (nm && b.includes(nm[0].trim().slice(0, 12))) return;
      if (ehHorario(n)) {
        b.split(/,|\s+e\s+(?=(?:seg|ter|qua|qui|sex|s[áa]b|dom))/i).forEach((p) => { const h = M.parseHorario(p); if (h) res.horarios.push(h); });
        return;
      }
      const qtdPreco = (b.match(/r\$/gi) || []).length;
      const partes = qtdPreco >= 2 && !/m[ãa]o de obra|pe[çc]as|instala/i.test(b) ? b.split(/,\s*(?=[A-Za-zÀ-ú])|\s+e\s+(?=[A-Za-zÀ-ú]+[^$]*r\$)/i) : [b];
      partes.forEach((p) => { const s = M.parseServico(p, seg); if (s) res.servicos.push(s); });
    });
    return res;
  };

  AT.M = M;
})(window.AT);
