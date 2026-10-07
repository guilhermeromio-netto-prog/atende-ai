/* Atende AI — guia "Como usar" (bot de teste no Telegram + app web) */
(function (AT) {
  'use strict';
  const BOT = 'https://t.me/Applojas10_bot';
  function render(main) {
    main.innerHTML = `
    <div class="guia">
      <div class="cab"><div><div class="olho">Guia rápido</div><h1>Como usar o Atende AI</h1>
        <p>Existe um <strong>bot real de teste</strong> no Telegram, <a href="${BOT}">@Applojas10_bot</a>, com o mesmo motor de regras desta demonstração. Ele funciona sem IA: o Grok entra quando houver créditos.</p></div>
        <a class="btn btn--tg" href="${BOT}">✈️ Abrir o bot no Telegram</a></div>

      <section class="card" aria-labelledby="g-dono"><h2 id="g-dono">🧑‍🔧 Para o dono da oficina ou loja</h2>
        <ol>
          <li>Abra <a href="${BOT}?start=dono">${BOT.replace('https://', '')}?start=dono</a> (ou envie <code>/dono</code> no bot).</li>
          <li>Toque em <strong>Assumir</strong> um negócio de exemplo (já vem com catálogo) ou em <strong>Criar meu negócio do zero</strong>.</li>
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
          <li>Abra o link que a oficina ou loja divulgou (ex.: <a href="${BOT}?start=oficina-pista-livre">${BOT.replace('https://', '')}?start=oficina-pista-livre</a>).</li>
          <li>Conte o problema do seu jeito: “barulho ao frear”, “carro não liga”, “quero pintar o quarto”.</li>
          <li>Responda as perguntas: nome, modelo e placa (oficina) ou bairro de entrega (loja), e a urgência.</li>
          <li>Receba o orçamento com itens, total, duração e prazo. Toque em <strong>✅ Aprovar</strong> ou <strong>🙋 Falar com atendente</strong>.</li>
          <li>Escolha o horário. Depois chegam sozinhas: confirmação, aviso de início, “pronto” e a pesquisa de satisfação (1 a 5 estrelas).</li>
        </ol>
        <p class="pequeno muted">Comandos: <code>/nova</code> recomeça, <code>/trocar</code> escolhe outro negócio. Escrever “atendente” chama uma pessoa a qualquer momento.</p>
      </section>

      <section class="card" aria-labelledby="g-dash"><h2 id="g-dash">🖥️ Ligar este painel aos dados do bot</h2>
        <ol>
          <li>No Telegram, como dono, envie <code>/conectar</code>.</li>
          <li>Abra o link recebido: ele traz o endereço da API e a chave de leitura do seu negócio.</li>
          <li>Pedidos e Dashboard mostram a faixa verde <strong>Modo conectado</strong> e se atualizam a cada 30 s. Para desligar, vá em Configurações → Modo conectado.</li>
        </ol>
        <p class="pequeno muted">A chave só lê os pedidos daquele negócio e não deve ser compartilhada. No painel web os pedidos reais são somente leitura: o avanço é feito pelos botões no Telegram.</p>
      </section>

      <section class="card" aria-labelledby="g-lim"><h2 id="g-lim">⚠️ Limitações do modo de teste</h2>
        <ul>
          <li>O bot e a API rodam num computador de teste. <strong>Se ele desligar ou reiniciar, o bot para de responder</strong> até ser religado.</li>
          <li>O endereço da API (túnel <code>trycloudflare.com</code>) muda a cada reinício: peça <code>/conectar</code> de novo.</li>
          <li>Sem IA: o entendimento é por palavras-chave do catálogo. Relatos muito diferentes caem em “qual destas opções é mais parecida?”.</li>
          <li>Os valores são estimativas do catálogo; não há pagamento, nota fiscal nem integração com WhatsApp.</li>
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
  }
  AT.V = AT.V || {};
  AT.V.comoUsar = { titulo: 'Como usar', render };
})(window.AT);
