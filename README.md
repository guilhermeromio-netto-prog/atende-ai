# Atende AI — CRM com atendimento automático (demonstração)

Protótipo de produto para **oficinas mecânicas e lojas**: o cliente conversa com o bot (canal principal **Telegram**; **WhatsApp em breve**), recebe orçamento automático com itens do catálogo, prazo/SLA e botões para aprovar, e o dono acompanha tudo num painel com pedidos, SLA e dashboard.

> **Demonstração — IA simulada.** As respostas são geradas por regras e palavras-chave (`dados.json`). Não há integração real com Telegram, WhatsApp ou modelos de IA. Os 25 pedidos iniciais são **dados de exemplo fictícios**, salvos só no navegador (localStorage).

**Site:** https://guilhermeromio-netto-prog.github.io/atende-ai/

## Telas (SPA por hash)

| Rota | O que mostra |
|---|---|
| `#/` | Proposta de valor, troca Oficina/Loja, prévia da conversa no Telegram |
| `#/onboarding` | O dono conversa com o bot de cadastro: "troca de óleo R$ 180 1h" vira linha do catálogo (editável), horário de funcionamento |
| `#/atendimento` | Visão do cliente final no Telegram: sintoma → perguntas (nome, modelo, placa, urgência) → orçamento itemizado → Aprovar/Falar com atendente → agendamento. Abre o pedido |
| `#/pedidos` | Kanban/lista (Novo → Orçado → Aprovado → Em serviço → Pronto → Entregue), SLA colorido, gaveta com conversa e cadeia de automações, "Simular avanço" |
| `#/dashboard` | KPIs, atendimentos por dia, funil, serviços mais pedidos, situação do SLA, pedidos em risco, filtros e exportação CSV |
| `#/config` | Modelos de mensagem com `{cliente}` `{servico}` `{prazo}`…, SLA por prioridade, canais, exportar/importar/restaurar dados |

## Estrutura

```
index.html
css/styles.css          tokens em :root, tema Cockpit + temas de canal
js/util.js              formatação, horas úteis, utilitários
js/store.js             estado em localStorage, semeado de dados.json
js/motor.js             orçamento, SLA, automações, parser do cadastro, intenção
js/conversa.js          motor de conversa do cliente (independente de canal)
js/canais/base.js       núcleo de renderização de conversa
js/canais/telegram.js   adaptador Telegram (principal)
js/canais/whatsapp.js   adaptador WhatsApp (em breve)
js/inicio.js, onboarding.js, atendimento.js, pedidos.js, dashboard.js, config.js, app.js
dados.json              catálogos, intenções, perguntas, automações, SLA, pedidos de exemplo
docs/arquitetura.md     proposta da fase 2 (Telegram Bot API + Grok, depois WhatsApp)
bot/                    bot REAL de teste no Telegram (Python, só biblioteca padrão) + API de leitura
COMO-USAR.md            guia para donos e clientes finais
```

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
