# Playbook de escala · Atende AI (interno, para o Guilherme)

> Documento interno de trabalho. Os campos entre colchetes (`[ ]`) são para você preencher; nenhum número aqui é resultado real. Complementa o [playbook do piloto](piloto.md).

## 1. Do piloto ao case

Ao fim das 2 a 4 semanas do piloto fundador, transforme os dados em um estudo de caso de uma página. Os números saem do Modo plataforma (`/admin_conectar` → loja → **Exportar CSV**) e do `/antes` preenchido pelo lojista.

**Regra de ouro:** nome da loja, números e depoimento só entram no case com **autorização explícita e por escrito** do lojista. Sem autorização, use "uma loja virtual de [segmento]" e números arredondados.

### Template de case

| Campo | Antes do Atende AI | Depois (semanas 1–4) |
|---|---|---|
| Segmento e porte | [ex.: loja virtual de eletrônicos, 1 pessoa] | — |
| Tempo médio de 1ª resposta | [ ] | [ ] |
| Pedidos por mês | [ ] | [ ] (projeção pelas semanas do piloto) |
| Vendas por mês (R$) | [ ] | [ ] |
| Conversão carrinho → pago | [não medido] | [ ] |
| Carrinhos recuperados | [não medido] | [ ] |
| Conversas resolvidas sem atendente | — | [ ] % |
| Avaliação média / NPS | [não medido] | [ ] |
| Horas economizadas por semana (estimativa) | — | [ ] |

- **Desafio (2 linhas):** [como era o atendimento antes]
- **Solução (2 linhas):** Atende AI Pro no Telegram: catálogo, frete por CEP, pedido com Pix do lojista, automações e resumo diário.
- **Resultado (3 bullets com números autorizados):** [ ]
- **Citação (com autorização):** "[ ]" — [nome/cargo ou "lojista piloto"]
- **Autorização registrada em:** [data, meio]

## 2. Para quem oferecer

Os três segmentos já estão prontos no motor e no site (botões Oficina, Loja e Loja virtual):

| Segmento | Dor principal | O que mostrar |
|---|---|---|
| **Oficina** | Cliente pergunta preço por WhatsApp e some; orçamento demora | Relato livre ("barulho ao frear") → orçamento com faixa de peças e mão de obra → agendamento → avisos de "pronto" |
| **Loja física** (material de construção, pet, bairro) | Perguntas repetidas de preço, estoque e entrega | Catálogo, orçamento com entrega por bairro, prazos e pós-venda |
| **Loja virtual** | Responder 24h, carrinho abandonado, Pix manual | Busca tolerante a erro, frete por CEP, Pix do lojista, "Já paguei", rastreio, resumo às 19h |

Onde achar: indicações do piloto fundador, comércio do bairro, grupos de lojistas, oficinas próximas, lojistas do Instagram que respondem "chama no direct".

## 3. Pitch de 30 segundos

> "Sabe quando o cliente pergunta preço, frete ou prazo e você demora a responder porque está atendendo outra pessoa? O Atende AI é um atendente automático no Telegram (e em breve no WhatsApp) que responde na hora, com os seus preços e as suas regras, monta o orçamento ou o pedido e te avisa só quando precisa de você. Ele nunca cobra nem confirma pagamento sozinho. Em 3 minutos sua loja está no ar, e todo dia às 19h você recebe o resumo do dia. Quer ver funcionando agora?"

## 4. Roteiro de demo (10 minutos, usando o site)

Site: https://guilhermeromio-netto-prog.github.io/atende-ai/

1. **Início (1 min):** escolha o segmento do cliente no topo (Oficina, Loja ou Loja virtual). A página muda o texto e o exemplo.
2. **Atendimento (3 min):** faça o papel do cliente dele. Oficina: "barulho ao frear". Loja virtual: "tem fone blutooth?" → carrinho → CEP → Pix → "Já paguei".
3. **Pedidos (2 min):** mostre o kanban, o prazo (SLA) colorido e o avanço com mensagem automática.
4. **Dashboard (2 min):** indicadores, funil, selo Pro e resumo. Destaque: "estes são números de exemplo; no piloto medimos os seus".
5. **Secretário (1 min):** "Agendar reunião com João, pagar conta de luz, lembrar de comprar leite".
6. **Bot real (1 min):** abra https://t.me/Applojas10_bot?start=loja-exemplo-online no celular dele. Feche com: "Quer que eu crie a sua agora? Leva 3 minutos."

## 5. Onboarding padrão de um novo cliente

1. Envie o link Pro: https://t.me/Applojas10_bot?start=pro-lojavirtual (loja virtual). Para oficina ou loja física: https://t.me/Applojas10_bot?start=dono → **Criar meu negócio do zero**; depois ligue o Pro com `/pro <slug>`.
2. O lojista aceita o **termo do piloto** (obrigatório, registrado com data e hora).
3. Confira em `/lojas` que a loja apareceu e anote o slug. Se for piloto: `/piloto <slug>`.
4. Peça o "antes" (`/antes resposta 2h vendas R$ 8.000 pedidos 40`, com os números dele).
5. Mande o manual: https://guilhermeromio-netto-prog.github.io/atende-ai/#/manual
6. Combine o check-in semanal e o canal de suporte.
7. Na primeira semana, olhe `/loja <slug>` a cada 2 dias: dias ativos, buscas sem resultado, pedidos travados.

## 6. Hipóteses de planos (sem preços definidos)

| | Starter | Pro | Rede |
|---|---|---|---|
| Para quem | Começando, poucos pedidos | Loja que vende todo dia | Várias unidades ou franquia |
| Canais | Telegram | Telegram (+ WhatsApp na fase 2) | Telegram + WhatsApp |
| Catálogo, orçamento/pedido, painel | ✅ | ✅ | ✅ |
| Automações (carrinho, pós-venda, SLA) | parcial | ✅ | ✅ |
| Resumo diário e Secretário do dono | — | ✅ | ✅ |
| Várias lojas e visão consolidada | — | — | ✅ |
| Suporte | [ ] | [ ] | [ ] |
| Preço mensal | [definir] | [definir] | [definir] |
| Taxa por resultado (opcional) | [definir] | [definir] | [definir] |
| Condição de piloto fundador | — | [definir] | — |

Perguntas para validar com os pilotos: quanto pagaria por mês? Prefere fixo ou por pedido? O que faria cancelar?

## 7. Checklist para escalar

- [ ] **Servidor sempre ligado:** bot em nuvem (Cloudflare Workers ou VPS pequena) com webhook do Telegram, banco Postgres e backup diário. Fim da dependência do computador de teste e do túnel temporário.
- [ ] **WhatsApp oficial:** conta Meta Business verificada, WhatsApp Cloud API, modelos de mensagem aprovados.
- [ ] **IA com créditos:** Grok com tool calling para texto livre, mantendo preço e prazo vindos do catálogo e as regras como plano B. Limite de custo por loja.
- [ ] **Contrato e LGPD:** contrato de prestação de serviço, termo de uso definitivo, política de privacidade revisada, papéis controlador/operador, prazo de retenção, canal do titular.
- [ ] **Pagamentos (se fizer sentido):** integração oficial com um provedor de Pix/cartão, sempre com confirmação automática do provedor, nunca "confirmado" pelo bot.
- [ ] **Operação:** monitoramento (alerta se o bot parar), página de status, rotina de suporte, cobrança.
- [ ] **Comercial:** case publicado com autorização, página de vendas, 3 a 5 lojistas na fila.
