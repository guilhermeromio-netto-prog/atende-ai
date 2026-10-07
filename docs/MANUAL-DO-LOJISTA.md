# Manual do lojista · Atende AI

> Versão do piloto · byGui. Este manual serve para qualquer lojista ou oficina que entra no Atende AI. O primeiro a usar é o nosso **piloto fundador**.

## 1. Boas-vindas

Seja bem-vindo ao **Atende AI**, a IA do Guilherme (**byGui**).

A ideia é simples: você continua cuidando do que importa no seu negócio, e o Atende AI cuida da parte repetitiva do atendimento. Ele responde o cliente na hora, monta orçamento ou pedido, acompanha cada etapa e te mostra os números do seu negócio.

Você não precisa instalar nada nem entender de tecnologia. Tudo acontece numa conversa no Telegram, com botões. E você está sempre no controle: nada de pagamento, desconto ou promessa sai sem o seu ok.

## 2. O que é o sistema

O Atende AI é um **plugin de inteligência** que funciona por meio de um bot (um atendente automático) no Telegram. Ele:

- **Atende:** responde o cliente a qualquer hora, entende erros de digitação e pergunta só o que falta.
- **Orça e vende:** monta o orçamento (oficina e loja) ou o carrinho com frete pelo CEP (loja virtual), com os preços que **você** cadastrou.
- **Acompanha:** cada pedido segue uma esteira (ex.: Aguardando pagamento → Pago → Separando → Enviado → Entregue) e o cliente recebe a mensagem certa em cada etapa.
- **Gera dados:** tempo de resposta, pedidos, conversão, carrinhos abandonados, prazo de envio e avaliação dos clientes, num painel simples.

Hoje ele funciona com regras e com o catálogo que você cadastrou, sem custo de IA paga. A IA conversacional (Grok) entra numa fase seguinte.

Ele atende três tipos de negócio prontos: **oficina**, **loja física** e **loja virtual**.

## 3. O que você ganha

Estes são os **objetivos** do Atende AI. Os números reais do seu negócio vamos medir juntos durante o piloto, sem promessas antecipadas.

- **Resposta 24 horas:** o cliente é atendido na hora, mesmo de madrugada ou quando você está ocupado.
- **Orçamento e pedido automáticos:** preço, frete, desconto no Pix e prazo calculados com as suas regras.
- **Menos carrinho abandonado:** quem esquece o carrinho recebe um lembrete educado.
- **Prazo sob controle (SLA):** o bot te avisa antes de um pedido atrasar.
- **Pós-venda:** depois da entrega, o cliente recebe agradecimento e pedido de avaliação.
- **Secretário do dono:** mande "agendar reunião com João amanhã 15h, pagar conta de luz dia 12" e ele organiza agenda, lembretes e contas.
- **Painel de resultados:** resumo diário às 19h no Telegram e um painel no computador com os números do negócio.

## 4. Missão, Visão e Valores

> **Versão 1, para o Guilherme ajustar.**

**Missão:** dar ao pequeno lojista o atendimento e os dados de uma grande empresa, de um jeito simples e acessível.

**Visão:** ser o jeito mais fácil de um pequeno negócio brasileiro atender bem, vender mais e decidir com dados, em qualquer canal de mensagem.

**Valores:**

- **Transparência com dados (LGPD):** você e seus clientes sabem quais dados ficam guardados, para quê, e podem pedir para apagar.
- **Humano no controle:** o bot nunca cobra, nunca confirma pagamento e nunca marca conta como paga sem o seu ok.
- **Simplicidade plug and play:** um link, quatro passos, e está funcionando.
- **Resultado medido:** comparamos o antes e o depois com números reais, não com achismo.
- **Parceria:** crescemos junto com quem usa. O seu feedback decide as próximas melhorias.

## 5. O que você está recebendo

1. **Link Pro de cadastro:** https://t.me/Applojas10_bot?start=pro-lojavirtual
2. **Cadastro em 4 passos** (menos de 3 minutos): nome da loja, aceite do termo do piloto, frete e pagamento com botões, e a lista de produtos colada de uma vez.
3. **Catálogo:** seus produtos com preço, estoque e prazo de envio. Para mudar depois, é só escrever (ex.: `Fone bluetooth R$ 89 estoque 12`). Ver tudo: `/catalogo`.
4. **Políticas:** frete, desconto no Pix, parcelas, chave Pix e política de troca (já vem com o texto do Código de Defesa do Consumidor). Ver e ajustar: `/politicas`.
5. **Link da sua loja:** o endereço que você coloca na bio do Instagram, no WhatsApp e no site. Ver: `/link`. Textos prontos para divulgar: `/modelos`.
6. **Automações ligadas:** lembrete de carrinho abandonado, mensagens de cada etapa do pedido, pós-venda com avaliação e alerta de prazo.
7. **Resumo diário às 19h:** pedidos do dia, pagos, faturamento e o que falta enviar. A qualquer hora: `/resumo`.
8. **Painel conectado:** envie `/conectar` e abra o link no computador para ver pedidos e indicadores ao vivo.
9. **Secretário do dono:** agenda, lembretes e contas a pagar numa mensagem só (`/agenda`, `/lembretes`, `/contas`).
10. **Suporte direto com o Guilherme:** durante o piloto, qualquer dúvida ou problema, é só chamar.

## 6. Como usar no dia a dia

**De manhã (5 minutos)**

- Abra o Telegram e veja `/pedidos`: o que está pago e precisa ser separado.
- Confira se algum cliente informou "Já paguei" e confirme no banco antes de tocar em **✅ Confirmar pagamento**.

**Durante o dia**

