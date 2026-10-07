# Atende AI — CRM com atendimento automático (demonstração)

Protótipo de produto para **oficinas mecânicas, lojas e lojas virtuais**: o cliente conversa com o bot (canal principal **Telegram**; **WhatsApp em breve**), recebe orçamento automático com itens do catálogo, prazo/SLA e botões para aprovar, e o dono acompanha tudo num painel com pedidos, SLA e dashboard.

> **Demonstração — IA simulada.** As respostas são geradas por regras e palavras-chave (`dados.json`). Não há integração real com Telegram, WhatsApp ou modelos de IA. Os 33 pedidos iniciais são **dados de exemplo fictícios**, salvos só no navegador (localStorage).

**Site:** https://guilhermeromio-netto-prog.github.io/atende-ai/

## Telas (SPA por hash)

| Rota | O que mostra |
|---|---|
| `#/` | Proposta de valor, troca Oficina/Loja/Loja virtual, prévia da conversa no Telegram |
| `#/onboarding` | O dono conversa com o bot de cadastro: "troca de óleo R$ 180 1h" vira linha do catálogo (editável), horário de funcionamento |
| `#/atendimento` | Visão do cliente final no Telegram: sintoma → perguntas (nome, modelo, placa, urgência) → orçamento itemizado → Aprovar/Falar com atendente → agendamento. Abre o pedido |
| `#/pedidos` | Kanban/lista (Novo → Orçado → Aprovado → Em serviço → Pronto → Entregue), SLA colorido, gaveta com conversa e cadeia de automações, "Simular avanço" |
| `#/dashboard` | KPIs, atendimentos por dia, funil, serviços mais pedidos, situação do SLA, pedidos em risco, filtros e exportação CSV |
| `#/admin` | Modo plataforma (dono da plataforma): todas as lojas, KPIs globais, detalhe por loja, saúde do piloto, antes × depois, CSV. Dados reais só com a chave de administrador; sem ela, demonstração |
| `#/privacidade` | Privacidade e termo de uso do piloto (LGPD) |
| `#/secretario` | Secretário do dono: uma mensagem com vários pedidos vira tarefas (agenda, lembretes, contas), pergunta só o que falta, painel por status |
| `#/manual` | Manual do lojista (fonte: `docs/MANUAL-DO-LOJISTA.md`), pronto para imprimir ou salvar em PDF |
| `#/config` | Modelos de mensagem com `{cliente}` `{servico}` `{prazo}`…, SLA por prioridade, canais, exportar/importar/restaurar dados |

## Estrutura

```
index.html
css/styles.css          tokens em :root, tema Cockpit + temas de canal
js/util.js              formatação, horas úteis, utilitários
js/store.js             estado em localStorage, semeado de dados.json
js/motor.js             orçamento, SLA, automações, parser do cadastro, intenção
js/conversa.js          motor de conversa do cliente (independente de canal)
js/ecommerce.js         loja virtual: busca tolerante a erros, frete por CEP, carrinho, políticas, parser do lojista
js/conversa-ecom.js     conversa do cliente da loja virtual (carrinho → pagamento do lojista → rastreio/troca)
js/admin.js             Modo plataforma (#/admin): lê /api/admin/export com a chave de administrador
js/privacidade.js       página de privacidade e termo do piloto
js/secretario.js        Secretário do dono (motor JS + simulação + painel)
js/doc.js · manual.js   renderizador mínimo de Markdown · página do manual
bot/pro.py              versão Pro: assistente de 1 link, /plano, /modelos, resumo diário 19h, boas-vindas
bot/secretario.py       Secretário do dono no bot
docs/MANUAL-DO-LOJISTA.md · docs/PLAYBOOK-ESCALA.md · docs/secretario/ (spec de origem)
js/canais/base.js       núcleo de renderização de conversa
js/canais/telegram.js   adaptador Telegram (principal)
js/canais/whatsapp.js   adaptador WhatsApp (em breve)
js/inicio.js, onboarding.js, atendimento.js, pedidos.js, dashboard.js, config.js, app.js
dados.json              catálogos, intenções, perguntas, automações, SLA, pedidos de exemplo
docs/arquitetura.md     proposta da fase 2 (Telegram Bot API + Grok, depois WhatsApp)
bot/                    bot REAL de teste no Telegram (Python, só biblioteca padrão) + API de leitura
COMO-USAR.md            guia para donos e clientes finais
```

