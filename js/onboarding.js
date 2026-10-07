/* Atende AI — chat compartilhado + onboarding do dono do negócio */
(function (AT) {
  'use strict';
  const U = AT.U;

  /* ---------- onboarding ---------- */
  const S = () => AT.S;
  function estado() {
    const seg = S().seg();
    if (!S().st.onboarding[seg]) {
      const def = S().segDef(seg);
      S().st.onboarding[seg] = { chat: [
        { de: 'bot', ts: Date.now(), texto: 'Oi! Sou o assistente de cadastro do Atende AI. Vou montar o seu catálogo conversando com você.' },
        { de: 'bot', ts: Date.now(), texto: seg === 'ecommerce'
          ? 'Me conte, do jeito que você fala: o nome da loja, cada produto com preço, estoque e prazo de envio, e as suas políticas (frete, Pix, cartão, trocas). Pode mandar uma coisa por linha.\nExemplo: "' + def.onboardingExemplos[1] + '"'
          : 'Me conte, do jeito que você fala: o nome do ' + (seg === 'oficina' ? 'negócio' : 'seu comércio') + ', cada serviço com preço e duração, e o horário de funcionamento. Pode mandar uma coisa por linha.\nExemplo: "' + def.onboardingExemplos[1] + '"' }
      ] };
    }
    return S().st.onboarding[seg];
  }
  const slug = (s) => U.norm(s).replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '').slice(0, 24);

  function aplicar(res) {
    const seg = S().seg(); const neg = S().negocio(); const cat = S().catalogo();
    const linhas = []; const novos = [];
    if (res.nome) { neg.nome = res.nome; linhas.push('🏷️ Nome do negócio: ' + res.nome); }
    res.servicos.forEach((sv) => {
      const ex = cat.find((c) => U.norm(c.nome) === U.norm(sv.nome));
      const alvo = ex || { id: slug(sv.nome) + '-' + Math.random().toString(36).slice(2, 6), nome: sv.nome, categoria: 'Cadastrado no chat', pecasMin: 0, pecasMax: 0, maoMin: 0, maoMax: 0, duracao: 60, palavras: [] };
      ['pecasMin', 'pecasMax', 'maoMin', 'maoMax'].forEach((k) => { if (sv.pecasMin || sv.pecasMax || sv.maoMin || sv.maoMax) alvo[k] = sv[k]; });
      if (sv.duracao) alvo.duracao = sv.duracao;
      alvo.palavras = Array.from(new Set((alvo.palavras || []).concat(sv.palavras)));
      if (!ex) { cat.push(alvo); novos.push(alvo.id); }
      const tot = U.faixa(alvo.pecasMin + alvo.maoMin, alvo.pecasMax + alvo.maoMax);
      linhas.push((ex ? '✏️ Atualizei: ' : '✅ Cadastrei: ') + alvo.nome + ' · ' + tot + ' · ' + U.dur(alvo.duracao));
    });
    res.horarios.forEach((h) => {
      h.dias.forEach((d) => { neg.horario[d] = h.fechado ? null : [h.abre, h.fecha]; });
      linhas.push('🕗 ' + h.dias.map((d) => U.diasCurto[d]).join(', ') + ': ' + (h.fechado ? 'fechado' : h.abre + ' às ' + h.fecha));
    });
    S().salvar();
    return { linhas, novos, seg };
  }

  /* ---------- loja virtual: políticas editáveis ---------- */
  function cartaoPoliticas() {
    const p = AT.E.pol(); const f = p.frete || {}; const pg = p.pagamento || {}; const rg = f.regioes || {}; const pz = f.prazosDias || {};
    const num = (id, rot, v, step) => '<label class="campo">' + rot + '<input class="inp num" type="number" min="0" step="' + (step || '0.01') + '" id="' + id + '" value="' + (v == null || v === '' ? '' : v) + '"></label>';
    return '<section class="card ficha" aria-labelledby="h-pol" style="margin-top:16px"><h2 id="h-pol">Políticas da loja</h2>' +
      '<p class="pequeno muted" style="margin:0 0 10px">O assistente usa estas regras no frete, no resumo do pedido e nas trocas. Nenhum pagamento é processado: o cliente recebe a chave Pix/link que você cadastrar.</p>' +
      '<div class="pol-grid">' +
      '<label class="campo">Tipo de frete<select class="inp" id="pol-tipo"><option value="regiao"' + (f.tipo !== 'fixo' ? ' selected' : '') + '>Tabela por região (CEP)</option><option value="fixo"' + (f.tipo === 'fixo' ? ' selected' : '') + '>Frete fixo</option></select></label>' +
      num('pol-fixo', 'Frete fixo (R$)', f.fixo) + num('pol-gratis', 'Frete grátis acima de (R$, vazio = nunca)', f.gratisAcima) +
      ['SP', 'Sudeste', 'Outros'].map((r) => num('pol-r-' + r, 'Frete ' + r + ' (R$)', rg[r]) + num('pol-d-' + r, 'Transporte ' + r + ' (dias)', pz[r], '1')).join('') +
      num('pol-envio', 'Envio após pagamento (dias úteis)', p.envioDiasUteis, '1') + num('pol-pix', 'Desconto no Pix (%)', pg.pixDescontoPct, '1') + num('pol-parc', 'Parcelas no cartão (até)', pg.parcelas, '1') +
      '<label class="campo">Chave Pix (texto que o cliente vê)<input class="inp" id="pol-chave" maxlength="120" value="' + U.esc(pg.pixChave || '') + '" placeholder="ex.: e-mail, CNPJ ou chave aleatória"></label>' +
      '<label class="campo">Link de pagamento no cartão<input class="inp" id="pol-link" maxlength="200" value="' + U.esc(pg.linkCartao || '') + '" placeholder="https://…"></label>' +
      '</div><label class="campo" style="margin-top:8px">Política de troca e devolução<textarea class="inp" id="pol-troca" rows="3">' + U.esc(p.troca || '') + '</textarea></label></section>';
  }
  function ligarPoliticas(main) {
    const p = AT.E.pol(); const g = (id) => main.querySelector('#' + id);
    const n = (id) => { const v = g(id).value.trim(); return v === '' ? null : Math.max(0, +v); };
    main.querySelectorAll('[id^="pol-"]').forEach((el) => el.addEventListener('change', () => {
      p.frete = p.frete || {}; p.pagamento = p.pagamento || {};
      p.frete.tipo = g('pol-tipo').value; p.frete.fixo = n('pol-fixo') || 0;
      const ga = n('pol-gratis'); if (ga == null) delete p.frete.gratisAcima; else p.frete.gratisAcima = ga;
      p.frete.regioes = p.frete.regioes || {}; p.frete.prazosDias = p.frete.prazosDias || {};
      ['SP', 'Sudeste', 'Outros'].forEach((r) => { p.frete.regioes[r] = n('pol-r-' + r) || 0; p.frete.prazosDias[r] = Math.round(n('pol-d-' + r) || 1); });
      p.envioDiasUteis = Math.max(1, Math.round(n('pol-envio') || 1));
      p.pagamento.pixDescontoPct = Math.round(n('pol-pix') || 0); p.pagamento.parcelas = Math.round(n('pol-parc') || 0);
      p.pagamento.pixChave = g('pol-chave').value.trim(); p.pagamento.linkCartao = g('pol-link').value.trim();
      p.troca = g('pol-troca').value.trim();
      S().salvar(); U.toast('Políticas salvas');
    }));
  }

  function termo() {
    const ac = S().st.termoAceitoEm;
    if (ac) return '<p class="termo-ok pequeno" role="status">📄 Termo de uso do piloto aceito em ' + U.dataHora(ac) + ' · <a href="#/privacidade">ler de novo</a></p>';
    return '<section class="card termo" aria-labelledby="ob-termo-t"><h2 id="ob-termo-t" class="h3">📄 Termo de uso do piloto</h2><ul>' +
      AT.Privacidade.TERMO.map((t) => '<li>' + U.esc(t) + '</li>').join('') + '</ul>' +
      '<div class="termo__acoes"><button type="button" class="btn btn--pri btn--p" id="ob-termo-ok">✅ Aceito</button><a class="btn btn--p" href="#/privacidade">Ler a política completa</a></div>' +
      '<p class="pequeno muted">No bot real, este aceite é obrigatório antes de criar ou assumir uma loja e fica registrado com data e hora.</p></section>';
  }
  function ligarTermo(main) {
    const b = main.querySelector('#ob-termo-ok');
    if (b) b.addEventListener('click', () => { S().st.termoAceitoEm = Date.now(); S().salvar(); main.querySelector('#ob-termo').innerHTML = termo(); U.toast('Termo do piloto aceito.'); const t = main.querySelector('#ob-termo .termo-ok'); if (t) { t.tabIndex = -1; t.focus(); } });
  }

  function render(main) {
    const seg = S().seg(); const def = S().segDef(seg); const ob = estado(); const ecom = seg === 'ecommerce';
    main.innerHTML = `
      <div class="cab"><div><div class="olho">Passo 1 · Cadastro pelo chat</div><h1>Converse com o assistente e monte seu catálogo</h1>
      <p>${ecom ? 'O lojista conversa com o bot do Telegram como fala no dia a dia. O assistente (simulado por regras) extrai produto, preço, estoque, prazo de envio e as políticas de frete, pagamento e troca, e preenche as tabelas. Tudo pode ser corrigido à mão.' : 'O dono do negócio conversa com o bot do Telegram como fala no dia a dia. O assistente (simulado por regras) extrai serviço, preço, duração e horário, e preenche as tabelas ao lado. Tudo pode ser corrigido à mão.'}</p></div></div>
      <div id="ob-termo">${termo()}</div>
      <div class="duas duas--chat">
        ${AT.Chat.moldura({ id: 'ob-chat', avatar: 'A', nome: 'Atende AI · Cadastro', status: 'bot · configurando ' + S().negocio().nome, label: 'Mensagem para o assistente de cadastro', placeholder: ecom ? 'Ex.: Fone bluetooth R$ 89 estoque 12 entrega 3 dias' : 'Ex.: Alinhamento R$ 150 1h' })}
        <div class="lateral">
          <section class="card ficha" aria-labelledby="h-neg">
            <h2 id="h-neg">Seu negócio</h2>
            <label class="campo">Nome<input id="ob-nome" class="inp" value="${U.esc(S().negocio().nome)}"></label>
            <h3 style="margin-top:14px">Horário de funcionamento</h3>
            <div class="tabela-wrap"><table class="horario-tab"><thead><tr><th>Dia</th><th>Aberto</th><th>Abre</th><th>Fecha</th></tr></thead><tbody id="ob-horario"></tbody></table></div>
            ${ecom ? '<p class="pequeno muted" style="margin:8px 0 0">Na loja virtual, o horário define os dias úteis de envio e de resposta.</p>' : ''}
          </section>
          ${ecom ? '<div id="ob-pol"></div>' : ''}
        </div>
      </div>
      <section class="card" style="margin-top:20px" aria-labelledby="h-cat">
        <div class="cab" style="margin-bottom:12px"><div><h2 id="h-cat">Catálogo de ${seg === 'oficina' ? 'serviços' : ecom ? 'produtos da loja virtual' : 'produtos e serviços'}</h2><p class="pequeno">${ecom ? 'Preço em reais, estoque em unidades e envio em dias úteis após o pagamento. Produto com estoque 0 aparece como esgotado. Itens “exemplo” são fictícios.' : 'Valores em reais. "' + U.esc(def.rotulos.pecas) + '" e "' + U.esc(def.rotulos.mao) + '" aparecem separados no orçamento. Duração em minutos.'}</p></div>
        <button type="button" class="btn btn--p" id="ob-add">+ Adicionar linha</button></div>
        <div class="tabela-wrap"><table><thead><tr>${ecom ? '<th>Produto</th><th>Categoria</th><th class="num">Preço (R$)</th><th class="num">Estoque</th><th class="num">Envio (dias úteis)</th>' : '<th>Serviço</th><th>Categoria</th><th class="num">' + U.esc(def.rotulos.pecas) + ' mín</th><th class="num">' + U.esc(def.rotulos.pecas) + ' máx</th><th class="num">' + U.esc(def.rotulos.mao) + ' mín</th><th class="num">' + U.esc(def.rotulos.mao) + ' máx</th><th class="num">Duração</th>'}<th><span class="sr">Ações</span></th></tr></thead><tbody id="ob-cat"></tbody></table></div>
      </section>`;
    ligarTermo(main);
    const wa = main.querySelector('#ob-chat'); const log = wa.querySelector('.cv__log'); const ops = wa.querySelector('.cv__opcoes');
    const form = wa.querySelector('form'); const inp = form.querySelector('input');
    const lado = ['dono'];
    AT.Chat.render(log, ob.chat, lado);
    const usados = new Set();
    const mostrarOpcoes = () => AT.Chat.opcoes(ops, def.onboardingExemplos.filter((e) => !usados.has(e)), (o) => { usados.add(o); enviar(o); });
    mostrarOpcoes();

    function enviar(txt) {
      txt = String(txt || '').trim(); if (!txt) return;
      ob.chat.push({ de: 'dono', texto: txt, ts: Date.now() });
      AT.Chat.render(log, ob.chat, lado); AT.Chat.digitando(log, true);
      const res = ecom ? AT.E.parseEcom(txt) : AT.M.parseDono(txt, seg);
      setTimeout(() => {
        let r;
        if (ecom) {
          const antes = new Set(S().catalogo().map((c) => c.id));
          const linhas = AT.E.aplicarCadastro(res); S().salvar();
          r = { linhas, novos: S().catalogo().filter((c) => !antes.has(c.id)).map((c) => c.id) };
          if (Object.keys(res.mudancas).length) { main.querySelector('#ob-pol').innerHTML = cartaoPoliticas(); ligarPoliticas(main); }
        } else r = aplicar(res);
        let resp;
        if (!r.linhas.length) resp = ecom ? 'Não entendi como produto ou política. Tente assim: "' + def.onboardingExemplos[1] + '" ou "Frete grátis acima de R$ 199" ou "Chave pix: sua-chave".' : 'Não encontrei preço, duração nem horário nessa mensagem. Tente assim: "' + def.onboardingExemplos[1] + '" ou "Seg a sex 8h às 18h".';
        else resp = 'Entendi! ' + r.linhas.join('\n') + '\n' + (r.novos.length ? (ecom ? 'Já aparece no catálogo abaixo e o atendimento passa a oferecer esse produto.' : 'Já aparece no catálogo abaixo e o atendimento passa a usar esse item nos orçamentos.') : 'Pode corrigir qualquer valor direto na tabela.');
        ob.chat.push({ de: 'bot', texto: resp, ts: Date.now() });
        S().salvar();
        AT.Chat.digitando(log, false); AT.Chat.render(log, ob.chat, lado);
        desenharTabelas(r.novos); mostrarOpcoes();
        main.querySelector('#ob-nome').value = S().negocio().nome;
      }, AT.Chat.atraso());
    }
    form.addEventListener('submit', (e) => { e.preventDefault(); const v = inp.value; inp.value = ''; enviar(v); });
    main.querySelector('#ob-nome').addEventListener('change', (e) => { S().negocio().nome = e.target.value.trim() || S().negocio().nome; S().salvar(); U.toast('Nome atualizado'); });
    main.querySelector('#ob-add').addEventListener('click', () => {
      const id = 'novo-' + Math.random().toString(36).slice(2, 7);
      S().catalogo().push(ecom ? { id, nome: 'Novo produto', categoria: 'Geral', preco: 0, estoque: 0, envioDias: AT.E.pol().envioDiasUteis || 1, pecasMin: 0, pecasMax: 0, maoMin: 0, maoMax: 0, duracao: 0, palavras: [] }
        : { id, nome: 'Novo serviço', categoria: 'Geral', pecasMin: 0, pecasMax: 0, maoMin: 0, maoMax: 0, duracao: 60, palavras: [] });
      S().salvar(); desenharTabelas([id]);
      const el = main.querySelector('#ob-cat tr[data-id="' + id + '"] input'); if (el) { el.focus(); el.select(); }
    });

    function desenharTabelas(novos) {
      novos = novos || [];
      const cat = S().catalogo();
      const tb = main.querySelector('#ob-cat');
      tb.innerHTML = cat.map((c) => `<tr data-id="${U.esc(c.id)}"${novos.includes(c.id) ? ' class="tk--novo"' : ''}>
        <td><input class="inp" data-k="nome" aria-label="Nome do ${ecom ? 'produto' : 'serviço'}" value="${U.esc(c.nome)}" style="min-width:220px">${c.exemplo ? ' <span class="chip chip--exemplo">exemplo</span>' : ''}</td>
        <td><input class="inp" data-k="categoria" aria-label="Categoria de ${U.esc(c.nome)}" value="${U.esc(c.categoria || '')}" style="min-width:120px"></td>
        ${(ecom ? [['preco', 'Preço', '0.01'], ['estoque', 'Estoque', '1'], ['envioDias', 'Envio em dias úteis', '1']] : [['pecasMin', 'Mínimo de ' + def.rotulos.pecas, '1'], ['pecasMax', 'Máximo de ' + def.rotulos.pecas, '1'], ['maoMin', 'Mínimo de ' + def.rotulos.mao, '1'], ['maoMax', 'Máximo de ' + def.rotulos.mao, '1'], ['duracao', 'Duração em minutos', '1']])
          .map(([k, rot, st]) => `<td><input class="inp num" type="number" min="0" step="${st}" data-k="${k}" aria-label="${U.esc(rot)} de ${U.esc(c.nome)}" value="${+c[k] || 0}" style="width:96px"></td>`).join('')}
        <td><button type="button" class="btn btn--p btn--perigo" data-rm aria-label="Remover ${U.esc(c.nome)}">✕</button></td></tr>`).join('');
      tb.querySelectorAll('input').forEach((i) => i.addEventListener('change', () => {
        const c = cat.find((x) => x.id === i.closest('tr').dataset.id); const k = i.dataset.k;
        c[k] = i.type === 'number' ? Math.max(0, +i.value || 0) : i.value.trim();
        if (k === 'pecasMin' && c.pecasMax < c.pecasMin) c.pecasMax = c.pecasMin;
        if (k === 'maoMin' && c.maoMax < c.maoMin) c.maoMax = c.maoMin;
        if (k === 'preco') { c.preco = AT.E.r2(c.preco); c.pecasMin = c.pecasMax = c.preco; }
        if (k === 'estoque' || k === 'envioDias') c[k] = Math.round(c[k]);
        if (k === 'nome') c.palavras = Array.from(new Set((c.palavras || []).concat(U.norm(c.nome).split(' ').filter((w) => w.length >= 4))));
        S().salvar();
      }));
      tb.querySelectorAll('[data-rm]').forEach((b) => b.addEventListener('click', () => {
        const id = b.closest('tr').dataset.id; const i = cat.findIndex((x) => x.id === id);
        if (i >= 0) { const nome = cat[i].nome; cat.splice(i, 1); S().salvar(); desenharTabelas(); U.toast('Removido: ' + nome); }
      }));
      const neg = S().negocio(); const hb = main.querySelector('#ob-horario');
      hb.innerHTML = [1, 2, 3, 4, 5, 6, 0].map((d) => { const h = neg.horario[d]; return `<tr data-d="${d}"><th scope="row" style="text-transform:none;font-size:.9rem">${U.diasLongo[d]}</th>
        <td><input type="checkbox" class="toggle" aria-label="Aberto na ${U.diasLongo[d]}" ${h ? 'checked' : ''}></td>
        <td><input type="time" aria-label="Abre ${U.diasLongo[d]}" value="${h ? h[0] : '08:00'}" ${h ? '' : 'disabled'}></td>
        <td><input type="time" aria-label="Fecha ${U.diasLongo[d]}" value="${h ? h[1] : '18:00'}" ${h ? '' : 'disabled'}></td></tr>`; }).join('');
      hb.querySelectorAll('tr').forEach((tr) => {
        const d = +tr.dataset.d; const [ck, ab, fe] = tr.querySelectorAll('input');
        const salvar = () => { ab.disabled = fe.disabled = !ck.checked; neg.horario[d] = ck.checked ? [ab.value || '08:00', fe.value || '18:00'] : null; S().salvar(); };
        [ck, ab, fe].forEach((i) => i.addEventListener('change', salvar));
      });
    }
    if (ecom) { main.querySelector('#ob-pol').innerHTML = cartaoPoliticas(); ligarPoliticas(main); }
    desenharTabelas();
  }
  AT.V = AT.V || {};
  AT.V.onboarding = { titulo: 'Cadastro', render };
})(window.AT);
