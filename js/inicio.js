/* Atende AI — landing */
(function (AT) {
  'use strict';
  const U = AT.U;
  const COPY = {
    oficina: {
      titulo: 'Sua oficina atende, orça e agenda pelo Telegram, mesmo com o elevador ocupado.',
      lead: 'O cliente chama o bot da oficina no Telegram e conta o problema ("barulho ao frear", "carro não liga"). O assistente entende o sintoma, pergunta o modelo e a placa, monta o orçamento com peças e mão de obra do seu catálogo, combina o prazo e abre a ordem de serviço. Você acompanha tudo num painel.',
      dor: 'Mecânico com a mão suja não responde mensagem. Cliente sem resposta em 10 minutos procura outra oficina.'
    },
    loja: {
      titulo: 'Sua loja responde orçamentos pelo Telegram em segundos, com entrega e prazo combinados.',
      lead: 'O cliente chama o bot da loja no Telegram e diz o que precisa ("quero pintar o quarto", "torneira vazando"). O assistente sugere os produtos certos do seu catálogo, calcula entrega ou instalação, informa o prazo e separa o pedido. Você acompanha tudo num painel.',
      dor: 'Balcão cheio e celular tocando: quem demora para responder perde a venda para o concorrente da esquina.'
    },
    ecommerce: {
      titulo: 'Sua loja virtual vende, calcula frete e responde “cadê meu pedido?” pelo Telegram, sozinha.',
      lead: 'O cliente pergunta do jeito dele ("vcs tem fone blutooth?"), vê preço e estoque, calcula o frete pelo CEP, monta o carrinho e fecha o pedido com resumo, frete e desconto no Pix. Ele recebe a sua chave Pix ou link de pagamento, toca em “Já paguei” e você confirma. Depois o bot avisa separação, envio com rastreio e pede avaliação.',
      dor: 'Quem vende online passa o dia respondendo frete, prazo e rastreio. Carrinho sem resposta vira venda perdida.'
    }
  };
  function previa(seg) {
    const ex = seg === 'ecommerce'
      ? [['out', 'vcs tem fone blutooth?'], ['in', '<b>Fone bluetooth TWS</b> — R$ 89,90 · ✅ 25 em estoque · envio em 1 dia útil'], ['out', 'frete pro cep 30140-071?'], ['in', '📍 Belo Horizonte/MG · frete R$ 21,90 · ~4 dias. <b>Total no Pix (5% off): R$ 107,31</b>. Fechar pedido?']]
      : seg === 'oficina'
      ? [['out', 'Oi, meu Onix 2019 tá fazendo barulho ao frear'], ['in', 'Barulho ao frear costuma indicar pastilhas no fim. Qual a placa?'], ['out', 'FTR4B21'], ['in', '<b>Orçamento:</b> pastilhas dianteiras R$ 250 a R$ 460 · prazo hoje às 17:30. Aprovar?']]
      : [['out', 'Quero pintar o quarto da minha filha'], ['in', 'Para até 12 m², 18 L de tinta rendem 2 demãos. Entrega em qual bairro?'], ['out', 'Cambuí'], ['in', '<b>Orçamento:</b> kit pintura + entrega R$ 405 a R$ 605 · entrega hoje. Aprovar?']];
    const neg = AT.S.negocio(seg); const tg = AT.Canais.get('telegram');
    const msgs = ex.map(([l, t]) => ({ de: l === 'out' ? 'cliente' : 'bot', html: '<p>' + t + '</p>', ts: Date.now() }));
    msgs[msgs.length - 1].teclado = seg === 'ecommerce' ? [{ rotulo: '✅ Fechar pedido', valor: 'x' }, { rotulo: '🛒 Meu carrinho', valor: 'x' }] : [{ rotulo: '✅ Aprovar orçamento', valor: 'x' }, { rotulo: '🙋 Falar com atendente', valor: 'x' }];
    const corpo = msgs.map((m) => AT.Chat.bolha(m, ['cliente'], false, tg)).join('');
    return '<div class="cv cv--telegram" aria-label="Exemplo de conversa no Telegram (ilustrativo)">' +
      '<div class="cv__topo"><div class="cv__avatar" aria-hidden="true">' + U.esc(neg.nome.charAt(0)) + '</div><div><div class="cv__nome">' + U.esc(neg.nome) + '</div><div class="cv__status">bot · exemplo ilustrativo</div></div><span class="cv__demo">Demonstração —<br>IA simulada</span></div>' +
      '<div class="cv__log" style="min-height:0">' + corpo + '</div></div>';
  }
  function render(main) {
    const seg = AT.S.seg(); const c = COPY[seg];
    main.innerHTML = `
    <section class="hero">
      <div>
        <div class="olho">CRM + atendimento automático para ${({ oficina: 'oficinas mecânicas', loja: 'lojas e comércio local', ecommerce: 'lojas virtuais' })[seg]}</div>
        <h1>${U.esc(c.titulo)}</h1>
        <p class="lead">${U.esc(c.lead)}</p>
        <div class="seg" role="group" aria-label="Ver exemplo para" style="margin-left:0">
          <button type="button" class="seg__btn" data-seg="oficina" aria-pressed="${seg === 'oficina'}">🔧 Oficina</button>
          <button type="button" class="seg__btn" data-seg="loja" aria-pressed="${seg === 'loja'}">🏬 Loja</button>
          <button type="button" class="seg__btn" data-seg="ecommerce" aria-pressed="${seg === 'ecommerce'}">🛒 Loja virtual</button>
        </div>
        <p class="pequeno muted" style="margin-top:14px">Canal principal: <strong>Telegram</strong> (gratuito, sem aprovação prévia). <span class="chip chip--atencao">WhatsApp em breve</span> com o mesmo motor de atendimento.</p>
        <div class="linha">
          <a class="btn btn--tg" href="#/atendimento">✈️ Testar como cliente no Telegram</a>
          <a class="btn btn--pri" href="#/onboarding">Cadastrar meu negócio pelo chat</a>
          <a class="btn" href="#/dashboard">Ver o painel</a>
        </div>
      </div>
      ${previa(seg)}
    </section>
    <section aria-labelledby="h-valor">
      <h2 id="h-valor" class="sr">O que o Atende AI faz</h2>
      <div class="destaques">
        <article class="destaque"><div class="ico" aria-hidden="true">💬</div><h3>Atende 24h no Telegram</h3><p>${seg === 'ecommerce' ? 'Entende perguntas com erro de digitação, mostra preço e estoque, calcula frete pelo CEP e responde rastreio e troca.' : 'Entende o problema em linguagem do dia a dia e faz as perguntas certas: modelo, placa, bairro, urgência.'}</p></article>
        <article class="destaque"><div class="ico" aria-hidden="true">⚡</div><h3>${seg === 'ecommerce' ? 'Carrinho e pedido no chat' : 'Orçamento em segundos'}</h3><p>${seg === 'ecommerce' ? 'Resumo itemizado com frete, desconto no Pix e total. O cliente recebe a sua chave Pix ou link e toca em “Já paguei”; você confirma.' : 'Itens, ' + (seg === 'oficina' ? 'peças e mão de obra' : 'produtos e entrega/instalação') + ' saem do seu catálogo, com faixa de preço e validade.'}</p></article>
        <article class="destaque"><div class="ico" aria-hidden="true">⏱️</div><h3>SLA que ninguém esquece</h3><p>${seg === 'ecommerce' ? 'Prazo de envio em dias úteis a partir do pagamento, alerta antes de estourar e lembrete de carrinho abandonado.' : 'Prazo por prioridade, contagem regressiva e alerta quando um pedido está para estourar.'}</p></article>
        <article class="destaque"><div class="ico" aria-hidden="true">📊</div><h3>Painel de controle</h3><p>${seg === 'ecommerce' ? 'Pedidos, faturamento, ticket médio, conversão carrinho → pago, carrinhos abandonados, trocas e CSV.' : 'Funil, taxa de aprovação, tempo de resposta, faturamento previsto e realizado, exportação em CSV.'}</p></article>
      </div>
    </section>
    <section aria-labelledby="h-como">
      <h2 id="h-como">Como funciona</h2>
      <p class="muted">${U.esc(c.dor)}</p>
      <div class="passos">
        <div class="passo"><h3>Você conversa e cadastra</h3><p>${seg === 'ecommerce' ? 'Escreva "Fone bluetooth R$ 89 estoque 12 entrega 3 dias" e "Frete grátis acima de R$ 199": o assistente monta catálogo e políticas.' : 'Escreva "troca de óleo R$ 180 1h" e o assistente monta o catálogo, o horário e as regras.'}</p></div>
        <div class="passo"><h3>O cliente resolve no chat</h3><p>${seg === 'ecommerce' ? 'Ele acha o produto, vê o frete, fecha o pedido e recebe as instruções de pagamento sem esperar ninguém.' : 'Ele descreve o problema, recebe o orçamento e aprova sem esperar ninguém.'}</p></div>
        <div class="passo"><h3>As mensagens seguem sozinhas</h3><p>${seg === 'ecommerce' ? 'Pagamento confirmado, separando, enviado com rastreio, pós-venda com avaliação e lembrete de carrinho, no momento certo.' : 'Confirmação, lembrete, "' + (seg === 'oficina' ? 'carro pronto' : 'pedido pronto') + '" e pesquisa de satisfação, no momento certo.'}</p></div>
      </div>
    </section>
    <div class="aviso" role="note"><strong>Esta é uma demonstração.</strong> As respostas do assistente são simuladas por regras e palavras-chave; não há integração real com o Telegram, o WhatsApp ou modelos de IA. Os pedidos já cadastrados são dados de exemplo fictícios, salvos só neste navegador. A proposta da versão real (Telegram Bot API + Grok, depois WhatsApp Cloud API) está em <a href="https://github.com/guilhermeromio-netto-prog/atende-ai/blob/main/docs/arquitetura.md">docs/arquitetura.md</a>.</div>`;
  }
  AT.V = AT.V || {};
  AT.V.inicio = { titulo: 'Início', render };
})(window.AT);