## Loja virtual (🛒)

Terceiro segmento, no mesmo motor e no mesmo `dados.json` do bot e do site: produtos com preço/estoque/prazo de envio, políticas de frete (grátis acima de, fixo ou tabela por região do CEP), Pix com desconto, parcelas, chave Pix/link do lojista (nunca simula pagamento), troca (CDC 7 dias). Pipeline: Novo → Aguardando pagamento → Pago → Separando → Enviado (rastreio) → Entregue, com trocas/atendimento em coluna própria. KPIs: pedidos, faturamento, ticket médio, conversão carrinho → pago, carrinhos abandonados, envio no prazo, trocas. Passo a passo em [COMO-USAR.md](COMO-USAR.md#-loja-virtual-para-quem-vende-online).

## Plataforma, privacidade e piloto

- **Administrador:** `/admin <código>` (código gerado na 1ª execução em `bot/data/admin.json`, fora do Git) libera `/plataforma`, `/lojas`, `/loja <slug>`, `/piloto <slug>`, `/admin_conectar` e `/excluir_loja <slug>`. API `/api/admin/*` com chave própria (`X-Atende-Admin`), separada das chaves das lojas e sem dados pessoais dos clientes.
- **Termo do piloto:** criar/assumir loja exige “Aceito” (registrado com data e hora). Cliente recebe aviso de privacidade na 1ª mensagem; `/excluir_dados` apaga/anonimiza (cliente) ou pede exclusão da loja (dono → admin). Ver [docs/privacidade.md](docs/privacidade.md).
- **Piloto:** `piloto: true` por loja, “antes” preenchido pelo dono com `/antes`, saúde do piloto (dias ativos, mensagens/dia, pedidos, NPS). Playbook: [docs/piloto.md](docs/piloto.md).

## Versão Pro (plug and play) e Secretário do dono

- **Assistente Pro de 1 link:** https://t.me/Applojas10_bot?start=pro-lojavirtual → nome da loja → termo do piloto → presets de frete e pagamento (+ chave Pix) → lista de produtos colada (`nome; preço; estoque; dias`, CSV ou texto livre). Em menos de 3 minutos a loja está no ar com `plano: "pro"`, automações ligadas (carrinho abandonado, pós-venda, alerta de SLA), modelos de mensagem (`/modelos`) e **resumo diário às 19h** (America/Sao_Paulo) no Telegram do dono. `/plano` lista os recursos; admin liga numa loja existente com `/pro <slug>`. Selo ⭐ Pro no Dashboard e no Modo plataforma.
- **Secretário do dono:** “Agendar reunião com João, pagar conta de luz, lembrar de comprar leite” vira 3 tarefas; pergunta só o que falta numa mensagem; agenda nunca sem dia e hora; lembrete sem hora = hoje 18h; conta fica `aguardando_ok` até o dono tocar em “Paguei”. `/agenda`, `/lembretes`, `/contas`, API `/api/secretario`. Spec: [docs/secretario/](docs/secretario/).
- **Manual do lojista** ([docs/MANUAL-DO-LOJISTA.md](docs/MANUAL-DO-LOJISTA.md), `#/manual`, `/manual` e `/missao` no bot) e **playbook de escala** interno ([docs/PLAYBOOK-ESCALA.md](docs/PLAYBOOK-ESCALA.md), também no `#/admin`).

## Bot de teste no Telegram

Além da demonstração, há um bot real de teste: **[@Applojas10_bot](https://t.me/Applojas10_bot)** (pasta `bot/`, Python sem dependências, long polling, mesmo `dados.json`). Veja [COMO-USAR.md](COMO-USAR.md). Ele roda num computador de teste: se esse computador desligar, o bot para.

## Rodar localmente

HTML/CSS/JS puro, sem build e sem dependências:

```bash
python3 -m http.server 8000
# abra http://localhost:8000
```

(Abrir o `index.html` direto do disco não funciona porque o navegador bloqueia o `fetch` do `dados.json`.)

## Fase 2

Veja [docs/arquitetura.md](docs/arquitetura.md): Telegram Bot API via webhook num servidor pequeno (o token do bot nunca fica no navegador), backend multi-tenant com Postgres, Grok com tool calling, fila para a cadeia de mensagens, LGPD, planos, custos e riscos. WhatsApp Cloud API entra depois como segundo adaptador do mesmo motor.

---

byGui
