# Secretário IA — Memorial estruturado

Versão 1.1 · 7 de outubro de 2026  
Fonte: vídeo `1000354350.mp4` (12,04 s)  
Especificação enriquecida: `secretario-ia-spec.json`

Este memorial descreve o produto demonstrado e separa o que a tela mostra do que a especificação propõe. O JSON é a fonte de detalhe; este texto é a leitura operacional.

## 1. Identificação

| Campo | Valor |
| --- | --- |
| Nome | Secretário IA |
| Categoria | Assistente pessoal de execução no WhatsApp |
| Promessa | Uma mensagem vira tarefas feitas, com confirmação explícita |
| Canal | WhatsApp |
| Fuso padrão | America/Sao_Paulo |
| Status | Conceito demonstrado; especificação pronta para MVP |

O produto não se apresenta como chatbot de perguntas. O usuário delega. O sistema extrai, completa o que falta, executa e devolve prova.

## 2. O que o vídeo mostra

1. **0–2 s.** Abertura de marca em fundo coral, símbolo S navy com corte ciano e wordmark “Secretário IA”.
2. **2–4 s.** Conversa no padrão WhatsApp. Saudação: “Olá! Sou seu Secretário IA personalizado. Como posso automatizar sua vida hoje?”
3. **4–6 s.** Três tarefas extraídas de uma fala: agendar reunião com João, pagar conta de luz, lembrar de comprar leite. Ícone de agenda e checks verdes.
4. **6–8 s.** Cartão de conclusão: “Tarefa concluída: Reunião agendada com sucesso!”
5. **8–10 s.** Uso em home office: telefone, notebook e gesto de aprovação.
6. **10–12 s.** Prova no aparelho, com as três tarefas marcadas.

Defeitos de quadro, a corrigir na próxima peça: transcrição ilegível, bolhas sobrepostas, horários inválidos (`11:240`, `11:2 0`) e status “Múdio” no cabeçalho.

## 3. Identidade

| Token | Valor | Uso |
| --- | --- | --- |
| Coral | `#F04B3A` | Fundo de marca |
| Navy | `#1B2340` | Símbolo e texto |
| Ciano | `#2EE6E6` | Corte do S e acento |
| Sucesso | `#22C55E` | Check de tarefa concluída |
| Papel | `#F7F4EE` | Superfície do chat |

O símbolo é um S geométrico. O corte ciano no vão central é o único acento. Não usar gradiente arco-íris no cartão de sucesso da peça final: no vídeo ele aparece, mas compete com a marca.

## 4. Problema e resposta

O usuário fala várias coisas na mesma mensagem. Um chat comum devolve texto. O Secretário IA devolve trabalho: evento, lembrete ou obrigação registrada.

Resposta de produto, em uma frase: separar intenções, perguntar só o dado que impede a ação e confirmar cada item com prova.

## 5. Intenções do demonstrativo

### 5.1 Agendar reunião com João

- Tipo: `agenda.criar`
- Evidência: observada, com cartão de sucesso.
- Slots mínimos: pessoa, data, hora.
- Lacuna: o vídeo confirma a reunião sem mostrar dia nem hora. A especificação não grava evento sem esses dois slots.
- Confirmação: “Tarefa concluída: reunião com João agendada.” Incluir data, hora e identificador do evento.

### 5.2 Pagar conta de luz

- Tipo: `financeiro.pagar`
- Evidência: observada como item da lista.
- Slots mínimos: credor e vencimento.
- Guarda: o check visual não autoriza débito. Status especificado: `aguardando_ok`.
- Confirmação: “Conta de luz registrada. O pagamento espera a sua confirmação.”

### 5.3 Lembrar de comprar leite

- Tipo: `lembrete.criar`
- Evidência: observada.
- Slot mínimo: item.
- Padrão se não houver hora: hoje às 18:00, declarado na resposta.
- Confirmação: “Lembrete criado: comprar leite hoje às 18h.”

## 6. Jornada canônica

1. O usuário envia áudio.
2. O Secretário transcreve e devolve a lista antes de executar.
3. Pergunta apenas o que falta: horário da reunião e vencimento da conta.
4. O usuário responde em uma frase.
5. O sistema grava a reunião, cria o lembrete e deixa o pagamento parado.
6. Cada item recebe o próprio cartão de conclusão.

Copy de lista proposta:

> Encontrei 3 pedidos:  
> 1. Reunião com João — falta dia e hora.  
> 2. Conta de luz — falta vencimento.  
> 3. Comprar leite — posso lembrar hoje às 18h.

## 7. Regras de execução

- Uma mensagem pode gerar várias tarefas; cada uma tem status próprio.
- Não inventar horário, valor ou pessoa.
- Confiança baixa na transcrição pede repetição em texto.
- Pagamento nunca segue sem ok explícito.
- Toda conclusão cita prova: evento, lembrete ou protocolo.
- Fuso America/Sao_Paulo até mudança do usuário.

## 8. Dados

Entidades: contato, mensagem, intenção, prova.

Status de intenção: `rascunho`, `aguardando_dado`, `aguardando_ok`, `executada`, `falhou`, `cancelada`.

O exemplo do vídeo fica assim na spec:

| Tarefa | Status na tela | Status especificado |
| --- | --- | --- |
| Reunião com João | Concluída | `executada`, após data e hora |
| Conta de luz | Check | `aguardando_ok` |
| Comprar leite | Check | `executada`, com horário padrão declarado |

## 9. Integrações

| Sistema | Papel | Prioridade |
| --- | --- | --- |
| WhatsApp | Entrada, lista e prova | P0 |
| Agenda Google ou Outlook | Criar a reunião | P0 |
| Lembrete no próprio WhatsApp | Comprar leite | P0 |
| Transcrição | Áudio para texto com confiança | P0 |
| Pagamentos | Preparar boleto, sem débito automático | P1 |
| Contatos | Resolver “João” | P1 |

## 10. Aceite e métricas

Aceite do demo:

- Três pedidos geram três cartões.
- Reunião só entra na agenda com pessoa, data e hora.
- Conta de luz não aparece como paga.
- Lembrete sem hora declara 18:00.
- Não há rótulo “Message” nem horário inválido na peça final.

Metas: extração correta ≥ 0,90 nas três intenções; no máximo uma pergunta de complemento; lista em até 8 s; zero débitos sem ok; 100% das conclusões com identificador externo.

## 11. Roadmap

1. **Demo fiel.** Corrigir copy, horários e lista do vídeo.
2. **MVP.** WhatsApp, transcrição, extração, agenda e lembrete.
3. **Controle.** Aprovação de pagamento, contatos e auditoria.
4. **Escala.** Recorrência, múltiplas agendas e handoff humano.

## 12. Leitura do JSON

`secretario-ia-spec.json` guarda marca, atos do vídeo, copy observada e proposta, slots, jornada, modelo, integrações, regras, aceite, métricas e roadmap. Campo `origem` distingue `observado` de `proposto`.
