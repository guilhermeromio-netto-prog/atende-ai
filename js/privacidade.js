/* Atende AI — privacidade e termo de uso do piloto (#/privacidade) */
(function (AT) {
  'use strict';
  const BOT = 'https://t.me/Applojas10_bot';
  const TERMO = [
    'Os dados do negócio e dos clientes (cadastro, conversas e pedidos) ficam na plataforma Atende AI, operada por Guilherme Romio Netto (byGui), num servidor de teste.',
    'Eles são usados só para operar o atendimento e calcular as métricas do piloto (tempo de resposta, pedidos, conversão, avaliação). Não são vendidos nem repassados a terceiros.',
    'Os clientes são avisados na 1ª mensagem e podem pedir a exclusão com /excluir_dados. O dono também pode pedir a exclusão da loja com /excluir_dados.',
    'O bot não processa pagamentos: ele só repassa as instruções que o dono cadastrar. Modo de teste, sem garantia de disponibilidade.'
  ];
  function render(main) {
    main.innerHTML = `
    <div class="guia">
      <div class="cab"><div><div class="olho">Versão 1 · 07/10/2026</div><h1>Privacidade e termo do piloto</h1>
        <p>Resumo em linguagem simples para a fase de piloto do Atende AI. Não substitui orientação jurídica.</p></div></div>

      <section class="card" aria-labelledby="p-quem"><h2 id="p-quem">Quem opera</h2>
        <p>A plataforma <strong>Atende AI</strong> é operada por <strong>Guilherme Romio Netto (byGui)</strong>, em modo de teste: o bot <a href="${BOT}">@Applojas10_bot</a> e este painel, rodando num servidor de teste.</p>
        <p>Na linguagem da LGPD: cada <strong>loja</strong> é a controladora dos dados dos próprios clientes; o Atende AI trata esses dados <strong>em nome da loja</strong> (operador). As métricas agregadas do piloto, sem identificar ninguém, servem para melhorar o serviço.</p>
      </section>

      <section class="card" aria-labelledby="p-termo" id="termo"><h2 id="p-termo">📄 Termo de uso do piloto</h2>
        <p>Quem cria ou assume uma loja no bot vê este termo e só continua depois de tocar em <strong>Aceito</strong>. O aceite fica registrado com data e hora. “Não aceito” não cria nada.</p>
        <ol>${TERMO.map((t) => '<li>' + t.replace(/\/excluir_dados/g, '<code>/excluir_dados</code>') + '</li>').join('')}</ol>
      </section>

      <section class="card" aria-labelledby="p-cli"><h2 id="p-cli">🔒 Aviso ao cliente final</h2>
        <p>Na primeira conversa com cada negócio, o cliente recebe: <em>“Seus dados (nome, mensagens e pedidos) ficam na plataforma Atende AI e são usados só para este atendimento. Para apagar: /excluir_dados”</em>.</p>
      </section>

      <section class="card" aria-labelledby="p-dados"><h2 id="p-dados">Quais dados e para quê</h2>
        <div class="tabela-wrap"><table><caption class="sr">Dados tratados</caption><thead><tr><th scope="col">De quem</th><th scope="col">Dados</th></tr></thead><tbody>
          <tr><th scope="row">Cliente final</th><td>Nome informado, @usuário e ID do Telegram, mensagens, itens e valores do pedido, CEP e endereço de entrega (loja virtual), modelo e placa (oficina), bairro (loja), avaliação de 1 a 5.</td></tr>
          <tr><th scope="row">Dono e equipe</th><td>Nome e @usuário do Telegram, cadastro do negócio (serviços/produtos, preços, horário, políticas, chave Pix ou link), data do aceite do termo, respostas do “antes” do piloto.</td></tr>
          <tr><th scope="row">Uso do serviço</th><td>Contagem de mensagens por dia e horários de atividade por loja (sem o conteúdo).</td></tr>
        </tbody></table></div>
        <ul>
          <li><strong>Operar o atendimento</strong>: orçamento, carrinho, frete, avisos à loja, mensagens automáticas e pós-venda (LGPD art. 7º, V).</li>
          <li><strong>Métricas do piloto</strong>: tempo de resposta, pedidos, conversão, NPS e faturamento intermediado, agregados (art. 7º, IX, com dados minimizados).</li>
          <li><strong>Segurança</strong>: por exemplo, bloqueio após tentativas erradas do código de administrador.</li>
        </ul>
        <p class="pequeno muted">Não pedimos dados sensíveis nem documentos. O bot não recebe dados de cartão.</p>
      </section>

      <section class="card" aria-labelledby="p-ve"><h2 id="p-ve">Quem vê o quê</h2>
        <ul>
          <li><strong>A loja</strong> vê pedidos e conversas dos próprios clientes (Telegram e painel com chave só dela).</li>
          <li><strong>O administrador da plataforma</strong> (<a href="#/admin">Modo plataforma</a>) vê números por loja: conversas, pedidos, status, valores, prazos, avaliações e atividade. Pela API de administração <strong>não</strong> vê nome, contato, endereço nem mensagens dos clientes.</li>
          <li><strong>Serviços usados</strong>: Telegram (conversa), Cloudflare (túnel do servidor de teste), ViaCEP (só o CEP, para cidade/UF) e GitHub Pages (hospeda este painel). Sem IA externa ligada hoje.</li>
        </ul>
      </section>

      <section class="card" aria-labelledby="p-dir"><h2 id="p-dir">Seus direitos e como apagar</h2>
        <ul>
          <li><strong>Cliente final</strong>: envie <code>/excluir_dados</code> no bot e confirme. Na hora, apagamos nome, @usuário, ID do chat, mensagens, endereço, CEP, placa e o histórico das conversas. Os pedidos ficam só como números anônimos (valor e status) e a loja é avisada.</li>
          <li><strong>Dono</strong>: <code>/excluir_dados</code> → “Pedir exclusão da loja”. O administrador confirma e a loja, com todos os pedidos, é apagada. O dono é avisado.</li>
          <li><strong>Outros pedidos</strong> (acesso, correção): fale com a loja ou mande mensagem no bot.</li>
        </ul>
        <p class="pequeno muted">A exclusão não alcança mensagens já entregues no aplicativo do Telegram de quem recebeu. Ao fim do piloto, os dados são apagados ou anonimizados em até 30 dias (incluindo cópias de segurança), salvo pedido da loja para levar os dados dela.</p>
      </section>

      <section class="card" aria-labelledby="p-seg"><h2 id="p-seg">Segurança</h2>
        <ul>
          <li>Token do bot só no servidor, nunca no navegador nem no código.</li>
          <li>Chave de leitura própria por loja; a administração usa outra chave, separada.</li>
          <li>Código de administrador só no servidor (fora do Git); a mensagem com o código é apagada do chat depois do uso.</li>
        </ul>
        <p class="pequeno muted">Texto completo: <a href="https://github.com/guilhermeromio-netto-prog/atende-ai/blob/main/docs/privacidade.md">docs/privacidade.md</a>.</p>
      </section>
    </div>`;
  }
  AT.V = AT.V || {};
  AT.V.privacidade = { titulo: 'Privacidade', render };
  AT.Privacidade = { TERMO };
})(window.AT);