- Cada pedido novo chega com botões. O caminho é: **Confirmar pagamento → Separando → Informar rastreio e enviar → Entregue**.
- Se o cliente pedir para falar com uma pessoa, você recebe o aviso e responde pelo botão **💬 Responder cliente**.
- Mudou preço ou estoque? Escreva, por exemplo, `Garrafa térmica R$ 59 estoque 20`.
- Lembrou de algo? Escreva para o Secretário: `lembrar de postar no Instagram amanhã 10h`.

**No fim do dia**

- Às 19h chega o **resumo do dia**. Veja o que ficou para enviar amanhã.
- Uma vez por semana, olhe o `/painel` (ou o painel no computador) para acompanhar a evolução.

**Comandos úteis**

- `/pedidos` pedidos em aberto · `/painel` indicadores · `/resumo` resumo do dia
- `/catalogo` produtos · `/politicas` frete, pagamento e trocas · `/link` link da loja · `/modelos` textos prontos
- `/agenda` · `/lembretes` · `/contas` Secretário do dono
- `/cliente` testar como cliente (volte com `/dono`) · `/plano` recursos do seu plano · `/manual` este manual · `/ajuda` todos os comandos

## 7. Como funciona o piloto

- **Onde roda:** nesta fase, o bot funciona num servidor de teste, no computador do Guilherme. É grátis e rápido de ajustar, mas tem limitações (veja abaixo).
- **Duração:** de 2 a 4 semanas.
- **O que medimos:** tempo de resposta ao cliente, número de pedidos, conversão (de carrinho para pago), carrinhos recuperados e satisfação dos clientes (NPS, pela avaliação de 1 a 5).
- **Antes e depois:** no começo, você conta como era antes (`/antes resposta 2h vendas R$ 8.000 pedidos 40`, com os seus números) para compararmos no final.
- **Check-in semanal:** uma conversa rápida por semana com o Guilherme para ver números, dúvidas e ajustes.

**Limitações honestas do modo de teste**

- Se o computador de teste desligar ou reiniciar, o bot para até ser religado. Se o bot não responder, avise o Guilherme.
- O link do painel no computador muda quando o servidor reinicia; é só pedir `/conectar` de novo.
- O bot entende por palavras-chave (sem IA paga ainda). Perguntas muito diferentes caem em opções para o cliente escolher ou em "falar com atendente".
- Frete por CEP é calculado pela região do CEP com as suas regras; não é cotação dos Correios.
- O bot não cobra, não emite nota fiscal e não confirma pagamento: ele mostra a sua chave Pix e você confirma.
- Por enquanto, só Telegram. WhatsApp vem na próxima fase.

## 8. Seu papel como case de sucesso

Você é o **piloto fundador**: o primeiro a usar e a ajudar a moldar o Atende AI.

**O que pedimos:**

- **Uso real:** colocar o link da loja para os seus clientes de verdade.
- **Feedback sincero:** o que funciona, o que atrapalha, o que falta.
- **Autorização para usar as métricas:** os números do piloto podem virar um estudo de caso. Nome da loja, números e depoimento só são usados **com o seu consentimento explícito**, por escrito, e você pode pedir para não aparecer.

**O que você recebe como piloto fundador:**

- Plano Pro sem cobrança durante o piloto.
- Suporte direto e prioridade nas melhorias que você pedir.
- Condição especial depois do piloto: **[a definir pelo Guilherme]**.

## 9. Privacidade e dados

- Seus dados e os dos seus clientes ficam na plataforma Atende AI e são usados só para o atendimento e para as métricas do piloto.
- Na primeira conversa, cada cliente recebe um aviso curto dizendo isso e como apagar.
- Qualquer pessoa pode apagar os próprios dados com `/excluir_dados`. Você pode pedir a exclusão da sua loja pelo mesmo comando.
- Política completa: https://guilhermeromio-netto-prog.github.io/atende-ai/#/privacidade

## 10. Próximos passos e roadmap

1. **Hoje:** Telegram, com regras e o seu catálogo, em servidor de teste.
2. **Servidor sempre ligado:** o bot passa para um servidor na nuvem, sem depender do computador de teste.
3. **WhatsApp:** o mesmo atendimento no WhatsApp oficial (API do WhatsApp Business).
4. **IA Grok:** conversa mais natural, entendendo qualquer jeito de perguntar. Preço e prazo continuam vindo do seu catálogo.

## 11. Perguntas frequentes

**Preciso instalar alguma coisa?**
Não. Só o Telegram, que você provavelmente já tem.

**O bot pode cobrar o cliente ou mexer no meu dinheiro?**
Não. Ele só mostra a sua chave Pix ou o seu link de pagamento. Quem confirma o pagamento é você, depois de conferir no banco.

**E se o cliente quiser falar com uma pessoa?**
Ele escreve "atendente" a qualquer momento e você recebe o aviso para responder.

**Posso mudar preço, estoque ou frete depois?**
Sim, a qualquer hora, escrevendo no bot. Ex.: `Frete grátis acima de R$ 199`.

**O que acontece se o bot parar?**
No piloto, ele roda num servidor de teste. Se parar de responder, avise o Guilherme para religar. Os seus dados não se perdem.

**Quanto custa?**
Durante o piloto, nada. A condição depois do piloto será combinada com o Guilherme.

**Meus clientes podem apagar os dados deles?**
Sim, com `/excluir_dados`, na hora.

**Funciona para oficina ou loja física também?**
Sim. O Atende AI já vem pronto para oficina, loja física e loja virtual.

---

Dúvidas? Fale com o Guilherme. Atende AI · byGui.
