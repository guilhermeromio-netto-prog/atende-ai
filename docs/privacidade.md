# Privacidade e termo de uso do piloto · Atende AI

*Versão 1 · 7 de outubro de 2026 · também em https://guilhermeromio-netto-prog.github.io/atende-ai/#/privacidade*

> Resumo em linguagem simples para a fase de piloto. Não substitui orientação jurídica. Antes de cobrar pelo serviço, revisar com um advogado.

## Quem opera

A plataforma **Atende AI** é operada por **Guilherme Romio Netto (byGui)**, hoje em **modo de teste/piloto**: um bot no Telegram ([@Applojas10_bot](https://t.me/Applojas10_bot)) e um painel web, rodando num servidor de teste.

Na linguagem da LGPD (Lei 13.709/2018):

- cada **loja** decide como atende os próprios clientes e é a **controladora** desses dados;
- o Atende AI trata esses dados **em nome da loja**, como **operador**;
- as métricas agregadas do piloto (sem identificar ninguém) são usadas pelo Atende AI para melhorar o serviço.

## Termo de uso do piloto (o que o dono aceita no bot)

Quando alguém cria ou assume uma loja, o bot mostra este termo e só continua depois do **Aceito**. O aceite fica registrado com data e hora:

1. Os dados do negócio e dos clientes (cadastro, conversas e pedidos) ficam na plataforma Atende AI, operada por Guilherme Romio Netto (byGui), num servidor de teste.
2. Eles são usados só para operar o atendimento e calcular as métricas do piloto (tempo de resposta, pedidos, conversão, avaliação). Não são vendidos nem repassados a terceiros.
3. Os clientes são avisados na 1ª mensagem e podem pedir a exclusão com `/excluir_dados`. O dono também pode pedir a exclusão da loja com `/excluir_dados`.
4. O bot não processa pagamentos: ele só repassa as instruções que o dono cadastrar. Modo de teste, sem garantia de disponibilidade.

Quem toca em “Não aceito” não ativa nada; nada é criado.

## Aviso ao cliente final

Na primeira conversa com cada negócio, o cliente recebe uma linha:

> 🔒 Seus dados (nome, mensagens e pedidos) ficam na plataforma Atende AI e são usados só para este atendimento. Para apagar: /excluir_dados

## Quais dados

| De quem | Dados |
|---|---|
| Cliente final | Nome que ele informa, @usuário e ID do Telegram, mensagens da conversa, itens e valores do pedido, CEP e endereço de entrega (loja virtual), modelo e placa do carro (oficina), bairro (loja), avaliação de 1 a 5 |
| Dono e equipe | Nome e @usuário do Telegram, ID do chat, cadastro do negócio (serviços/produtos, preços, horário, políticas, chave Pix ou link de pagamento), data do aceite do termo, respostas do “antes” do piloto |
| Uso do serviço | Contagem de mensagens por dia e por loja, horários de atividade (sem o conteúdo), para a saúde do piloto |

Não pedimos dados sensíveis (saúde, religião, biometria etc.) nem documentos. O bot não recebe dados de cartão.

## Para que

- **Operar o atendimento:** entender o pedido, montar orçamento ou carrinho, calcular frete, avisar a loja, mandar mensagens automáticas e o pós-venda (LGPD art. 7º, V: procedimentos preliminares e execução de contrato a pedido do titular).
- **Métricas do piloto:** tempo de resposta, pedidos, conversão, NPS e faturamento intermediado, agregados por loja e na plataforma (art. 7º, IX: legítimo interesse, com dados minimizados).
- **Segurança:** evitar abuso (por exemplo, bloqueio após tentativas erradas do código de administrador).

## Quem vê o quê

- **A loja** vê os pedidos e as conversas dos próprios clientes, no Telegram e no painel (`/conectar`, com chave só dela).
- **O administrador da plataforma** vê números por loja: conversas, pedidos, status, valores, prazos, avaliações e atividade. Pela API de administração ele **não** vê nome, contato, endereço nem mensagens dos clientes (minimização).
- **Serviços usados:** Telegram (canal da conversa), Cloudflare (túnel que expõe a API de leitura do servidor de teste), ViaCEP (recebe só o CEP para achar cidade e UF) e GitHub Pages (hospeda o painel; os dados ao vivo vão direto do servidor para o navegador com a chave). Hoje não há IA externa ligada; se for ligada, só o texto do relato vai para classificação, sem nome nem contato.

## Por quanto tempo

Durante o piloto, num arquivo do servidor de teste. Ao fim do piloto, os dados são **apagados ou anonimizados em até 30 dias**, salvo se a loja pedir para levar os dados dela. Cópias de segurança feitas em atualizações do servidor também são apagadas nesse prazo.

## Seus direitos e como exercer

A LGPD (art. 18) garante confirmação e acesso, correção, anonimização ou eliminação, informação sobre compartilhamento e revogação do consentimento.

- **Cliente final:** envie `/excluir_dados` no bot e confirme. Na hora, apagamos nome, @usuário, ID do chat, mensagens, endereço, CEP, placa e o histórico das conversas em todos os negócios. Os pedidos ficam só como números anônimos (valor e status), para as contas da loja, e a loja é avisada.
- **Dono:** `/excluir_dados` → “Pedir exclusão da loja”. O administrador recebe o pedido, confirma e a loja, com todos os pedidos, é apagada. O dono é avisado.
- **Outros pedidos** (acesso, correção): fale com a loja ou mande mensagem no bot.

**O que a exclusão não alcança:** mensagens já entregues ficam no aplicativo do Telegram de quem recebeu (o seu e o do dono); o bot não consegue apagar o histórico no aparelho de outra pessoa.

## Segurança

- Token do bot só em variável de ambiente do servidor, nunca no navegador nem no código.
- Cada loja tem uma chave de leitura própria; a administração usa outra chave, separada.
- O código de administrador fica só no servidor (fora do Git) e a mensagem com o código é apagada do chat depois do uso.
- Servidor de teste: sem garantia de disponibilidade. Não use para dados que não sejam do atendimento.
