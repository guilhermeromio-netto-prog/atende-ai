# Como usar o Atende AI (modo de teste)

Existe um **bot real de teste** no Telegram: **[@Applojas10_bot](https://t.me/Applojas10_bot)**. Ele usa o mesmo motor de regras da demonstração web (catálogo, intenções e perguntas de `dados.json`) e funciona **sem IA**.

- App web (demonstração + painel): https://guilhermeromio-netto-prog.github.io/atende-ai/
- Guia dentro do app: https://guilhermeromio-netto-prog.github.io/atende-ai/#/como-usar

## Para o dono da oficina ou loja

1. Abra https://t.me/Applojas10_bot?start=dono (ou envie `/dono`).
2. Toque em **Assumir** um negócio de exemplo (já vem com catálogo) ou em **Criar meu negócio do zero**.
3. Cadastre conversando, uma coisa por mensagem:
   - `Troca de óleo R$ 180 1h`
   - `Pastilha de freio peças R$ 160 a 320 mão de obra R$ 120 1h30`
   - `Seg a sex 8h às 18h; sábado 8h às 12h`
   - `Minha oficina se chama Auto Center Silva`
4. Envie `/link` e divulgue o link para os clientes (Instagram, Google, QR code no balcão).
5. Quando um cliente pedir orçamento, você recebe a notificação com os botões **▶ Avançar** (Aprovado → Em serviço → Pronto → Entregue) e **💬 Responder cliente**. Cada avanço manda a mensagem automática certa ao cliente.
6. Acompanhe com `/painel` e `/pedidos`. O bot avisa quando um pedido entra em atenção (menos de 25% do prazo) ou estoura o SLA.
7. Para testar sozinho: `/cliente` (vira cliente do seu negócio) e `/dono` para voltar.

| Comando | O que faz |
|---|---|
| `/painel` | Indicadores: atendimentos, aprovação, 1ª resposta, SLA, faturamento, avaliação |
| `/pedidos` | Pedidos em aberto, ordenados pelo prazo, com botões |
| `/catalogo` · `/remover N` | Ver catálogo · remover item |
| `/horario` | Ver horário de funcionamento |
| `/link` | Link para os clientes (`https://t.me/Applojas10_bot?start=<negócio>`) |
| `/codigo` | Código para outra pessoa da equipe (`/dono CÓDIGO`) |
| `/conectar` | Link do painel web ligado aos dados ao vivo |
| `/cliente` · `/dono` | Alternar entre testar como cliente e modo dono |

## Para o cliente final

1. Abra o link divulgado pelo negócio (ex.: https://t.me/Applojas10_bot?start=oficina-pista-livre).
2. Conte o problema do seu jeito: “barulho ao frear”, “carro não liga”, “quero pintar o quarto”.
3. Responda: nome, modelo e placa (oficina) ou bairro de entrega (loja), e a urgência.
4. Receba o orçamento com itens, total, duração e prazo, e toque em **✅ Aprovar** ou **🙋 Falar com atendente**.
5. Escolha o horário. Depois chegam sozinhas: confirmação, aviso de início, “pronto” e a pesquisa de satisfação (1 a 5 estrelas).

`/nova` recomeça · `/trocar` escolhe outro negócio · escrever “atendente” chama uma pessoa.

## Ligar o painel web aos dados do bot

1. No Telegram, como dono, envie `/conectar`.
2. Abra o link recebido (traz o endereço da API e a chave de leitura do negócio).
3. Pedidos e Dashboard mostram a faixa **Modo conectado** e se atualizam a cada 30 s. Para desligar: Configurações → Modo conectado.

A API é **somente leitura** e exige a chave do negócio. Os pedidos reais não podem ser avançados pelo painel web; o avanço é pelos botões no Telegram.

## 🛒 Loja virtual (para quem vende online)

O bot mostra produtos, preço e estoque (entende erro de digitação), calcula frete pelo CEP, fecha o pedido com resumo itemizado (frete, desconto no Pix e total) e manda **as suas** instruções de pagamento. **O bot nunca cobra nem confirma pagamento sozinho:** o cliente toca em “💸 Já paguei”, você recebe o aviso, confere no banco e confirma.

- **Criar a sua loja:** https://t.me/Applojas10_bot?start=dono
- **Ver a loja de exemplo funcionando** (produtos fictícios, não pague nada): https://t.me/Applojas10_bot?start=loja-exemplo-online

### 1. Criar a loja
1. Abra https://t.me/Applojas10_bot?start=dono e toque em **➕ Criar meu negócio do zero**.
2. Escreva o nome da loja (ex.: `Loja do Mano`).
3. Escolha **🛒 Loja virtual (catálogo de exemplo)** (10 produtos fictícios para testar) ou **🛒 Loja virtual (catálogo vazio)**.

### 2. Cadastrar produtos e políticas conversando (uma coisa por mensagem)
- Produto: `Fone bluetooth R$ 89 estoque 12 entrega 3 dias` (mandar o mesmo nome de novo atualiza preço/estoque)
- Frete grátis: `Frete grátis acima de R$ 199` · frete fixo: `Frete fixo R$ 19,90`
- Frete por região do CEP: `Frete SP R$ 15 2 dias, Sudeste R$ 22 4 dias, outros R$ 35 8 dias`
- Prazo de envio: `Envio em 1 dia útil`
- Pagamento: `Pix com 5% de desconto, cartão em até 6x`
- Chave Pix (texto que o cliente vê): `Chave pix: sua-chave-aqui` · link do cartão: `Link do cartão: https://...`
- Troca: `Troca em até 7 dias por arrependimento` (padrão já vem com o texto do CDC, art. 49)
- Conferir: `/catalogo` e `/politicas` · remover: `/remover N`

### 3. Divulgar e testar
1. `/link` → coloque o link na bio do Instagram, no site ou no WhatsApp.
2. Teste com `/cliente`: “tem fone bluetooth?” → adicionar ao carrinho → **Fechar pedido** → nome, CEP, endereço, Pix ou cartão → **Confirmar**. Volte com `/dono`.
3. Cada pedido chega com botões: **✅ Confirmar pagamento** (depois de conferir no banco; o estoque baixa sozinho) → **▶ Separando** → **📦 Informar rastreio e enviar** (você digita o código, ou `sem`) → **Entregue** (sai o pós-venda com avaliação).
4. O cliente pode perguntar “cadê meu pedido EC-3005?” (recebe status e rastreio), “quanto é o frete pro CEP 30140-071?” ou “quero trocar” (abre solicitação com motivo e a sua política).
5. Carrinho esquecido recebe lembrete automático uma vez (modo teste: 10 minutos).
6. `/painel` mostra pedidos, faturamento, ticket médio, conversão carrinho → pago, carrinhos abandonados, envio no prazo e trocas. `/conectar` abre o mesmo painel no navegador.

## Limitações do modo de teste

- O bot e a API rodam num computador de teste. **Se ele desligar ou reiniciar, o bot para** até ser religado.
- O endereço do túnel (`*.trycloudflare.com`) muda a cada reinício: peça `/conectar` de novo.
- Sem IA: entendimento por palavras-chave. Relatos muito diferentes caem em “qual destas opções é mais parecida?”.
- Valores são estimativas do catálogo. Sem pagamento, nota fiscal ou WhatsApp. Na loja virtual o bot só repassa a chave Pix/link cadastrados pelo lojista; a confirmação é sempre manual.
- Frete por CEP: região pelo 1º dígito do CEP (com consulta pública ViaCEP para cidade/UF quando disponível). Não é cotação de Correios ou transportadora.
- Pós-venda sai 2 minutos após “Entregue” (para facilitar o teste); na versão final, 1 dia depois.

## Caminho para a fase 2

1. **Sempre ligado:** Cloudflare Workers (ou servidor pequeno) com webhook do Telegram + Postgres. Token do bot só no servidor.
2. **Grok com créditos:** texto livre com tool calling; preço e prazo continuam vindo do catálogo; regras como plano B.
3. **WhatsApp:** segundo adaptador do mesmo motor, via WhatsApp Cloud API.

Detalhes em [docs/arquitetura.md](docs/arquitetura.md).

## Para quem mantém o servidor de teste

```bash
# iniciar (o token vem só da variável de ambiente; nunca vai para arquivo)
cd bot && setsid nohup ./run.sh >/dev/null 2>&1 &      # bot com reinício automático → data/bot.log
setsid nohup ./tunnel.sh >/dev/null 2>&1 &             # túnel cloudflared → data/tunnel_url.txt
python3 test_bot.py                                    # testes com updates simulados (sem rede)
# ATENDE_ABANDONO_MIN=10 (lembrete de carrinho) · ATENDE_POSVENDA_MIN=2 · ATENDE_SEM_REDE=1 desliga o ViaCEP
```

Parar: `kill $(cat bot/data/run.pid) $(cat bot/data/bot.pid)` e `kill $(cat bot/data/tunnel.pid); pkill -f "cloudflared tunnel"`.
