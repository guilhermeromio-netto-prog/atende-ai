/* Atende AI — conversa do cliente da Loja virtual (mesmo fluxo do bot do Telegram, simulado no navegador).
   Produtos/preço/estoque com busca tolerante a erros, carrinho, frete por CEP, fechamento com resumo,
   instruções de pagamento do lojista + “Já paguei”, rastreio, troca/devolução e atendente. */
(function (AT) {
  'use strict';
  const U = AT.U, M = AT.M, E = AT.E;
  const S = () => AT.S;
  const CE = {};
  const SEG = 'ecommerce';
  const MENU = [
    { rotulo: '🔎 Produtos e preços', valor: 'menu:produtos' }, { rotulo: '🚚 Frete e prazo', valor: 'menu:frete' },
    { rotulo: '🛒 Meu carrinho', valor: 'menu:carrinho' }, { rotulo: '📦 Rastrear pedido', valor: 'menu:rastreio' },
    { rotulo: '🔁 Troca/devolução', valor: 'menu:troca' }, { rotulo: '🙋 Falar com atendente', valor: 'atendente' }];
  const MOTIVOS = [{ rotulo: 'Defeito', valor: 'mot:Defeito' }, { rotulo: 'Arrependimento (7 dias)', valor: 'mot:Arrependimento (7 dias)' }, { rotulo: 'Produto errado', valor: 'mot:Produto errado' }, { rotulo: 'Outro motivo', valor: 'mot:Outro motivo' }];

  CE.iniciar = function () {
    const neg = S().negocio(SEG), def = S().segDef(SEG);
    const conv = { seg: SEG, etapa: 'menu', dados: {}, carrinho: {}, chat: [], pedidos: [], opcoes: def.exemplos.slice(), canal: S().st.canal || 'telegram', ticketId: null };
    conv.chat.push({ de: 'bot', ts: Date.now(), teclado: MENU, texto: 'Olá! 👋 Aqui é o atendimento automático da ' + neg.nome + ' 🛒\nPergunte do seu jeito: “tem fone bluetooth?”, “quanto é o frete pro meu CEP?”, “cadê meu pedido?”. Ou toque numa opção.\n\n🔒 Seus dados (nome, mensagens e pedidos) ficam na plataforma Atende AI e são usados só para este atendimento. Para apagar: /excluir_dados' });
    S().st.conversas[SEG] = conv; S().salvar();
    return conv;
  };
  /** conversa contínua + mensagens automáticas/atendente que os pedidos dessa conversa receberam depois */
  CE.msgs = function (conv) {
    const extra = [];
    (conv.pedidos || []).forEach((id) => { const t = S().ticket(id); if (t) t.chat.forEach((m) => { if ((m.de === 'auto' || m.de === 'atendente') && m.ts >= t.criado && !m.espelho) extra.push(m); }); });
    return extra.length ? conv.chat.concat(extra).sort((a, b) => a.ts - b.ts) : conv.chat;
  };
  CE.pedido = (conv) => (conv.pedidoAtual ? S().ticket(conv.pedidoAtual) : null);

  const linhaProd = (c) => '• ' + c.nome + ' — ' + E.brlC(c.preco) + ' · ' + (c.estoque > 0 ? '✅ ' + c.estoque + ' em estoque' : '❌ esgotado') + ' · envio em ' + (c.envioDias || 1) + ' dia(s) útil(eis)';
  function kbCarrinho(conv) {
    const u = conv.ultimo; const k = [];
    if (u && conv.carrinho[u]) k.push({ rotulo: '➕ 1', valor: 'inc:' + u }, { rotulo: '➖ 1', valor: 'dec:' + u });
    return k.concat([{ rotulo: '🔎 Continuar comprando', valor: 'menu:produtos' }, { rotulo: '✅ Fechar pedido', valor: 'checkout' }, { rotulo: '🗑️ Esvaziar', valor: 'limpar' }]);
  }
  function textoCarrinho(conv, r) {
    const ls = r.itens.map((i) => i.qtd + 'x ' + i.nome + ' — ' + E.brlC(i.preco * i.qtd));
    ls.push('Subtotal: ' + E.brlC(r.subtotal));
    const f = E.pol().frete || {};
    if (r.frete) ls.push('🚚 Frete (' + conv.dados.regiao + '): ' + (r.frete.gratis ? 'grátis 🎉' : E.brlC(r.frete.valor)));
    else if (f.gratisAcima != null && f.gratisAcima !== '') { const falta = +f.gratisAcima - r.subtotal; ls.push(falta <= 0 ? '🎁 Você já tem frete grátis!' : '🎁 Faltam ' + E.brlC(falta) + ' para frete grátis'); }
    return ls.join('\n');
  }
  function cartaoResumo(conv, r) {
    const d = conv.dados, pg = E.pol().pagamento || {};
    const linhas = r.itens.map((i) => '<tr><td>' + i.qtd + 'x ' + U.esc(i.nome) + '</td><td class="num">' + E.brlC(i.preco * i.qtd) + '</td></tr>').join('');
    return '<span class="orc__tag">Resumo automático · IA simulada</span><div class="orc"><h4>Resumo do pedido</h4><table><tbody>' + linhas +
      '<tr><td>Subtotal</td><td class="num">' + E.brlC(r.subtotal) + '</td></tr>' +
      '<tr><td>Frete (' + U.esc(d.cidade ? d.cidade + '/' + d.uf : d.regiao) + ')</td><td class="num">' + (r.frete.gratis ? 'grátis' : E.brlC(r.frete.valor)) + '</td></tr>' +
      (r.desconto ? '<tr><td>Desconto Pix (' + pg.pixDescontoPct + '%)</td><td class="num">−' + E.brlC(r.desconto) + '</td></tr>' : '') +
      '</tbody><tfoot><tr><td>Total</td><td class="num">' + E.brlC(r.total) + '</td></tr></tfoot></table></div>' +
      '<p>📦 Envio em até ' + E.envioDias(null, { itens: r.itens }) + ' dia(s) útil(eis) após o pagamento + ~' + r.frete.dias + ' dia(s) de transporte<br>🏠 ' + U.esc(d.endereco) + ' · CEP ' + U.esc(d.cep) + '<br>👤 ' + U.esc(d.cliente) + ' · ' + (d.pagamento === 'pix' ? 'Pix' : 'cartão' + (pg.parcelas ? ' (até ' + pg.parcelas + 'x)' : '')) + '</p>';
  }

  async function aplicarCep(conv, cep) {
    const info = await E.viacep(cep); const d = conv.dados;
    d.cep = cep; d.cidade = info ? info.cidade : ''; d.uf = info ? info.uf : ''; d.regiao = E.regiaoCep(cep, d.uf || null);
    return '📍 CEP ' + cep + ' · ' + (info ? d.cidade + '/' + d.uf + ' (consulta pública ViaCEP)' : 'região ' + d.regiao + ' (pelo 1º dígito do CEP)');
  }
  function textoFrete(conv) {
    const pol = E.pol(); const sub = Object.keys(conv.carrinho).length ? E.resumo(S().catalogo(SEG), conv.carrinho, pol, null, null).subtotal : 0;
    const fr = E.calcFrete(pol, sub, conv.dados.regiao); const f = pol.frete || {};
    let t = '🚚 Frete: ' + (fr.gratis ? 'grátis' : E.brlC(fr.valor)) + (sub ? ' (para o seu carrinho atual)' : '');
    if (!fr.gratis && f.gratisAcima != null && f.gratisAcima !== '' && +f.gratisAcima > 0) t += '\n🎁 Grátis em compras acima de ' + E.brlC(f.gratisAcima);
    return t + '\n📦 Prazo: envio em até ' + E.envioDias(pol) + ' dia(s) útil(eis) após o pagamento + cerca de ' + fr.dias + ' dia(s) útil(eis) de transporte.';
  }
  function intencao(n) {
    let melhor = null, pts = 0;
    S().segDef(SEG).intents.forEach((it) => { let s = 0; it.palavras.forEach((p) => { const q = U.norm(p); if (n.includes(q)) s += q.split(' ').length + 0.5; }); if (s > pts) { pts = s; melhor = it.id; } });
    return melhor;
  }
  function acharPedido(txt) {
    const m = U.norm(txt).match(/(?:ec-?)?\s*(\d{4,6})\b/); if (!m) return null;
    const t = S().ticket('EC-' + m[1]); return t && t.seg === SEG ? t : null;
  }
  const meusPedidos = (conv) => (conv.pedidos || []).map((id) => S().ticket(id)).filter((t) => t && t.tipo === 'pedido');

  function novoTicket(conv, extra) {
    const agora = Date.now();
    const t = Object.assign({
      id: S().novoId(SEG), seg: SEG, exemplo: false, canal: conv.canal || 'telegram', cliente: conv.dados.cliente || 'Cliente (demonstração)', telefone: '',
      veiculo: '', placa: '', bairro: '', servicos: [], opcionais: [], itens: [], total: { min: 0, max: 0 }, prioridade: 'media', status: 'Novo', criado: agora,
      humano: false, tempoRespostaSeg: Math.max(1, Math.round((agora - (conv.ultimaEntrada || agora)) / 1000)) || 1,
      chat: conv.chat.map((m) => Object.assign({}, m, { espelho: true })), eventos: [], historico: [{ status: 'Novo', ts: agora }]
    }, extra);
    S().st.tickets.unshift(t); conv.pedidos = (conv.pedidos || []).concat([t.id]);
    return t;
  }

  CE.processar = async function (texto, valor) {
    const conv = S().st.conversas[SEG] || CE.iniciar();
    if (valor === 'nova') { CE.iniciar(); return; }
    const out = (txt, extra) => conv.chat.push(Object.assign({ de: 'bot', texto: txt, ts: Date.now() }, extra || {}));
    const n = U.norm(texto); const cat = S().catalogo(SEG); const pol = E.pol(); const v = valor || '';
    const listar = (lista, titulo) => {
      if (!lista.length) return out('O catálogo ainda está vazio. Fale com um atendente:', { teclado: [MENU[5]] });
      conv.etapa = 'menu';
      const tec = lista.filter((c) => c.estoque > 0).slice(0, 6).map((c) => ({ rotulo: '🛒 ' + (c.nome.length > 28 ? c.nome.slice(0, 27).trim() + '…' : c.nome) + ' · ' + E.brlC(c.preco), valor: 'add:' + c.id }));
      if (Object.keys(conv.carrinho).length) tec.push({ rotulo: '✅ Fechar pedido', valor: 'checkout' });
      if (!tec.length) return out(titulo + '\n' + lista.slice(0, 10).map(linhaProd).join('\n') + '\n\nEsse item está esgotado no momento. Posso mostrar outros produtos ou chamar um atendente para avisar quando voltar.', { teclado: [MENU[0], MENU[5]] });
      out(titulo + '\n' + lista.slice(0, 10).map(linhaProd).join('\n') + '\n\nToque para adicionar ao carrinho:', { teclado: tec });
    };
    const carrinho = (prefixo) => {
      if (!Object.keys(conv.carrinho).length) return out((prefixo || '') + '🛒 Seu carrinho está vazio.', { teclado: [MENU[0]] });
      const r = E.resumo(cat, conv.carrinho, pol, conv.dados.regiao, null); conv.etapa = 'menu';
      out((prefixo || '') + '🛒 Seu carrinho\n' + textoCarrinho(conv, r), { teclado: kbCarrinho(conv) });
    };
    const add = (id, qtd) => {
      const c = cat.find((x) => x.id === id); if (!c) return out('Esse produto não está mais no catálogo.', { teclado: MENU });
      if (c.estoque <= 0) return out('😕 ' + c.nome + ' está esgotado no momento.', { teclado: [MENU[0], MENU[5]] });
      if (!Object.keys(conv.carrinho).length) E.metricas().carrinhos += 1;
      const nova = Math.min(c.estoque, (conv.carrinho[id] || 0) + qtd); conv.carrinho[id] = nova;
      conv.carrinhoEm = Date.now(); conv.lembrado = false; conv.ultimo = id;
      carrinho('✅ Adicionei ' + qtd + 'x ' + c.nome + (nova < qtd ? ' (limitei ao estoque: ' + c.estoque + ')' : '') + '.\n\n');
    };
    const pedirNumero = (modo) => {
      const meus = meusPedidos(conv).slice(0, 5); conv.etapa = modo === 'rastreio' ? 'rastreio' : 'troca_pedido';
      const tec = meus.map((t) => ({ rotulo: t.id + ' · ' + t.status, valor: (modo === 'rastreio' ? 'rt:' : 'tr:') + t.id }));
      if (modo === 'troca') tec.push({ rotulo: 'Não tenho o número', valor: 'tr-sem' });
      out((modo === 'rastreio' ? '📦 Qual o número do pedido? (ex.: EC-1029)' : '🔁 Vamos resolver. Qual o número do pedido? (ex.: EC-1028)') + (meus.length ? '\nOu toque num dos seus pedidos:' : ''), tec.length ? { teclado: tec } : {});
    };
    const mostrarPedido = (t) => {
      const ls = ['📦 Pedido ' + t.id + ' · status: ' + t.status, E.itensTexto(t.itens)];
      if (t.rastreio) ls.push('🔎 Código de rastreio: ' + t.rastreio);
      if (t.status === 'Pago' || t.status === 'Separando') ls.push('Envio previsto até ' + U.dataHora(t.prazo) + '.');
      if (t.tipo === 'troca') ls.push('Solicitação de troca/devolução' + (t.motivo ? ' · ' + t.motivo : ''));
      const tec = t.status === 'Aguardando pagamento' && (conv.pedidos || []).includes(t.id) ? [{ rotulo: '💸 Já paguei', valor: 'pago:' + t.id }] : null;
      out(ls.join('\n'), tec ? { teclado: tec } : {});
    };
    const checkout = () => {
      if (!Object.keys(conv.carrinho).length) return out('Seu carrinho está vazio. Vamos escolher algo?', { teclado: [MENU[0]] });
      const d = conv.dados;
      if (!d.cliente) { conv.etapa = 'checkout_nome'; return out('Para fechar o pedido, qual é o seu nome completo?'); }
      if (!d.cep) { conv.etapa = 'checkout_cep'; return out('📮 Qual o CEP de entrega? (ex.: 01310-100)'); }
      if (!d.endereco) { conv.etapa = 'checkout_endereco'; return out('🏠 Rua, número e complemento para a entrega:'); }
      if (!d.pagamento) {
        conv.etapa = 'checkout_pagamento'; const pg = pol.pagamento || {};
        return out('Como você prefere pagar?', { teclado: [{ rotulo: '⚡ Pix' + (pg.pixDescontoPct ? ' (' + pg.pixDescontoPct + '% de desconto)' : ''), valor: 'pg:pix' }, { rotulo: '💳 Cartão' + (pg.parcelas ? ' (até ' + pg.parcelas + 'x)' : ''), valor: 'pg:cartao' }] });
      }
      const r = E.resumo(cat, conv.carrinho, pol, d.regiao, d.pagamento); conv.etapa = 'confirmar';
      out('Resumo do pedido: total ' + E.brlC(r.total) + '.', { html: cartaoResumo(conv, r), teclado: [{ rotulo: '✅ Confirmar pedido', valor: 'confirmar' }, { rotulo: '✏️ Alterar carrinho', valor: 'menu:carrinho' }, MENU[5]] });
    };
    const confirmar = () => {
      const d = conv.dados;
      if (!Object.keys(conv.carrinho).length || !d.pagamento || !d.regiao) return checkout();
      const r = E.resumo(cat, conv.carrinho, pol, d.regiao, d.pagamento);
      for (const i of r.itens) { const c = cat.find((x) => x.id === i.id); if (i.qtd > c.estoque) return out('😕 Só restam ' + c.estoque + ' unidade(s) de ' + c.nome + '. Ajuste o carrinho:', { teclado: kbCarrinho(conv) }); }
      const agora = Date.now();
      const t = novoTicket(conv, {
        tipo: 'pedido', intent: 'comprar', problema: (conv.chat.find((m) => m.de === 'cliente') || {}).texto || 'Pedido pelo chat',
        servicos: r.itens.map((i) => i.id), itens: r.itens, subtotal: r.subtotal, frete: r.frete.valor, freteGratis: r.frete.gratis, freteDias: r.frete.dias,
        desconto: r.desconto, totalFinal: r.total, total: { min: r.total, max: r.total }, pagamento: d.pagamento, cep: d.cep, cidade: d.cidade || '', uf: d.uf || '',
        regiao: d.regiao, endereco: d.endereco, cliente: d.cliente, rastreio: ''
      });
      t.prazo = E.somaDiasUteis(agora, E.envioDias(pol, t) + 1, S().negocio(SEG).horario);
      conv.carrinho = {}; conv.pedidoAtual = t.id; conv.etapa = 'pagamento';
      M.mudarStatus(t, 'Aguardando pagamento', agora);
      const pg = pol.pagamento || {};
      let instr = '💰 Pagamento do pedido ' + t.id + ': ' + E.brlC(t.totalFinal) + '\n';
      if (t.pagamento === 'pix') instr += pg.pixChave ? 'Pague por Pix usando a chave cadastrada pela loja: ' + pg.pixChave + '\nDepois toque em “Já paguei”.' : 'A loja ainda não cadastrou a chave Pix. A equipe envia os dados de pagamento por esta conversa.';
      else instr += pg.linkCartao ? 'Pague no cartão pelo link da loja: ' + pg.linkCartao + '\nDepois toque em “Já paguei”.' : 'A equipe da loja envia o link de pagamento no cartão por esta conversa.';
      instr += '\nO pedido só é separado depois que a loja confirmar o pagamento.\n⚠️ Demonstração: nenhum pagamento real é feito ou processado aqui.';
      out(instr, { ts: Date.now() + 5, teclado: [{ rotulo: '💸 Já paguei', valor: 'pago:' + t.id }, MENU[5]] });
    };
    const abrirTroca = (motivo, detalhe) => {
      const ref = conv.dados.pedidoRef ? S().ticket(conv.dados.pedidoRef) : null;
      const t = novoTicket(conv, { tipo: 'troca', intent: 'troca', motivo, pedidoRef: ref ? ref.id : '', problema: motivo === 'Outro motivo' ? detalhe : motivo + (ref ? ' · pedido ' + ref.id : ''), itens: ref ? ref.itens : [], cliente: conv.dados.cliente || (ref && ref.cliente) || 'Cliente (demonstração)' });
      t.prazo = E.somaDiasUteis(t.criado, 2, S().negocio(SEG).horario);
      conv.etapa = 'menu'; delete conv.dados.pedidoRef;
      out('✅ Abri a solicitação ' + t.id + ' (' + motivo + ').\n\nNossa política: ' + (pol.troca || '') + '\n\nA equipe responde por aqui com as instruções de envio.', { teclado: MENU });
    };

    if (v === 'atendente' || (!v && /atendente|humano|falar com (alguem|uma pessoa)|pessoa de verdade/.test(n))) {
      let t = CE.pedido(conv);
      if (!t || ['Entregue', 'Resolvido'].includes(t.status) || t.tipo !== 'atendimento') {
        t = novoTicket(conv, { tipo: 'atendimento', intent: null, problema: texto, humano: true });
        t.prazo = U.somaUteis(t.criado, (S().st.sla[SEG].media || {}).respostaMin || 15, S().negocio(SEG).horario);
        conv.pedidoAtual = t.id;
      } else t.humano = true;
      conv.etapa = 'humano';
      out('Combinado! Chamei a equipe da ' + S().negocio(SEG).nome + '. A resposta chega em até ' + ((S().st.sla[SEG].media || {}).respostaMin || 15) + ' min em horário de atendimento. Protocolo: ' + t.id + '.', { teclado: [{ rotulo: '🔁 Nova conversa', valor: 'nova' }] });
      return S().salvar();
    }
    if (v.indexOf('menu:') === 0) {
      const op = v.slice(5);
      if (op === 'produtos') listar(cat.slice().sort((a, b) => (a.estoque <= 0) - (b.estoque <= 0)), '🗂️ Nossos produtos');
      else if (op === 'frete') { conv.etapa = 'cep'; conv.volta = 'frete'; out('📮 Qual é o seu CEP? (ex.: 01310-100)'); }
      else if (op === 'carrinho') carrinho();
      else pedirNumero(op === 'rastreio' ? 'rastreio' : 'troca');
      return S().salvar();
    }
    if (v.indexOf('add:') === 0) { add(v.slice(4), 1); return S().salvar(); }
    if (v.indexOf('inc:') === 0 || v.indexOf('dec:') === 0) {
      const id = v.slice(4); const c = cat.find((x) => x.id === id); const q = (conv.carrinho[id] || 0) + (v[0] === 'i' ? 1 : -1);
      if (c && q > c.estoque) out('Só temos ' + c.estoque + ' unidade(s) de ' + c.nome + ' em estoque.', { teclado: kbCarrinho(conv) });
      else { if (q <= 0) delete conv.carrinho[id]; else conv.carrinho[id] = q; conv.carrinhoEm = Date.now(); conv.lembrado = false; carrinho(); }
      return S().salvar();
    }
    if (v === 'limpar') { conv.carrinho = {}; out('🗑️ Carrinho esvaziado.', { teclado: MENU }); return S().salvar(); }
    if (v === 'checkout') { checkout(); return S().salvar(); }
    if (v.indexOf('pg:') === 0) { conv.dados.pagamento = v.slice(3); checkout(); return S().salvar(); }
    if (v === 'confirmar') { confirmar(); return S().salvar(); }
    if (v.indexOf('pago:') === 0) {
      const t = S().ticket(v.slice(5));
      if (t && t.status === 'Aguardando pagamento') {
        t.pagamentoInformadoEm = Date.now(); t.chat.push({ de: 'cliente', texto: 'Já paguei', ts: Date.now() });
        out('Obrigado! 🙌 Avisei a loja. Assim que o pagamento for conferido, você recebe a confirmação aqui.\n(Na demonstração, confirme em Pedidos → ' + t.id + ' → “Confirmar pagamento”.)');
      } else if (t) out('O pedido ' + t.id + ' está como ' + t.status + '.');
      return S().salvar();
    }
    if (v.indexOf('rt:') === 0) { const t = S().ticket(v.slice(3)); if (t) mostrarPedido(t); return S().salvar(); }
    if (v.indexOf('tr:') === 0) { conv.dados.pedidoRef = v.slice(3); conv.etapa = 'troca_motivo'; out('Qual o motivo da troca/devolução do pedido ' + v.slice(3) + '?', { teclado: MOTIVOS }); return S().salvar(); }
    if (v === 'tr-sem') { conv.dados.pedidoRef = ''; conv.etapa = 'troca_motivo'; out('Sem problema. Qual o motivo?', { teclado: MOTIVOS }); return S().salvar(); }
    if (v.indexOf('mot:') === 0) { abrirTroca(v.slice(4), texto); return S().salvar(); }

    const et = conv.etapa; const cep = E.acharCep(texto);
    if ((et === 'cep' || et === 'checkout_cep') && cep) {
      const info = await aplicarCep(conv, cep);
      if (et === 'checkout_cep' || conv.volta === 'checkout') { out(info); checkout(); }
      else { conv.etapa = 'menu'; out(info + '\n' + textoFrete(conv), { teclado: [MENU[0], MENU[2]] }); }
      return S().salvar();
    }
    if (et === 'checkout_nome' && texto.length >= 2 && !cep) {
      conv.dados.cliente = texto.replace(/^(meu nome (é|e)|me chamo|sou (o|a))\s+/i, '').trim().split(/\s+/).slice(0, 4).map(U.cap).join(' ').slice(0, 60);
      checkout(); return S().salvar();
    }
    if (et === 'checkout_endereco' && texto.length >= 5) { conv.dados.endereco = texto.trim().slice(0, 160); checkout(); return S().salvar(); }
    if (et === 'checkout_pagamento' && /pix|cart/.test(n)) { conv.dados.pagamento = /pix/.test(n) ? 'pix' : 'cartao'; checkout(); return S().salvar(); }
    if (et === 'confirmar' && /^(sim|confirmo|confirmar|pode|ok|fechado|isso)/.test(n)) { confirmar(); return S().salvar(); }
    if (et === 'rastreio') { const t = acharPedido(texto); if (t) { conv.etapa = 'menu'; mostrarPedido(t); return S().salvar(); } }
    if (et === 'troca_pedido') {
      const t = acharPedido(texto);
      if (t || /nao (tenho|sei|lembro)/.test(n)) { conv.dados.pedidoRef = t ? t.id : ''; conv.etapa = 'troca_motivo'; out('Qual o motivo da troca/devolução?', { teclado: MOTIVOS }); return S().salvar(); }
    }
    if (et === 'troca_motivo' && texto.length >= 3) { abrirTroca('Outro motivo', texto); return S().salvar(); }

    const it = intencao(n); const achados = E.buscar(cat, texto);
    if (it === 'rastreio') { const t = acharPedido(texto); if (t) mostrarPedido(t); else pedirNumero('rastreio'); return S().salvar(); }
    if (it === 'troca') { pedirNumero('troca'); return S().salvar(); }
    if (it === 'frete' && !achados.length) {
      if (cep) { const info = await aplicarCep(conv, cep); out(info + '\n' + textoFrete(conv), { teclado: [MENU[0], MENU[2]] }); }
      else { conv.etapa = 'cep'; conv.volta = 'frete'; out('📮 Me passa o seu CEP que eu calculo o frete e o prazo. (ex.: 01310-100)'); }
      return S().salvar();
    }
    if (it === 'pagamento' && !achados.length) { out('💳 Formas de pagamento\n' + (E.textoPoliticas(pol).split('\n').find((l) => l.indexOf('💳') === 0) || 'Pix ou cartão') + '\nO pagamento é combinado com a loja depois que você confirma o pedido.', { teclado: MENU }); return S().salvar(); }
    if (achados.length) {
      const qtd = E.acharQtd(texto);
      if ((it === 'comprar' && achados.length === 1) || (qtd && achados[0].sc >= 3 && (achados.length === 1 || achados[0].sc > achados[1].sc))) add(achados[0].c.id, qtd || 1);
      else listar(achados.slice(0, 6).map((a) => a.c), '🔎 Encontrei:');
      return S().salvar();
    }
    if (it === 'comprar') { if (Object.keys(conv.carrinho).length) carrinho(); else listar(cat, '🛒 Ótimo! Escolha o produto:'); return S().salvar(); }
    if (cep) { const info = await aplicarCep(conv, cep); out(info + '\n' + textoFrete(conv), { teclado: MENU }); return S().salvar(); }
    out('Não encontrei isso no catálogo. Posso te mostrar os produtos ou ajudar com frete, pedido e troca:', { teclado: MENU });
    S().salvar();
  };

  /** carrinho abandonado (modo teste: 10 min) — chamado pelo relógio da página */
  CE.vigiar = function () {
    const conv = S().st && S().st.conversas[SEG];
    if (!conv || conv.lembrado || !conv.carrinhoEm || !Object.keys(conv.carrinho || {}).length) return false;
    if (Date.now() - conv.carrinhoEm < 10 * 60000) return false;
    conv.lembrado = true; E.metricas().abandonados += 1;
    const r = (S().st.automacoes[SEG] || []).find((x) => x.id === 'carrinho');
    if (r && r.ativo) {
      const itens = E.itensTexto(E.resumo(S().catalogo(SEG), conv.carrinho, E.pol(), null, null).itens);
      conv.chat.push({ de: 'auto', regra: 'carrinho', ts: Date.now(), texto: U.template(r.template, { negocio: S().negocio(SEG).nome, servico: itens, cliente: '' }), teclado: [MENU[2], { rotulo: '✅ Fechar pedido', valor: 'checkout' }] });
    }
    S().salvar(); return true;
  };
  CE.MENU = MENU;
  AT.ConversaEcom = CE;
})(window.AT);
