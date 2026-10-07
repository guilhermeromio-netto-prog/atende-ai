/* Atende AI — motor de conversa do cliente final (independente de canal).
   Simulação por regras: intenção por palavras-chave (dados.json), perguntas de acompanhamento,
   orçamento a partir do catálogo, SLA e abertura de pedido. Não há IA real. */
(function (AT) {
  'use strict';
  const U = AT.U, M = AT.M;
  const S = () => AT.S;
  const C = {};
  const BT_APROVAR = { rotulo: '✅ Aprovar orçamento', valor: 'aprovar' };
  const BT_HUMANO = { rotulo: '🙋 Falar com atendente', valor: 'atendente' };
  const BT_NOVA = { rotulo: '🔁 Nova conversa', valor: 'nova' };

  C.iniciar = function (seg) {
    const neg = S().negocio(seg), def = S().segDef(seg), ts = Date.now();
    const conv = { etapa: 'problema', campo: null, dados: {}, intent: null, confianca: 0, ticketId: null, chat: [], opcoes: def.exemplos.slice(), canal: S().st.canal || 'telegram' };
    conv.chat.push({ de: 'bot', ts, texto: 'Olá! 👋 Aqui é o atendimento automático da ' + neg.nome + '. ' + (seg === 'oficina' ? 'Me conte o que está acontecendo com o seu carro, do seu jeito.' : 'Me conte o que você precisa, do seu jeito.') });
    S().st.conversas[seg] = conv; S().salvar();
    return conv;
  };
  C.estado = (seg) => S().st.conversas[seg] || C.iniciar(seg);
  C.ticket = (conv) => (conv.ticketId ? S().ticket(conv.ticketId) : null);
  C.msgs = (conv) => (C.ticket(conv) || conv).chat;

  C.receber = function (seg, texto) {
    const conv = C.estado(seg);
    C.msgs(conv).push({ de: 'cliente', texto, ts: Date.now() });
    conv.opcoes = []; conv.ultimaEntrada = Date.now();
    S().salvar();
  };

  function criarTicket(conv, seg, problema) {
    const agora = Date.now(); const it = conv.intent;
    const t = {
      id: S().novoId(seg), seg, exemplo: false, canal: conv.canal || 'telegram',
      cliente: conv.dados.cliente || 'Cliente (demonstração)', telefone: '', veiculo: conv.dados.veiculo || '', placa: conv.dados.placa || '', bairro: conv.dados.bairro || '',
      problema, intent: it ? it.id : null, servicos: it ? it.servicos.slice() : [], opcionais: it ? it.opcionais.slice() : [],
      prioridade: conv.dados.urgencia || (it ? it.prioridade : 'media'), status: 'Novo', criado: agora, humano: false,
      tempoRespostaSeg: Math.max(1, Math.round((agora - (conv.ultimaEntrada || agora)) / 1000)),
      chat: conv.chat.slice(), eventos: [], historico: [{ status: 'Novo', ts: agora }], itens: [], total: { min: 0, max: 0 }
    };
    const orc = M.orcamento(seg, t.servicos, t.veiculo);
    t.itens = orc.itens; t.total = orc.total; t.prazo = M.calcPrazo(seg, t.prioridade, agora, orc.duracao);
    S().st.tickets.unshift(t); conv.ticketId = t.id; conv.chat = [];
    return t;
  }
  function sync(conv, t) {
    if (!t) return;
    ['cliente', 'veiculo', 'placa', 'bairro'].forEach((k) => { if (conv.dados[k] != null && conv.dados[k] !== '') t[k] = conv.dados[k]; });
    if (conv.dados.urgencia) t.prioridade = conv.dados.urgencia;
  }
  function tecladoPergunta(campo) {
    if (campo === 'urgencia') return [{ rotulo: '🚨 Hoje, é urgente', valor: 'urg:alta' }, { rotulo: '📅 Nesta semana', valor: 'urg:media' }, { rotulo: '🙂 Sem pressa', valor: 'urg:baixa' }];
    if (campo === 'placa') return [{ rotulo: 'Pular', valor: 'pular' }];
    if (campo === 'bairro') return [{ rotulo: '🏬 Vou retirar na loja', valor: 'retirar' }];
    return null;
  }
  function perguntar(conv, seg, out, prefixo) {
    const p = S().segDef(seg).perguntas.find((q) => conv.dados[q.campo] == null);
    if (!p) return orcar(conv, seg, out, prefixo);
    conv.etapa = 'pergunta'; conv.campo = p.campo;
    const texto = (prefixo ? prefixo + ' ' : '') + p.texto.replace(/ ?Se preferir, digite "pular"\.| ?Se for retirar na loja, digite "retirar"\./, '');
    const tec = tecladoPergunta(p.campo);
    out(texto, tec ? { teclado: tec } : {});
  }
  function cartaoOrcamento(t, seg) {
    const rot = S().segDef(seg).rotulos; const cat = S().catalogo(seg);
    const linhas = t.itens.map((i) => '<tr><td>' + U.esc(i.nome) + '</td><td class="num">' + U.faixaT(i.pecasMin, i.pecasMax) + '</td><td class="num">' + U.faixaT(i.maoMin, i.maoMax) + '</td></tr>').join('');
    const dur = t.itens.reduce((a, i) => a + (+i.duracao || 0), 0);
    const opc = (t.opcionais || []).map((id) => cat.find((c) => c.id === id)).filter(Boolean);
    return '<span class="orc__tag">Orçamento automático · IA simulada</span><div class="orc"><h4>Orçamento ' + U.esc(t.id) + '</h4>' +
      '<table><thead><tr><th>Item</th><th class="num">' + U.esc(rot.pecas) + '</th><th class="num">' + U.esc(rot.mao) + '</th></tr></thead><tbody>' + linhas + '</tbody>' +
      '<tfoot><tr><td>Total estimado</td><td class="num" colspan="2">' + U.faixa(t.total.min, t.total.max) + '</td></tr></tfoot></table></div>' +
      '<p>⏱️ Duração estimada: ' + U.dur(dur) + '<br>📅 Prazo combinado: ' + U.dataHora(t.prazo) + ' (prioridade ' + S().dados.prioridades[t.prioridade].toLowerCase() + ')</p>' +
      (t.ajuste ? '<p>ℹ️ ' + U.esc(t.ajuste) + '</p>' : '') +
      (opc.length ? '<p>🔎 Pode ser necessário, só com sua autorização: ' + opc.map((c) => U.esc(c.nome) + ' (' + U.faixa(c.pecasMin + c.maoMin, c.pecasMax + c.maoMax) + ')').join('; ') + '.</p>' : '') +
      '<p class="pequeno">Valores estimados, confirmados ' + (seg === 'oficina' ? 'após avaliação do carro' : 'na separação do pedido') + '. Válido por 7 dias.</p>';
  }
  function orcar(conv, seg, out, prefixo) {
    const t = C.ticket(conv); sync(conv, t);
    if (seg === 'loja' && conv.dados.bairro != null) {
      const retira = conv.dados.bairro === 'Retirada na loja';
      if (retira) t.servicos = t.servicos.filter((id) => id !== 'entrega');
      else if (!t.servicos.includes('entrega') && S().catalogo(seg).some((c) => c.id === 'entrega')) t.servicos.push('entrega');
      t.opcionais = (t.opcionais || []).filter((id) => !t.servicos.includes(id) && id !== 'entrega');
    }
    const orc = M.orcamento(seg, t.servicos, t.veiculo);
    t.itens = orc.itens; t.total = orc.total; t.ajuste = orc.ajuste;
    t.prazo = M.calcPrazo(seg, t.prioridade, Date.now(), orc.duracao);
    if (prefixo) out(prefixo + ' Montei seu orçamento:');
    M.mudarStatus(t, 'Orçado', Date.now(), { pularChat: ['orcamento'] });
    out('Orçamento ' + t.id + ': ' + U.faixa(t.total.min, t.total.max) + ', prazo ' + U.dataHora(t.prazo) + '.', { html: cartaoOrcamento(t, seg), teclado: [BT_APROVAR, BT_HUMANO] });
    conv.etapa = 'orcado';
  }
  function humano(conv, seg, problema, out) {
    let t = C.ticket(conv);
    if (!t) t = criarTicket(conv, seg, problema);
    t.humano = true; sync(conv, t);
    const sla = S().st.sla[seg][t.prioridade] || S().st.sla[seg].media;
    out('Combinado! Chamei um atendente da ' + S().negocio(seg).nome + '. Pela nossa regra de SLA, a resposta chega em até ' + sla.respostaMin + ' min. Seu protocolo é ' + t.id + '.', { teclado: [BT_NOVA] });
    conv.etapa = 'humano';
  }

  C.processar = function (seg, texto, valor) {
    let conv = C.estado(seg);
    if (valor === 'nova') { C.iniciar(seg); return; }
    const out = (txt, extra) => C.msgs(conv).push(Object.assign({ de: 'bot', texto: txt, ts: Date.now() }, extra || {}));
    const n = U.norm(texto);
    if (valor === 'atendente' || (!valor && /atendente|humano|falar com (alguem|uma pessoa)|pessoa de verdade/.test(n))) { humano(conv, seg, texto, out); S().salvar(); return; }
    const ext = M.extrair(seg, texto);
    const cat = S().catalogo(seg);
    switch (conv.etapa) {
      case 'problema': {
        let det = null;
        if (valor && valor.indexOf('serv:') === 0) {
          const c = cat.find((x) => x.id === valor.slice(5));
          if (c) det = { intent: { id: 'cat-' + c.id, rotulo: c.nome, servicos: [c.id], opcionais: [], prioridade: 'media', explicacao: 'Certo: ' + c.nome + '. Duração média de ' + U.dur(c.duracao) + '.' }, confianca: 0.95 };
        } else det = M.detectar(seg, texto);
        if (!det) {
          out('Ainda não tenho certeza do que é. Qual destas opções é mais parecida?', { teclado: cat.slice(0, 6).map((c) => ({ rotulo: c.nome, valor: 'serv:' + c.id })).concat([BT_HUMANO]) });
          break;
        }
        Object.keys(ext).forEach((k) => { if (conv.dados[k] == null) conv.dados[k] = ext[k]; });
        conv.intent = det.intent; conv.confianca = det.confianca;
        criarTicket(conv, seg, texto);
        const achados = [ext.veiculo && 'veículo ' + ext.veiculo, ext.placa && 'placa ' + ext.placa].filter(Boolean);
        out(det.intent.explicacao + (achados.length ? ' Já anotei: ' + achados.join(', ') + '.' : ''));
        perguntar(conv, seg, out);
        break;
      }
      case 'pergunta': {
        const campo = conv.campo; let prefixo = '';
        if (campo === 'cliente') {
          const nome = ext.cliente || texto.replace(/^(oi|olá|ola)[,!. ]*/i, '').replace(/^(meu nome (é|e)|me chamo|sou (o|a)|é|e)\s+/i, '').trim().split(/\s+/).slice(0, 3).map(U.cap).join(' ').replace(/[^A-Za-zÀ-ú '-]/g, '');
          if (nome.length < 2) { out('Não peguei seu nome. Pode escrever de novo?'); break; }
          conv.dados.cliente = nome; prefixo = 'Prazer, ' + U.primeiroNome(nome) + '!';
        } else if (campo === 'veiculo') {
          conv.dados.veiculo = ext.veiculo || U.cap(texto.trim()).slice(0, 40);
          if (ext.placa && conv.dados.placa == null) conv.dados.placa = ext.placa;
          prefixo = 'Anotado: ' + conv.dados.veiculo + '.';
        } else if (campo === 'placa') {
          if (valor === 'pular' || /pular|nao sei|nao tenho|depois|sem placa/.test(n)) conv.dados.placa = '';
          else if (ext.placa) conv.dados.placa = ext.placa;
          else { out('Não reconheci a placa. Use o formato ABC1D23 ou ABC-1234, ou toque em Pular.', { teclado: tecladoPergunta('placa') }); break; }
        } else if (campo === 'bairro') {
          conv.dados.bairro = valor === 'retirar' || /retir/.test(n) ? 'Retirada na loja' : U.cap(texto.trim()).slice(0, 40);
        } else if (campo === 'urgencia') {
          conv.dados.urgencia = valor && valor.indexOf('urg:') === 0 ? valor.slice(4) : (M.urgenciaDeResposta(texto) || 'media');
        }
        Object.keys(ext).forEach((k) => { if (conv.dados[k] == null && k !== 'cliente') conv.dados[k] = ext[k]; });
        sync(conv, C.ticket(conv));
        perguntar(conv, seg, out, prefixo);
        break;
      }
      case 'orcado': {
        if (valor === 'aprovar' || /^(sim|aprovo|aprovar|aprovado|ok|pode fazer|pode|fechado|bora|quero)/.test(n)) {
          const t = C.ticket(conv);
          M.mudarStatus(t, 'Aprovado');
          const slots = U.proximosHorarios(Date.now(), S().negocio(seg).horario, 3);
          out(seg === 'oficina' ? 'Escolha o melhor horário para trazer o carro:' : 'Escolha quando quer receber ou retirar:', { teclado: slots.map((s) => ({ rotulo: '📅 ' + U.dataHora(s), valor: 'slot:' + s })).concat([BT_HUMANO]) });
          conv.etapa = 'agendar';
        } else out('Quer seguir com o orçamento? É só tocar em um dos botões.', { teclado: [BT_APROVAR, BT_HUMANO] });
        break;
      }
      case 'agendar': {
        const t = C.ticket(conv);
        if (valor && valor.indexOf('slot:') === 0) {
          const ts = +valor.slice(5); t.agendamento = ts;
          t.eventos.filter((e) => e.regra === 'lembrete').forEach((e) => { e.ts = ts - 2 * 3600000; });
          out('📅 Agendado para ' + U.dataHora(ts) + '. Vou te mandar um lembrete antes. Protocolo: ' + t.id + '. Qualquer dúvida, é só escrever aqui.', { teclado: [BT_NOVA] });
          conv.etapa = 'fim';
        } else {
          const slots = U.proximosHorarios(Date.now(), S().negocio(seg).horario, 3);
          out('Pra confirmar, toque em um dos horários:', { teclado: slots.map((s) => ({ rotulo: '📅 ' + U.dataHora(s), valor: 'slot:' + s })) });
        }
        break;
      }
      default: {
        const t = C.ticket(conv);
        out('Seu atendimento ' + (t ? t.id + ' ' : '') + 'já está registrado e a equipe acompanha pelo painel. Para um novo assunto, toque em Nova conversa.', { teclado: [BT_NOVA] });
      }
    }
    S().salvar();
  };
  AT.Conversa = C;
})(window.AT);
