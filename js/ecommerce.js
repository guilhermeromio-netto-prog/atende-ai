/* Atende AI — Loja virtual (ecommerce): mesmas regras do bot (bot/motor.py + bot/ecommerce.py), em JS.
   Busca tolerante a erros, carrinho, frete por CEP (região pelo 1º dígito; ViaCEP opcional), resumo com
   desconto Pix, instruções de pagamento do lojista e “Já paguei”. Nenhum pagamento real acontece aqui. */
(function (AT) {
  'use strict';
  const U = AT.U;
  const S = () => AT.S;
  const E = {};
  const clone = (o) => JSON.parse(JSON.stringify(o));

  /* ---------- formatação ---------- */
  const brlC = new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL', minimumFractionDigits: 2, maximumFractionDigits: 2 });
  E.brlC = (v) => brlC.format(+v || 0).replace(/\u00a0/g, ' ');
  E.r2 = (v) => Math.round((+v + 1e-9) * 100) / 100;
  E.itensTexto = (itens) => (itens || []).map((i) => (i.qtd != null ? i.qtd + 'x ' : '') + i.nome).join(' + ');

  /* ---------- políticas ---------- */
  E.politicasPadrao = () => clone(S().dados.segmentos.ecommerce.politicas);
  E.pol = () => { const st = S().st; st.politicas = st.politicas || {}; if (!st.politicas.ecommerce) st.politicas.ecommerce = E.politicasPadrao(); return st.politicas.ecommerce; };
  E.metricas = () => { const st = S().st; st.metricas = st.metricas || {}; if (!st.metricas.ecommerce) st.metricas.ecommerce = { carrinhos: 0, abandonados: 0 }; return st.metricas.ecommerce; };
  E.envioDias = (pol, t) => {
    let base = parseInt((pol || E.pol()).envioDiasUteis, 10) || 1;
    if (t && t.itens) t.itens.forEach((i) => { base = Math.max(base, parseInt(i.envioDias, 10) || 0); });
    return base;
  };
  /** fim do expediente do n-ésimo dia útil (dia com horário de funcionamento) depois de ts */
  E.somaDiasUteis = (ts, n, horario) => {
    const d = new Date(ts); let contados = 0;
    for (let g = 0; g < 60; g++) {
      d.setDate(d.getDate() + 1); d.setHours(12, 0, 0, 0);
      const h = horario ? horario[d.getDay()] : ['18:00', '18:00'];
      if (h) { contados++; if (contados >= Math.max(1, n)) { const fe = U.toMin(h[1]); d.setHours(Math.floor(fe / 60), fe % 60, 0, 0); return d.getTime(); } }
    }
    return ts + n * 86400000;
  };
  const REGIAO_UF = { SP: 'SP', RJ: 'Sudeste', MG: 'Sudeste', ES: 'Sudeste' };
  E.regiaoCep = (cep, uf) => {
    if (uf) return REGIAO_UF[String(uf).toUpperCase()] || 'Outros';
    const c = String(cep || '').replace(/\D/g, ''); if (!c) return 'Outros';
    return '01'.includes(c[0]) ? 'SP' : '23'.includes(c[0]) ? 'Sudeste' : 'Outros';
  };
  E.acharCep = (txt) => { const m = String(txt || '').match(/\b(\d{5})-?(\d{3})\b/); return m ? m[1] + '-' + m[2] : null; };
  /** consulta pública opcional; se falhar, vale a regra do 1º dígito */
  E.viacep = async (cep) => {
    if (E.semRede) return null;
    try {
      const ctl = new AbortController(); const tm = setTimeout(() => ctl.abort(), 3500);
      const r = await fetch('https://viacep.com.br/ws/' + cep.replace(/\D/g, '') + '/json/', { signal: ctl.signal });
      clearTimeout(tm); if (!r.ok) return null;
      const d = await r.json(); return d.erro ? null : { cidade: d.localidade, uf: d.uf };
    } catch (e) { return null; }
  };
  E.calcFrete = (pol, subtotal, regiao) => {
    const f = pol.frete || {}; const dias = parseInt((f.prazosDias || {})[regiao], 10) || 5;
    if (f.gratisAcima != null && f.gratisAcima !== '' && subtotal >= +f.gratisAcima) return { valor: 0, dias, gratis: true };
    if (f.tipo === 'fixo') return { valor: +f.fixo || 0, dias, gratis: false };
    let v = (f.regioes || {})[regiao]; if (v == null) v = f.fixo || 0;
    return { valor: +v, dias, gratis: false };
  };
  E.textoPoliticas = (pol) => {
    const f = pol.frete || {}, pg = pol.pagamento || {}; const ls = [];
    if (f.tipo === 'fixo') ls.push('🚚 Frete fixo ' + E.brlC(f.fixo || 0));
    else ls.push('🚚 Frete por região: ' + Object.entries(f.regioes || {}).map(([k, v]) => k + ' ' + E.brlC(v) + ' (' + ((f.prazosDias || {})[k] || '?') + ' dias)').join('; '));
    if (f.gratisAcima != null && f.gratisAcima !== '') ls.push(+f.gratisAcima > 0 ? '🎁 Frete grátis acima de ' + E.brlC(f.gratisAcima) : '🎁 Frete grátis para todo o Brasil');
    ls.push('📦 Envio em até ' + (pol.envioDiasUteis || 1) + ' dia(s) útil(eis) após o pagamento');
    ls.push('💳 ' + [pg.pixDescontoPct ? 'Pix com ' + pg.pixDescontoPct + '% de desconto' : 'Pix', pg.parcelas ? 'cartão em até ' + pg.parcelas + 'x' : null].filter(Boolean).join(', '));
    ls.push('🔁 ' + (pol.troca || ''));
    return ls.join('\n');
  };

  /* ---------- busca tolerante a erros ---------- */
  const STOP = new Set(('vcs voces voce vc tem tens tenho quero queria comprar compra um uma uns umas o a os as de do da dos das pra para por preco ' +
    'quanto custa custam valor estoque disponivel ai e me ver mostrar produto produtos algum alguma qual quais com sem no na em ' +
    'isso esse essa este esta sim nao ola oi bom dia boa tarde noite gostaria saber vende vendem por favor').split(' '));
  const NUMS = { um: 1, uma: 1, dois: 2, duas: 2, tres: 3, quatro: 4, cinco: 5, seis: 6, dez: 10 };
  E.lev = (a, b) => {
    if (Math.abs(a.length - b.length) > 2) return 3;
    let prev = Array.from({ length: b.length + 1 }, (_, i) => i);
    for (let i = 1; i <= a.length; i++) {
      const cur = [i];
      for (let j = 1; j <= b.length; j++) cur.push(Math.min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (a[i - 1] !== b[j - 1] ? 1 : 0)));
      prev = cur;
    }
    return prev[b.length];
  };
  const sing = (w) => (w.length > 4 && w.endsWith('s') ? w.slice(0, -1) : w);
  const palavras = (s) => U.norm(s).match(/[a-z0-9-]+/g) || [];
  E.buscar = (catalogo, texto) => {
    const n = U.norm(texto);
    const toks = palavras(texto).filter((w) => !STOP.has(w) && !/^\d+$/.test(w) && w.length >= 3).map(sing);
    let res = [];
    catalogo.forEach((c) => {
      const termos = new Set();
      [c.nome].concat(c.palavras || []).forEach((p) => palavras(p).forEach((w) => { if (w.length >= 3 && !STOP.has(w)) termos.add(sing(w)); }));
      let sc = 0;
      (c.palavras || []).forEach((p) => { if (p.includes(' ') && n.includes(U.norm(p))) sc += 3; });
      toks.forEach((q) => {
        let best = 0;
        for (const w of termos) {
          if (q === w) { best = 3; break; }
          if (q.length >= 4 && w.length >= 4 && (w.startsWith(q) || q.startsWith(w))) best = Math.max(best, 2);
          else if (q.length >= 4 && w.length >= 4 && E.lev(q, w) <= (q.length >= 7 ? 2 : 1)) best = Math.max(best, 2);
        }
        sc += best;
      });
      if (sc >= 2) res.push({ c, sc });
    });
    res.sort((a, b) => b.sc - a.sc || ((a.c.estoque <= 0) - (b.c.estoque <= 0)));
    if (res.length) { const topo = res[0].sc; res = res.filter((r) => r.sc >= Math.max(2, topo * 0.6)); }
    return res;
  };
  E.acharQtd = (texto) => {
    const n = U.norm(texto);
    const m = n.match(/\b(\d{1,2})\s*(?:x|un|unid|unidades|pecas)?\b(?!\s*(?:dias|%|reais|mil))/);
    if (m && !E.acharCep(texto) && +m[1] > 0) return +m[1];
    for (const k of Object.keys(NUMS)) if (new RegExp('\\b' + k + '\\b').test(n)) return NUMS[k];
    return null;
  };
  E.resumo = (catalogo, carrinho, pol, regiao, pagamento) => {
    const itens = [];
    Object.entries(carrinho || {}).forEach(([id, q]) => {
      const c = catalogo.find((x) => x.id === id);
      if (c && q > 0) itens.push({ id, nome: c.nome, qtd: q, preco: +c.preco, envioDias: c.envioDias || 1, pecasMin: +c.preco * q, pecasMax: +c.preco * q, maoMin: 0, maoMax: 0, duracao: 0 });
    });
    const sub = E.r2(itens.reduce((a, i) => a + i.preco * i.qtd, 0));
    const fr = regiao ? E.calcFrete(pol, sub, regiao) : null;
    const desc = pagamento === 'pix' ? E.r2(sub * (+(pol.pagamento || {}).pixDescontoPct || 0) / 100) : 0;
    return { itens, subtotal: sub, frete: fr, desconto: desc, total: E.r2(sub + (fr ? fr.valor : 0) - desc) };
  };

  /* ---------- cadastro do lojista pelo chat ---------- */
  const NUM = '(\\d{1,3}(?:\\.\\d{3})+(?:,\\d{1,2})?|\\d+(?:,\\d{1,2})?)';
  const preco = (s) => (s ? parseFloat(String(s).replace(/\./g, '').replace(',', '.')) : null);
  E.parseProduto = (chunk) => {
    let resto = ' ' + chunk + ' '; const out = { estoque: null, envioDias: null };
    const e = resto.match(/(?:estoque|qtd|quantidade)\s*:?\s*(\d+)|(\d+)\s*(?:unidades|unid|un|pe[çc]as|em estoque)\b/i);
    if (e) { out.estoque = +(e[1] || e[2]); resto = resto.replace(e[0], ' '); }
    const v = resto.match(/(?:entrega|envio|prazo|despacho|postagem|envia)\s*(?:em|de)?\s*(\d+)\s*(?:dias?|d)\b(?:\s*[uú]teis)?/i);
    if (v) { out.envioDias = +v[1]; resto = resto.replace(v[0], ' '); }
    const g = resto.match(new RegExp('r\\$\\s*' + NUM, 'i')) || resto.match(new RegExp('\\b' + NUM + '\\s*reais', 'i')) || resto.match(new RegExp('\\b' + NUM + '\\b'));
    if (!g) return null;
    const p = preco(g[1]); if (!p || p < 1) return null;
    resto = resto.replace(g[0], ' ');
    let nome = resto.replace(/r\$|\breais\b|\b(custa|por|valor|pre[çc]o|vendo|tenho|cada)\b/gi, ' ').replace(/[:=|•·()]/g, ' ').replace(/\s+/g, ' ').trim()
      .replace(/^[ ,.;-]+|[ ,.;-]+$/g, '').replace(/\s+(de|por|a|e|com|em)$/i, '');
    if (nome.length < 3) return null;
    return Object.assign(out, { nome: U.cap(nome), preco: E.r2(p), palavras: U.norm(nome).split(' ').filter((w) => w.length >= 4) });
  };
  const REG = '(sp|sao paulo|capital|sudeste|outros|outras regioes|demais regioes|demais|resto do brasil|brasil)';
  const regNome = (n) => (['sp', 'sao paulo', 'capital'].includes(n) ? 'SP' : n === 'sudeste' ? 'Sudeste' : 'Outros');
  E.parseEcom = (texto) => {
    const res = { nome: null, produtos: [], politicas: [], mudancas: {} };
    const nm = texto.match(/(?:se chama|chama-se|nome (?:da loja |do negócio |da empresa )?(?:é|e)|^\s*nome\s*:)\s*["“']?([^"”'\n;.!]+)/i);
    if (nm) res.nome = nm[1].trim().replace(/\s+/g, ' ');
    const ch = {};
    texto.split(/\n|;|\.\s+(?=\S)/).map((s) => s.trim()).filter(Boolean).forEach((b) => {
      const n = U.norm(b);
      if (nm && b.includes(nm[0].trim().slice(0, 12))) return;
      const reRegs = new RegExp('(?:frete\\s+)?(?:para |pra )?' + REG + '\\s*:?\\s*(?:r\\$\\s*)?' + NUM + '(?:\\s*(?:reais)?\\s*(?:em\\s*)?(\\d+)\\s*dias?)?', 'g');
      const regs = []; let m; while ((m = reRegs.exec(n))) regs.push([m[1], m[2], m[3]]);
      if (n.includes('frete') || (regs.length && !n.includes('estoque'))) {
        const f = ch.frete = ch.frete || {};
        const g = n.match(new RegExp('frete gratis (?:acima|a partir) de (?:r\\$\\s*)?' + NUM));
        if (g) { f.gratisAcima = preco(g[1]); res.politicas.push('🎁 Frete grátis acima de ' + E.brlC(f.gratisAcima)); }
        else if (/frete gratis/.test(n) && !regs.length) { f.gratisAcima = 0; res.politicas.push('🎁 Frete grátis para todo o Brasil'); }
        const fx = n.match(new RegExp('frete (?:fixo|unico)\\s*(?:de)?\\s*(?:r\\$\\s*)?' + NUM));
        if (fx) { f.tipo = 'fixo'; f.fixo = preco(fx[1]); res.politicas.push('🚚 Frete fixo ' + E.brlC(f.fixo)); }
        if (regs.length) {
          f.tipo = 'regiao';
          regs.forEach(([nr, val, dias]) => {
            const r = regNome(nr); (f.regioes = f.regioes || {})[r] = preco(val);
            if (dias) (f.prazosDias = f.prazosDias || {})[r] = +dias;
            res.politicas.push('🚚 Frete ' + r + ': ' + E.brlC(preco(val)) + (dias ? ' · ' + dias + ' dias' : ''));
          });
        }
        return;
      }
      if (/\bpix\b|cartao|parcel|chave|link de pagamento|boleto/.test(n)) {
        const pg = ch.pagamento = ch.pagamento || {};
        const d = n.match(/pix\D{0,25}?(\d{1,2})\s*%/) || n.match(/(\d{1,2})\s*%\D{0,25}pix/);
        if (d) { pg.pixDescontoPct = +d[1]; res.politicas.push('💸 Pix com ' + pg.pixDescontoPct + '% de desconto'); }
        const pc = n.match(/(\d{1,2})\s*x\b/) || n.match(/ate (\d{1,2}) vezes/);
        if (pc) { pg.parcelas = +pc[1]; res.politicas.push('💳 Cartão em até ' + pg.parcelas + 'x'); }
        const ck = b.match(/chave(?:\s+pix)?\s*(?:é|e|:|=)?\s*(.+)$/i);
        if (ck && ck[1].trim().length >= 5) { pg.pixChave = ck[1].trim().slice(0, 120); res.politicas.push('🔑 Chave Pix cadastrada'); }
        const lk = b.match(/(https?:\/\/\S+)/);
        if (lk && !ck) { pg.linkCartao = lk[1].slice(0, 200); res.politicas.push('🔗 Link de pagamento cadastrado'); }
        return;
      }
      if (/\btroca|devolu|arrependimento/.test(n) && !/r\$/.test(n)) { ch.troca = U.cap(b).slice(0, 400); res.politicas.push('🔁 Política de troca atualizada'); return; }
      const ev = n.match(/(?:envio|despacho|postagem|enviamos|postamos|despachamos)\D{0,15}(\d+)\s*dias?/);
      if (ev && !/r\$|estoque/.test(n)) { ch.envioDiasUteis = +ev[1]; res.politicas.push('📦 Envio em até ' + ch.envioDiasUteis + ' dia(s) útil(eis)'); return; }
      const p = E.parseProduto(b); if (p) res.produtos.push(p);
    });
    res.mudancas = ch;
    return res;
  };
  E.aplicarPoliticas = (pol, ch) => {
    Object.entries(ch).forEach(([k, v]) => {
      if (v && typeof v === 'object') { const alvo = pol[k] = pol[k] || {}; Object.entries(v).forEach(([kk, vv]) => { if (vv && typeof vv === 'object') alvo[kk] = Object.assign(alvo[kk] || {}, vv); else alvo[kk] = vv; }); }
      else pol[k] = v;
    });
  };
  /** aplica produtos e políticas no catálogo/políticas da demonstração; devolve as linhas de confirmação */
  E.aplicarCadastro = (res) => {
    const cat = S().catalogo('ecommerce'); const out = [];
    if (res.nome) { S().negocio('ecommerce').nome = res.nome.slice(0, 60); out.push('🏷️ Nome da loja: ' + res.nome); }
    res.produtos.forEach((p) => {
      const ex = cat.find((c) => U.norm(c.nome) === U.norm(p.nome));
      const alvo = ex || { id: U.norm(p.nome).replace(/[^a-z0-9]+/g, '-').slice(0, 20) + '-' + Math.random().toString(16).slice(2, 6), nome: p.nome, categoria: 'Cadastrado no chat', estoque: 10, envioDias: E.pol().envioDiasUteis || 1, palavras: [] };
      alvo.preco = p.preco; alvo.pecasMin = alvo.pecasMax = p.preco; alvo.maoMin = alvo.maoMax = 0; alvo.duracao = 0;
      if (p.estoque != null) alvo.estoque = p.estoque;
      if (p.envioDias != null) alvo.envioDias = p.envioDias;
      alvo.palavras = Array.from(new Set((alvo.palavras || []).concat(p.palavras))).sort();
      delete alvo.exemplo;
      if (!ex) cat.push(alvo);
      out.push((ex ? '✏️ Atualizei: ' : '✅ Cadastrei: ') + alvo.nome + ' · ' + E.brlC(alvo.preco) + ' · estoque ' + alvo.estoque + ' · envio ' + alvo.envioDias + ' dia(s)');
    });
    if (Object.keys(res.mudancas).length) { E.aplicarPoliticas(E.pol(), res.mudancas); out.push(...res.politicas); }
    return out;
  };

  AT.E = E;
})(window.AT);
