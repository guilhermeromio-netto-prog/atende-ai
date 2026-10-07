# Playbook do piloto · Atende AI

Guia curto para rodar o primeiro piloto (a loja virtual do irmão do Guilherme) em 2 a 4 semanas e sair com números para um estudo de caso e uma hipótese de preço.

## 1. Objetivo

Provar, com dados de uma loja real, que o Atende AI:

1. responde clientes na hora, inclusive fora do horário;
2. resolve a maior parte das conversas sem o dono;
3. transforma conversa em pedido pago;
4. economiza tempo do dono, e que ele continuaria usando (e pagaria).

## 2. Colocar o irmão no piloto (dia 0, cerca de 1 hora)

| Quem | Passo |
|---|---|
| Irmão | Abre https://t.me/Applojas10_bot?start=dono → **Criar meu negócio do zero** → nome da loja → **🛒 Loja virtual (catálogo vazio)** → lê o termo do piloto → **✅ Aceito** |
| Irmão | Cadastra 10 a 30 produtos (`Fone bluetooth R$ 89 estoque 12 entrega 3 dias`), as políticas (`Frete grátis acima de R$ 199`, `Pix com 5% de desconto, cartão em até 6x`, `Chave pix: …`) e confere com `/catalogo` e `/politicas` |
| Irmão | Testa como cliente com `/cliente` (busca, carrinho, CEP, Pix, “Já paguei”) e volta com `/dono` |
| Guilherme | Vira admin (`/admin SEU_CÓDIGO`), acha o slug da loja em `/lojas` e marca: `/piloto <slug>` |
| Irmão | Recebe o convite e preenche o **antes**: `/antes resposta 2h vendas R$ 8.000 pedidos 40` |
| Irmão | Publica o link (`/link`) na bio do Instagram, nos destaques e na resposta automática do WhatsApp/Instagram |
| Os dois | Combinam a rotina: o irmão confirma pagamentos e informa rastreio pelos botões; responde quando o bot chamar um atendente |

**Como estimar o “antes” sem chute:** pegue as últimas 20 conversas no WhatsApp/Instagram e anote quanto tempo levou a 1ª resposta (use a mediana); vendas e pedidos por mês = média dos últimos 3 meses (extrato da plataforma de pagamento ou planilha).

## 3. O que medir (toda segunda-feira, 15 minutos)

Abra o [Modo plataforma](https://guilhermeromio-netto-prog.github.io/atende-ai/#/admin) com `/admin_conectar`, clique na loja e exporte o CSV. Anote numa planilha, semana a semana:

| Indicador | Onde ver | Por que importa |
|---|---|---|
| Conversas | `/loja`, Modo plataforma | Demanda que chegou pelo bot |
| Pedidos e pedidos pagos | `/painel` do dono, Modo plataforma | Resultado de verdade |
| Conversão carrinho → pago | `/painel` | Qualidade do fluxo de compra |
| Faturamento intermediado | `/plataforma`, `/loja` | Base para preço por resultado |
| 1ª resposta do bot e resposta da equipe quando chamada | `/loja`, Dashboard | Comparação com o “antes” |
| % resolvido sem atendente | Dashboard (atendimentos sem atendente) | Tempo economizado |
| Carrinhos abandonados e lembretes | `/painel` | Venda recuperada |
| Avaliação (1 a 5) e NPS | `/loja`, Dashboard | Satisfação do cliente final |
| Dias ativos e mensagens por dia | Saúde do piloto | Uso real (se cair, algo travou) |
| Buscas sem resultado, falhas, reclamações | Conversa com o irmão | Lista de melhorias |

Também vale anotar frases do irmão e dos clientes (“vendi de madrugada”, “não preciso mais responder preço”). Elas viram a citação do case.

**Horas economizadas (estimativa):** conversas resolvidas sem atendente × minutos que o irmão gastava por conversa antes (pergunte; 3 a 5 min é comum).

## 4. Critérios de sucesso (hipóteses para o fim da semana 4)

| Critério | Meta |
|---|---|
| Resposta | 1ª resposta em menos de 1 minuto, 24 horas por dia |
| Autonomia | 60% ou mais das conversas sem chamar atendente |
| Vendas pelo bot | 10 ou mais pedidos pagos, ou 15% ou mais das vendas da loja |
| Conversão | 25% ou mais dos carrinhos viram pedido pago |
| Satisfação | Avaliação média 4,5 ou mais (ou NPS 50 ou mais) |
| Uso | Loja ativa em 80% ou mais dos dias |
| Retenção | O irmão diz que ficaria “muito decepcionado” se o bot sumisse e topa continuar pagando um valor simbólico |
| Estabilidade | No máximo 2 quedas do servidor de teste por semana |

**Se bater 5 de 8:** vira case e parte para mais lojas. **Se não:** listar os 3 maiores motivos (busca, frete, pagamento, disponibilidade) e rodar mais 2 semanas antes de escalar.

## 5. Transformar em estudo de caso

1. **Autorização por escrito** do irmão para publicar nome da loja, números e citação. Nada de dados de clientes finais.
2. Estrutura de uma página:
   - **Contexto:** que loja é, quanto vende, como atendia;
   - **Problema:** demora para responder e vendas perdidas fora do horário;
   - **Solução:** o que foi configurado em 1 hora;
   - **Números antes × depois:** tabela do Modo plataforma, mais a estimativa de horas economizadas;
   - **Citação;**
   - **Próximos passos.**
3. Usar no Instagram/LinkedIn do byGui, na página inicial do Atende AI e como roteiro nas conversas com as próximas lojas.

## 6. Hipótese de preço para escalar

Validar com 5 a 10 lojas parecidas antes de fixar. Perguntas: “a partir de que preço fica caro demais?” e “que preço parece barato demais para ser bom?”.

| Plano | Para quem | Hipótese |
|---|---|---|
| Teste | Primeiros 30 dias | Grátis, com acompanhamento |
| Essencial | 1 loja, Telegram, regras sem IA, até ~500 conversas/mês | R$ 59 a R$ 99 por mês |
| Pro | WhatsApp, IA (Grok), link de pagamento real, painel, até 3 atendentes | R$ 149 a R$ 249 por mês |
| Por resultado (alternativa) | Lojas que preferem pagar só quando vendem | 1% a 2% do faturamento intermediado, com mínimo mensal |

**Conferir antes de fechar o preço:**

- **Custo por loja:** servidor sempre ligado, custo por conversa do WhatsApp na tabela vigente da Meta, tokens de IA por conversa e meio de pagamento.
- **Margem:** mire 70% ou mais.
- **Âncora de valor:** horas economizadas × valor da hora do dono, mais vendas fora do horário. Use os números do case.

## 7. Antes de cobrar de verdade

- **Fase 2 no ar:** servidor sempre ligado com webhook, banco de dados e backups (ver [arquitetura.md](arquitetura.md)).
- **Pagamento real:** link de pagamento com confirmação automática por webhook (Mercado Pago/Stripe) e cotação de frete.
- **Contrato:** termo de uso, política de privacidade e contrato de operador de dados (LGPD) revisados por advogado ([privacidade.md](privacidade.md) é só o resumo do piloto).
- **Suporte:** canal e prazo de resposta definidos.
