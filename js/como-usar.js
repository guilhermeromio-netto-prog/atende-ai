/* Atende AI — guia "Como usar" (bot de teste no Telegram + app web) */
(function (AT) {
  'use strict';
  const BOT = 'https://t.me/Applojas10_bot';
  const U = AT.U;
  // Texto para o Guilherme encaminhar ao lojista (mesmo texto de COMO-USAR.md).
  const MSG_PRO = "Oi! Montei uma versão Pro do Atende AI para a sua loja virtual: um atendente automático no Telegram que mostra seus produtos, calcula o frete pelo CEP, fecha o pedido e passa a sua chave Pix para o cliente. Leva menos de 3 minutos para deixar no ar:\n\n1. Abra este link no celular: https://t.me/Applojas10_bot?start=pro-lojavirtual\n2. Escreva o nome da loja\n3. Leia o termo do piloto e toque em ✅ Aceito\n4. Escolha o frete e a forma de pagamento nos botões e mande sua chave Pix (ou toque em Pular)\n5. Cole sua lista de produtos, uma linha por produto, assim:\nFone bluetooth; 89,90; 12; 3\n(nome; preço; estoque; dias para despachar). Também dá para colar direto da planilha.\n6. Toque em ✅ Concluir. Ele te dá o link da loja para colocar na bio do Instagram e no WhatsApp (os textos prontos estão em /modelos)\n\nNo dia a dia:\n• Cada pedido chega no seu Telegram com botões: confirmar pagamento → separar → enviar com rastreio\n• O bot nunca cobra nem confirma pagamento sozinho: você confere no banco e toca em Confirmar\n• Ele lembra quem esqueceu o carrinho, pede avaliação depois da entrega e avisa se um envio estiver atrasando\n• Todo dia às 19h chega um resumo (pedidos, pagos, faturamento e o que falta enviar)\n• Ele também anota agenda, lembretes e contas: escreva algo como \"lembrar de postar no Instagram amanhã 10h\"\n\nPara testar como cliente: /cliente (e /dono para voltar). Recursos do plano: /plano.\nÉ um piloto e roda num servidor de teste: se o bot parar de responder, me avisa que eu religo. Qualquer dúvida, me chama!";
  function render(main) {
    main.innerHTML = `
    <div class="guia">
      <div class="cab"><div><div class="olho">Guia rápido</div><h1>Como usar o Atende AI</h1>
        <p>Existe um <strong>bot real de teste</strong> no Telegram, <a href="${BOT}">@Applojas10_bot</a>, com o mesmo motor de regras desta demonstração. Ele funciona sem IA: o Grok entra quando houver créditos.</p></div>
        <div class="linha"><a class="btn btn--tg" href="${BOT}">✈️ Abrir o bot no Telegram</a> <a class="btn" href="#/manual">📘 Manual do lojista</a></div></div>

      <section class="card guia-pro" aria-labelledby="g-pro" id="guia-pro"><h2 id="g-pro">⭐ Guia rápido Pro · Loja virtual em menos de 3 minutos</h2>
        <p>A versão Pro é <strong>plug and play</strong>: um link só abre um assistente de 4 passos com botões. No fim, a loja já está no ar com modelos de mensagem, políticas e automações ligadas. Funciona sem IA paga.</p>
        <p><a class="btn btn--tg" href="${BOT}?start=pro-lojavirtual">⭐ Abrir o assistente Pro</a> <code>${BOT.replace('https://', '')}?start=pro-lojavirtual</code></p>
        <ol>
          <li><strong>Nome da loja:</strong> escreva, por exemplo, <code>Loja do Mano</code>.</li>
          <li><strong>Termo do piloto:</strong> leia e toque em <strong>✅ Aceito</strong> (fica registrado com data e hora; “Não aceito” não cria nada).</li>
          <li><strong>Frete e pagamento:</strong> toque num modelo de frete (grátis acima de R$ 199 · fixo R$ 19,90 · por região) e num de pagamento (Pix 5% + 3x · Pix 10% + 6x · só Pix). Mande a chave Pix ou toque em <strong>Pular</strong>.</li>
          <li><strong>Produtos:</strong> cole a lista, uma linha por produto: <code>Fone bluetooth; 89,90; 12; 3</code> (nome; preço; estoque; dias para envio), CSV da planilha <code>Cabo USB-C,29.90,50,1</code> ou texto livre <code>Garrafa térmica R$ 59 estoque 20 entrega 2 dias</code>. Sem lista à mão? <strong>🧪 Usar 5 produtos de exemplo</strong>. Toque em <strong>✅ Concluir</strong>.</li>
        </ol>
        <p><strong>Já vem ligado:</strong> carrinho abandonado (lembrete ao cliente), pós-venda com avaliação de 1 a 5, alerta de SLA de envio, <strong>resumo diário às 19h</strong> no Telegram do dono, Secretário do dono e modelos de mensagem (<code>/modelos</code>: bio do Instagram, status, resposta automática, Pix pendente, atraso, troca aprovada). Lista completa: <code>/plano</code> · resumo na hora: <code>/resumo</code>.</p>
        <p class="pequeno muted">O bot nunca cobra nem confirma pagamento sozinho: ele mostra a chave Pix do lojista e o lojista confirma depois de conferir no banco. Plano Pro durante o piloto: sem cobrança. O administrador pode ligar o Pro numa loja existente com <code>/pro slug</code>.</p>
        <p>Para o lojista ler com calma (e imprimir ou salvar em PDF): <a href="#/manual">📘 Manual do lojista</a>.</p>
        <h3>Mensagem pronta para encaminhar</h3>
        <pre class="msg-pronta" id="msg-pro">${U.esc(MSG_PRO)}</pre>
        <button type="button" class="btn" id="copiar-msg-pro">📋 Copiar mensagem</button> <span class="pequeno muted" id="copiar-ok" role="status"></span>
      </section>

      <section class="card" aria-labelledby="g-dono"><h2 id="g-dono">🧑‍🔧 Para o dono da oficina ou loja</h2>
        <ol>
          <li>Abra <a href="${BOT}?start=dono">${BOT.replace('https://', '')}?start=dono</a> (ou envie <code>/dono</code> no bot).</li>
          <li>Toque em <strong>Assumir</strong> um negócio de exemplo (já vem com catálogo) ou em <strong>Criar meu negócio do zero</strong>. Leia o <strong>Termo de uso do piloto</strong> e toque em <strong>✅ Aceito</strong> (obrigatório, fica registrado).</li>
          <li>Cadastre conversando, uma coisa por mensagem: <code>Troca de óleo R$ 180 1h</code>, <code>Pastilha de freio peças R$ 160 a 320 mão de obra R$ 120 1h30</code>, <code>Seg a sex 8h às 18h; sábado 8h às 12h</code>.</li>
          <li>Envie <code>/link</code> e divulgue o link para seus clientes (Instagram, Google, QR code no balcão).</li>
          <li>Quando um cliente pedir orçamento, você recebe a notificação com botões: <strong>▶ Avançar</strong> (Aprovado → Em serviço → Pronto → Entregue) e <strong>💬 Responder cliente</strong>. Cada avanço manda a mensagem automática certa para o cliente.</li>
          <li>Acompanhe com <code>/painel</code> (indicadores) e <code>/pedidos</code>. O bot avisa quando um pedido entra em atenção ou estoura o SLA.</li>
          <li>Para testar sozinho, envie <code>/cliente</code>, faça o papel de cliente e volte com <code>/dono</code>.</li>
        </ol>
        <p class="pequeno muted">Outros comandos: <code>/catalogo</code>, <code>/remover N</code>, <code>/horario</code>, <code>/codigo</code> (para outra pessoa da equipe receber os pedidos com <code>/dono CÓDIGO</code>), <code>/conectar</code>, <code>/ajuda</code>.</p>
      </section>

      <section class="card" aria-labelledby="g-cli"><h2 id="g-cli">🙋 Para o cliente final</h2>
        <ol>
          <li>Abra o link que a oficina ou loja divulgou (ex.: <a href="${BOT}?start=oficina-pista-livre">${BOT.replace('https://', '')}?start=oficina-pista-livre</a> ou a loja virtual <a href="${BOT}?start=loja-exemplo-online">…?start=loja-exemplo-online</a>).</li>
          <li>Conte o problema do seu jeito: “barulho ao frear”, “carro não liga”, “quero pintar o quarto”.</li>
          <li>Responda as perguntas: nome, modelo e placa (oficina) ou bairro de entrega (loja), e a urgência.</li>
          <li>Receba o orçamento com itens, total, duração e prazo. Toque em <strong>✅ Aprovar</strong> ou <strong>🙋 Falar com atendente</strong>.</li>
          <li>Escolha o horário. Depois chegam sozinhas: confirmação, aviso de início, “pronto” e a pesquisa de satisfação (1 a 5 estrelas).</li>
        </ol>
        <p class="pequeno muted">Comandos: <code>/nova</code> recomeça, <code>/trocar</code> escolhe outro negócio. Escrever “atendente” chama uma pessoa a qualquer momento.</p>
      </section>

      <section class="card" aria-labelledby="g-ecom" id="loja-virtual"><h2 id="g-ecom">🛒 Loja virtual: passo a passo para o lojista</h2>
        <p>Para quem vende online: o bot mostra produtos, preço e estoque, calcula frete pelo CEP, fecha o pedido com resumo e manda as <strong>suas</strong> instruções de pagamento. O bot nunca cobra nem confirma pagamento sozinho: quem confere e confirma é você.</p>
        <h3>1. Criar a sua loja</h3>
        <ol>
          <li>Abra <a href="${BOT}?start=dono">${BOT.replace('https://', '')}?start=dono</a> e toque em <strong>➕ Criar meu negócio do zero</strong>.</li>
          <li>Escreva o nome da loja (ex.: <code>Loja do Mano</code>).</li>
          <li>Escolha <strong>🛒 Loja virtual (catálogo de exemplo)</strong> para começar com 10 produtos fictícios ou <strong>🛒 Loja virtual (catálogo vazio)</strong> para cadastrar os seus.</li>
          <li>Leia o <strong>Termo de uso do piloto</strong> e toque em <strong>✅ Aceito</strong>. Só depois disso a loja é criada.</li>
        </ol>
        <h3>2. Cadastrar produtos e políticas (conversando)</h3>
        <ul>
          <li>Produto: <code>Fone bluetooth R$ 89 estoque 12 entrega 3 dias</code> (repetir o nome atualiza preço/estoque).</li>
          <li>Frete grátis: <code>Frete grátis acima de R$ 199</code> · fixo: <code>Frete fixo R$ 19,90</code></li>
          <li>Frete por região do CEP: <code>Frete SP R$ 15 2 dias, Sudeste R$ 22 4 dias, outros R$ 35 8 dias</code></li>
          <li>Prazo de envio: <code>Envio em 1 dia útil</code> · Troca: <code>Troca em até 7 dias por arrependimento</code></li>
          <li>Pagamento: <code>Pix com 5% de desconto, cartão em até 6x</code> · <code>Chave pix: sua-chave</code> · <code>Link do cartão: https://…</code></li>
          <li>Conferir tudo: <code>/catalogo</code> e <code>/politicas</code>. Remover produto: <code>/remover N</code>.</li>
        </ul>
        <h3>3. Divulgar e testar</h3>
        <ol>
          <li>Envie <code>/link</code> e coloque o link no Instagram, na bio ou no site.</li>
          <li>Teste você mesmo com <code>/cliente</code>: pergunte “tem fone bluetooth?”, adicione ao carrinho, informe CEP, endereço e forma de pagamento e confirme. Volte com <code>/dono</code>.</li>
          <li>Cada pedido chega para você com botões: <strong>✅ Confirmar pagamento</strong> (depois de conferir no banco; o estoque baixa sozinho), <strong>▶ Separando</strong>, <strong>📦 Informar rastreio e enviar</strong> (você digita o código) e <strong>Entregue</strong> (sai o pós-venda com avaliação).</li>
          <li>O cliente pode perguntar “cadê meu pedido EC-…?” e recebe status e rastreio; “quero trocar” abre uma solicitação com motivo e a sua política.</li>
          <li>Carrinho esquecido recebe um lembrete automático (modo teste: 10 minutos). <code>/painel</code> mostra pedidos, faturamento, ticket médio, conversão carrinho → pago, abandonos e trocas.</li>
        </ol>
        <p>Quer só ver funcionando? Abra a loja de exemplo: <a href="${BOT}?start=loja-exemplo-online">${BOT.replace('https://', '')}?start=loja-exemplo-online</a> (produtos fictícios; não faça pagamento).</p>
      </section>

      <section class="card" aria-labelledby="g-sec" id="secretario"><h2 id="g-sec">🗂️ Secretário do dono</h2>
        <p>No modo dono, mande vários pedidos numa mensagem só: <code>Agendar reunião com João, pagar conta de luz, lembrar de comprar leite</code>. O bot separa em tarefas, pergunta <strong>só o que falta numa única mensagem</strong> (“dia e hora da reunião; vencimento da conta”) e confirma cada uma com prova (<code>#AG-0001</code>).</p>
        <ul>
          <li>Agenda nunca é criada sem dia e hora. Lembrete sem hora vai para hoje às 18h (America/Sao_Paulo) e o bot avisa que usou o padrão.</li>
          <li>Conta a pagar fica <strong>aguardando seu ok</strong>: só vira paga quando você toca em “Paguei”. O bot não movimenta dinheiro.</li>
          <li>Lembretes disparam no Telegram na hora, com botões <strong>Feito</strong> e <strong>+1h</strong>. Também entende “ligar pro cliente Ana amanhã 9h” e “repor fone bluetooth 20 unidades”.</li>
          <li>Comandos: <code>/agenda</code>, <code>/lembretes</code>, <code>/contas</code>. Áudio: o bot pede o texto (não transcreve ainda). Simulação no app: <a href="#/secretario">Secretário</a>.</li>
        </ul>
      </section>

      <section class="card" aria-labelledby="g-dash"><h2 id="g-dash">🖥️ Ligar este painel aos dados do bot</h2>
        <ol>
          <li>No Telegram, como dono, envie <code>/conectar</code>.</li>
          <li>Abra o link recebido: ele traz o endereço da API e a chave de leitura do seu negócio.</li>
          <li>Pedidos e Dashboard mostram a faixa verde <strong>Modo conectado</strong> e se atualizam a cada 30 s. Para desligar, vá em Configurações → Modo conectado.</li>
        </ol>
        <p class="pequeno muted">A chave só lê os pedidos daquele negócio e não deve ser compartilhada. No painel web os pedidos reais são somente leitura: o avanço é feito pelos botões no Telegram.</p>
      </section>

      <section class="card" aria-labelledby="g-priv" id="privacidade-piloto"><h2 id="g-priv">🔒 Termo do piloto e privacidade</h2>
        <ul>
          <li>Ao criar ou assumir uma loja, o bot mostra o <strong>Termo de uso do piloto</strong> e só continua depois do <strong>✅ Aceito</strong> (fica registrado com data e hora). “Não aceito” não cria nada.</li>
          <li>Na 1ª conversa com cada negócio, o cliente recebe uma linha avisando onde ficam os dados e como apagar.</li>
          <li><code>/excluir_dados</code>: o cliente apaga na hora nome, contato, mensagens e endereço (os pedidos ficam anônimos); o dono pede a exclusão da loja e o administrador confirma.</li>
        </ul>
        <p class="pequeno muted">Política completa: <a href="#/privacidade">Privacidade</a>.</p>
      </section>

      <section class="card" aria-labelledby="g-adm" id="admin"><h2 id="g-adm">🛡️ Para o administrador da plataforma</h2>
        <ol>
          <li>No bot, envie <code>/admin SEU_CÓDIGO</code> (o código fica só no servidor; a mensagem é apagada do chat depois do uso). Cinco tentativas erradas bloqueiam por 1 hora.</li>
          <li><code>/plataforma</code>: lojas ativas, conversas, pedidos, conversão, faturamento intermediado, tempo de resposta e NPS.</li>
          <li><code>/lojas</code> lista todas as lojas (segmento, donos, pedidos, faturamento, última atividade). <code>/loja slug</code> mostra indicadores, saúde do piloto e pedidos recentes.</li>
          <li><code>/piloto slug</code> marca uma loja como piloto (<code>/piloto slug off</code> desmarca). Os donos recebem o convite para preencher o “antes” com <code>/antes resposta 2h vendas R$ 8.000 pedidos 40</code>.</li>
          <li><code>/admin_conectar</code> manda o link do <a href="#/admin">Modo plataforma</a> com a chave de administrador (separada das chaves das lojas). Sem chave, a página mostra dados de demonstração.</li>
          <li><code>/excluir_loja slug</code> exclui uma loja e os pedidos dela (pede confirmação).</li>
        </ol>
      </section>

      <section class="card" aria-labelledby="g-lim"><h2 id="g-lim">⚠️ Limitações do modo de teste</h2>
        <ul>
          <li>O bot e a API rodam num computador de teste. <strong>Se ele desligar ou reiniciar, o bot para de responder</strong> até ser religado.</li>
          <li>O endereço da API (túnel <code>trycloudflare.com</code>) muda a cada reinício: peça <code>/conectar</code> de novo.</li>
          <li>Sem IA: o entendimento é por palavras-chave do catálogo. Relatos muito diferentes caem em “qual destas opções é mais parecida?”.</li>
          <li>Os valores são estimativas do catálogo; não há pagamento, nota fiscal nem integração com WhatsApp. Na loja virtual, o bot só repassa a chave Pix/link que o lojista cadastrou e avisa quando o cliente toca em “Já paguei”.</li>
          <li>Frete por CEP usa a região pelo 1º dígito (com consulta pública ViaCEP para cidade/UF, quando disponível); não é cotação dos Correios ou transportadora.</li>
          <li>Pós-venda sai 2 minutos após “Entregue” (para facilitar o teste); na versão final, 1 dia depois.</li>
        </ul>
      </section>

      <section class="card" aria-labelledby="g-f2"><h2 id="g-f2">🚀 Caminho para a fase 2</h2>
        <ol>
          <li><strong>Sempre ligado:</strong> mover o bot para Cloudflare Workers (ou um servidor pequeno) com webhook do Telegram e banco Postgres. O token do bot fica só no servidor.</li>
          <li><strong>Grok com créditos:</strong> entendimento de texto livre com tool calling. Preço e prazo continuam vindo do catálogo; as regras ficam como plano B.</li>
          <li><strong>WhatsApp:</strong> segundo adaptador do mesmo motor, via WhatsApp Cloud API (Meta).</li>
        </ol>
        <p class="pequeno"><a href="https://github.com/guilhermeromio-netto-prog/atende-ai/blob/main/docs/arquitetura.md">Ver a arquitetura completa</a> · <a href="https://github.com/guilhermeromio-netto-prog/atende-ai/blob/main/COMO-USAR.md">COMO-USAR.md</a></p>
      </section>
    </div>`;
    const bt = main.querySelector('#copiar-msg-pro');
    bt.addEventListener('click', () => {
      const ok = (t) => { main.querySelector('#copiar-ok').textContent = t; };
      if (navigator.clipboard && navigator.clipboard.writeText) navigator.clipboard.writeText(MSG_PRO).then(() => ok('Copiado!'), () => ok('Selecione o texto acima e copie.'));
      else ok('Selecione o texto acima e copie.');
    });
    if (AT.irPara) { const alvo = document.getElementById(AT.irPara); AT.irPara = null; if (alvo) setTimeout(() => alvo.scrollIntoView({ block: 'start' }), 30); }
  }
  AT.V = AT.V || {};
  AT.V.comoUsar = { titulo: 'Como usar', render };
})(window.AT);
