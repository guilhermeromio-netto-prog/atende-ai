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

## Limitações do modo de teste

- O bot e a API rodam num computador de teste. **Se ele desligar ou reiniciar, o bot para** até ser religado.
- O endereço do túnel (`*.trycloudflare.com`) muda a cada reinício: peça `/conectar` de novo.
- Sem IA: entendimento por palavras-chave. Relatos muito diferentes caem em “qual destas opções é mais parecida?”.
- Valores são estimativas do catálogo. Sem pagamento, nota fiscal ou WhatsApp.
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
```

Parar: `kill $(cat bot/data/run.pid) $(cat bot/data/bot.pid)` e `kill $(cat bot/data/tunnel.pid); pkill -f "cloudflared tunnel"`.
