"""Atende AI — versão Pro (plug and play) da loja virtual.

- Assistente de 1 link (?start=pro-lojavirtual): 4 passos com botões, loja pronta em menos de 3 minutos.
- Flag de plano no negócio (t["plano"] = "pro"), recursos listados em /plano.
- Resumo diário às 19h (America/Sao_Paulo) no Telegram do dono, pelo vigia do bot.
Tudo funciona sem IA paga.
"""
from __future__ import annotations

import html
import json
import os
import re
from datetime import datetime, timedelta

import motor as M

E = html.escape
DEEP_LINK = "pro-lojavirtual"
HORA_RESUMO = 19
RECURSOS_PRO = [
    "Assistente de cadastro em 1 link (4 passos, menos de 3 minutos)",
    "Catálogo com busca tolerante a erros, carrinho e frete por CEP",
    "Pedido com as suas instruções de Pix/cartão e botão “Já paguei” (o bot não cobra nada)",
    "Carrinho abandonado: lembrete automático ao cliente",
    "Pós-venda com avaliação de 1 a 5",
    "Alerta de SLA de envio e de resposta",
    "Resumo diário às 19h aqui no Telegram",
    "Secretário do dono: agenda, lembretes e contas numa mensagem só",
    "Painel web ao vivo (/conectar) com exportação CSV",
    "Modelos de mensagem prontos (/modelos)",
    "Suporte direto do Guilherme durante o piloto",
]
RECURSOS_BASICO = RECURSOS_PRO[1:3] + [RECURSOS_PRO[5], RECURSOS_PRO[8]]
FRETES = {
    "A": ("🎁 Grátis acima de R$ 199 · fixo R$ 19,90 abaixo", {"tipo": "fixo", "fixo": 19.9, "gratisAcima": 199}),
    "B": ("🚚 Fixo R$ 19,90 para todo o Brasil", {"tipo": "fixo", "fixo": 19.9, "gratisAcima": None}),
    "C": ("🗺️ Por região (SP R$ 14,90 · Sudeste R$ 21,90 · demais R$ 32,90) · grátis acima de R$ 299",
          {"tipo": "regiao", "gratisAcima": 299, "regioes": {"SP": 14.9, "Sudeste": 21.9, "Outros": 32.9}, "prazosDias": {"SP": 2, "Sudeste": 4, "Outros": 8}}),
}
PAGAMENTOS = {
    "1": ("💸 Pix 5% off · cartão em até 3x", {"pixDescontoPct": 5, "parcelas": 3}),
    "2": ("💸 Pix 10% off · cartão em até 6x", {"pixDescontoPct": 10, "parcelas": 6}),
    "3": ("💠 Só Pix (sem desconto)", {"pixDescontoPct": 0, "parcelas": 0}),
}
MODELOS = [
    ("Bio do Instagram", "🛒 Compre pelo nosso atendimento automático, 24h: {link}"),
    ("Status / stories", "Agora dá pra ver produtos, calcular o frete e fechar o pedido sozinho, a qualquer hora, sem esperar resposta: {link} ⚡"),
    ("Resposta automática do WhatsApp/Instagram", "Oi! 👋 Para ver produtos, preço, frete e fazer seu pedido na hora, use nosso atendimento: {link}. Se preferir falar comigo, é só escrever aqui."),
    ("Lembrar Pix pendente (com carinho)", "Oi, {cliente}! Seu pedido {pedido} está reservado. Se ainda quiser, a chave Pix é {pix}. Qualquer dúvida, é só responder 🙂"),
    ("Aviso de atraso no envio", "Oi, {cliente}! Seu pedido {pedido} vai atrasar um pouquinho: sai até {prazo}. Desculpe o transtorno, já estamos cuidando."),
    ("Troca aprovada", "Oi, {cliente}! Sua troca do pedido {pedido} foi aprovada. Te mandamos as instruções de envio por aqui."),
]


MISSAO = ("🧭 <b>Missão, visão e valores do Atende AI</b> <i>(versão 1, em construção com o Guilherme)</i>\n\n"
          "<b>Missão:</b> dar ao pequeno lojista o atendimento e os dados de uma grande empresa, de um jeito simples e acessível.\n\n"
          "<b>Visão:</b> ser o jeito mais fácil de um pequeno negócio brasileiro atender bem, vender mais e decidir com dados, em qualquer canal de mensagem.\n\n"
          "<b>Valores:</b>\n"
          "🔒 <b>Transparência com dados (LGPD):</b> você e seus clientes sabem o que fica guardado e podem pedir para apagar (/excluir_dados).\n"
          "🙋 <b>Humano no controle:</b> o bot nunca cobra, nunca confirma pagamento e nunca marca conta como paga sem o seu ok.\n"
          "🔌 <b>Simplicidade plug and play:</b> um link, quatro passos, funcionando.\n"
          "📏 <b>Resultado medido:</b> comparamos o antes e o depois com números reais.\n"
          "🤝 <b>Parceria:</b> crescemos junto com quem usa; o seu feedback decide as próximas melhorias.")


def dia_iso(ms):
    return datetime.fromtimestamp(ms / 1000, M.TZ).strftime("%Y-%m-%d")


def _num(s):
    s = re.sub(r"[^\d,.]", "", s or "")
    if not s:
        return None
    if "," in s and "." in s:
        s = s.replace(".", "").replace(",", ".")
    elif "," in s:
        s = s.replace(",", ".")
    try:
        return float(s)
    except ValueError:
        return None


def linhas_produtos(texto):
    """Lê uma lista colada: 'Nome; preço; estoque; dias', CSV 'nome,preco,estoque,envio' ou texto livre. Devolve (produtos, ignoradas)."""
    prods, ign = [], []
    for raw in texto.splitlines():
        lin = raw.strip().strip("-•*·").strip()
        if not lin or re.match(r"^(nome|produto)\s*[,;|\t]", lin, re.I):
            continue
        partes = None
        if re.search(r"[;|\t]", lin):
            partes = [p.strip() for p in re.split(r"\s*[;|\t]\s*", lin)]
        elif ", " in lin:
            partes = [p.strip() for p in re.split(r",\s+", lin)]
        elif lin.count(",") >= 1 and re.match(r"^[^,]+,(?:r\$)?\s*\d", lin, re.I):
            partes = [p.strip() for p in lin.split(",")]
            if len(partes) >= 3 and re.fullmatch(r"\d{2}", partes[2] or "") and len(partes) in (3, 5):  # "89,90" partido
                partes = [partes[0], partes[1] + "," + partes[2]] + partes[3:]
        if partes and len(partes) >= 2 and _num(partes[1]):
            p = {"nome": partes[0][:60], "preco": round(_num(partes[1]), 2), "estoque": None, "envioDias": None,
                 "palavras": [w for w in M.norm(partes[0]).split() if len(w) > 2][:6]}
            if len(partes) >= 3 and re.fullmatch(r"\d{1,5}", re.sub(r"\D", "", partes[2]) or "x"):
                p["estoque"] = int(re.sub(r"\D", "", partes[2]))
            if len(partes) >= 4 and re.sub(r"\D", "", partes[3]):
                p["envioDias"] = int(re.sub(r"\D", "", partes[3]))
            if p["nome"] and p["preco"] >= 1:
                prods.append(p); continue
        r = M.parse_ecom(lin)["produtos"]
        if r:
            prods += r
        else:
            ign.append(lin[:60])
    return prods, ign


class ProMixin:
    # ------------------------------------------------------------ assistente de 1 link
    def pro_iniciar(self, cid, u):
        u["pro"] = {"etapa": "nome", "inicio": M.agora_ms()}
        u["modo"] = "dono" if u.get("dono_de") else u.get("modo", "cliente")
        return self.tg.send(cid, "⭐ <b>Atende AI Pro · Loja virtual</b>\nVamos deixar sua loja pronta para vender em menos de 3 minutos, em 4 passos:\n"
                                 "1️⃣ nome da loja · 2️⃣ termo do piloto · 3️⃣ frete e pagamento · 4️⃣ produtos\n\n"
                                 "<b>Passo 1/4 · Nome</b>\nComo a sua loja se chama?")

    def pro_ativo(self, u):
        w = u.get("pro") or {}
        if w.get("etapa") not in ("nome", "pix", "produtos"):
            return False
        if M.agora_ms() - w.get("inicio", 0) > 6 * 3600000:  # assistente esquecido: não sequestra mensagens para sempre
            u.pop("pro", None)
            return False
        return True

    def pro_texto(self, cid, u, txt):
        w = u["pro"]; et = w["etapa"]
        if et == "nome":
            nome = txt.strip()[:60]
            if len(nome) < 2:
                return self.tg.send(cid, "Qual é o nome da loja? (ex.: Loja do Mano)")
            w["nome"] = nome; w["etapa"] = "termo"
            self.tg.send(cid, f"Ótimo: <b>{E(nome)}</b> 🛒\n\n<b>Passo 2/4 · Termo do piloto</b>")
            return self.exigir_termo(cid, u, {"tipo": "criar", "nome": nome, "seg": "ecommerce", "modo": "vazio", "pro": True})
        t = self.db.tenant(w.get("tenant") or "")
        if not t:
            u.pop("pro", None)
            return self.tg.send(cid, "Não achei a loja do assistente. Recomece pelo link: " + self.link(DEEP_LINK))
        if et == "pix":
            chave = re.sub(r"^(?:chave\s*(?:pix)?\s*:?\s*)", "", txt.strip(), flags=re.I)[:80]
            self.ecom_pol(t)["pagamento"]["pixChave"] = chave
            w["etapa"] = "produtos"
            self.tg.send(cid, f"🔑 Chave Pix anotada: <code>{E(chave)}</code> (o cliente vê isso no fim do pedido).")
            return self.pro_passo4(cid)
        if et == "produtos":
            prods, ign = linhas_produtos(txt)
            if not prods:
                return self.tg.send(cid, "Não reconheci produtos nessa mensagem. Uma linha por produto, por exemplo:\n<code>Fone bluetooth; 89,90; 12; 3</code>\n<code>Garrafa térmica R$ 59 estoque 20 entrega 2 dias</code>",
                                    [[("🧪 Usar 5 produtos de exemplo", "pro:prod:ex")]])
            ls = [self.pro_upsert(t, p) for p in prods]
            w["produtos"] = w.get("produtos", 0) + len(prods)
            msg = f"📦 <b>{len(prods)} produto(s) importado(s):</b>\n" + "\n".join(ls[:15]) + (f"\n… e mais {len(ls) - 15}" if len(ls) > 15 else "")
            if ign:
                msg += "\n\n⚠️ Não entendi: " + "; ".join(f"“{E(x)}”" for x in ign[:5])
            return self.tg.send(cid, msg + "\n\nQuer colar mais alguma lista ou concluir?", [[("✅ Concluir: deixar a loja no ar", "pro:fim")], [("➕ Colar mais produtos", "pro:mais")]])

    def pro_upsert(self, t, p):
        ex = next((c for c in t["catalogo"] if M.norm(c["nome"]) == M.norm(p["nome"])), None)
        alvo = ex or {"id": re.sub(r"[^a-z0-9]+", "-", M.norm(p["nome"])).strip("-")[:20] + "-" + os.urandom(2).hex(), "nome": p["nome"],
                      "categoria": "Importado no assistente", "estoque": 10, "envioDias": self.ecom_pol(t).get("envioDiasUteis", 1), "palavras": []}
        alvo["preco"] = p["preco"]; alvo["pecasMin"] = alvo["pecasMax"] = p["preco"]; alvo["maoMin"] = alvo["maoMax"] = 0; alvo["duracao"] = 0
        if p.get("estoque") is not None:
            alvo["estoque"] = p["estoque"]
        if p.get("envioDias") is not None:
            alvo["envioDias"] = p["envioDias"]
        alvo["palavras"] = sorted(set(alvo.get("palavras", []) + list(p.get("palavras") or [])))
        if not ex:
            t["catalogo"].append(alvo)
        return f"• {E(alvo['nome'])} · {M.brl_c(alvo['preco'])} · estoque {alvo['estoque']} · envio {alvo['envioDias']}d"

    def pro_ativar(self, cid, u, t):
        """Chamado depois do aceite do termo: liga o plano Pro e as automações, vira dono e segue para o passo 3."""
        self.pro_ligar(t)
        if cid not in t["donos"]:
            t["donos"].append(cid)
        if t["id"] not in u.setdefault("dono_de", []):
            u["dono_de"].append(t["id"])
        u["tenant_dono"] = t["id"]; u["modo"] = "dono"
        self.comandos_dono(cid)
        w = u.setdefault("pro", {"inicio": M.agora_ms()}); w["tenant"] = t["id"]; w["etapa"] = "frete"
        return self.tg.send(cid, "<b>Passo 3/4 · Frete</b>\nEscolha um modelo (dá para mudar depois em /politicas):",
                            [[(r, f"pro:frete:{k}")] for k, (r, _) in FRETES.items()])

    def pro_ligar(self, t):
        t["plano"] = "pro"; t.setdefault("planoDesde", M.agora_ms())
        t["recursos"] = {"carrinho_abandonado": True, "posvenda": True, "alerta_sla": True, "resumo_diario": f"{HORA_RESUMO}:00", "secretario": True}
        for a in t.get("automacoes", []):
            a["ativo"] = True
        t["modelos"] = [{"titulo": a, "texto": b} for a, b in MODELOS]

    def pro_passo4(self, cid):
        return self.tg.send(cid, "<b>Passo 4/4 · Produtos</b>\nCole a sua lista, <b>uma linha por produto</b>, do jeito que tiver:\n"
                                 "<code>Fone bluetooth; 89,90; 12; 3</code>  (nome; preço; estoque; dias para envio)\n"
                                 "<code>Garrafa térmica R$ 59 estoque 20 entrega 2 dias</code>\n"
                                 "<code>Cabo USB-C,29.90,50,1</code>  (CSV da planilha)\n\n"
                                 "Pode colar várias linhas numa mensagem só.", [[("🧪 Usar 5 produtos de exemplo", "pro:prod:ex")]])

    def pro_callback(self, cid, u, dado):
        w = u.get("pro") or {}
        t = self.db.tenant(w.get("tenant") or "")
        partes = dado.split(":")
        if dado == "pro:inicio":
            return self.pro_iniciar(cid, u)
        if not t or t["id"] not in u.get("dono_de", []):
            return self.tg.send(cid, "Esse assistente expirou. Recomece pelo link: " + self.link(DEEP_LINK))
        pol = self.ecom_pol(t)
        if partes[1] == "frete" and partes[2] in FRETES:
            pol["frete"].update(json.loads(json.dumps(FRETES[partes[2]][1])))
            w["frete"] = FRETES[partes[2]][0]; w["etapa"] = "pagamento"
            return self.tg.send(cid, f"✅ Frete: {E(FRETES[partes[2]][0])}\n\n<b>Passo 3/4 · Pagamento</b>\nComo você recebe?",
                                [[(r, f"pro:pag:{k}")] for k, (r, _) in PAGAMENTOS.items()])
        if partes[1] == "pag" and partes[2] in PAGAMENTOS:
            pol["pagamento"].update(PAGAMENTOS[partes[2]][1])
            w["pagamento"] = PAGAMENTOS[partes[2]][0]; w["etapa"] = "pix"
            return self.tg.send(cid, f"✅ Pagamento: {E(PAGAMENTOS[partes[2]][0])}\n\nAgora mande a sua <b>chave Pix</b> (e-mail, telefone, CPF/CNPJ ou aleatória). "
                                     "O bot só mostra essa chave ao cliente no fim do pedido; quem confirma o pagamento é você.",
                                [[("⏭️ Pular (eu mando os dados na conversa)", "pro:pix:pular")]])
        if partes[1] == "pix":
            w["etapa"] = "produtos"
            return self.pro_passo4(cid)
        if partes[1] == "prod" and partes[2] == "ex":
            for c in M.DADOS["segmentos"]["ecommerce"]["catalogo"][:5]:
                if not any(x["id"] == c["id"] for x in t["catalogo"]):
                    x = json.loads(json.dumps(c)); x["exemplo"] = True; t["catalogo"].append(x)
            w["produtos"] = w.get("produtos", 0) + 5; w["etapa"] = "produtos"
            return self.tg.send(cid, "🧪 Coloquei 5 produtos de exemplo (marcados como exemplo; troque pelos seus quando quiser).",
                                [[("✅ Concluir: deixar a loja no ar", "pro:fim")], [("➕ Colar meus produtos", "pro:mais")]])
        if partes[1] == "mais":
            w["etapa"] = "produtos"
            return self.tg.send(cid, "Pode colar a próxima lista (uma linha por produto).")
        if partes[1] == "fim":
            return self.pro_concluir(cid, u, t)

    def pro_concluir(self, cid, u, t):
        w = u.pop("pro", {}) or {}
        seg = max(1, round((M.agora_ms() - w.get("inicio", M.agora_ms())) / 1000))
        dur = f"{seg // 60} min {seg % 60:02d} s" if seg >= 60 else f"{seg} s"
        t["proConcluidoEm"] = M.agora_ms(); t["proDuracaoSeg"] = seg
        pol = self.ecom_pol(t)
        self.tg.send(cid, f"🎉 <b>Pronto! A {E(t['nome'])} está no ar</b> (em {dur}).\n\n"
                          f"✅ Termo do piloto aceito\n✅ Frete: {E(w.get('frete') or 'padrão')}\n✅ Pagamento: {E(w.get('pagamento') or 'padrão')}"
                          f"{' · chave Pix cadastrada' if pol['pagamento'].get('pixChave') else ' · sem chave Pix (você manda os dados na conversa)'}\n"
                          f"✅ {len(t['catalogo'])} produto(s) no catálogo\n"
                          f"⚙️ <b>Automações ligadas:</b> carrinho abandonado, pós-venda com avaliação, alerta de SLA e resumo diário às {HORA_RESUMO}h\n"
                          f"⭐ Plano: <b>Pro</b> (veja /plano)\n\n"
                          f"🔗 <b>Link da sua loja</b> para os clientes:\n{self.link(t['id'])}\n\n"
                          f"<b>Agora:</b>\n1. Teste como cliente: /cliente (volte com /dono)\n2. Copie os textos prontos para Instagram e WhatsApp: /modelos\n"
                          f"3. Cada pedido chega aqui com botões: confirmar pagamento → separar → enviar com rastreio\n"
                          f"4. Painel no computador: /conectar · Secretário: escreva “lembrar de postar no Instagram amanhã 10h”")
        return self.tg.send(cid, self.boas_vindas(t))

    def boas_vindas(self, t=None):
        dono = t is not None
        passos = (f"1. Teste como cliente: /cliente (volte com /dono)\n2. Divulgue o link da loja: /link (textos prontos em /modelos)\n"
                  f"3. Conte como era antes, com os seus números, para compararmos depois: <code>/antes resposta 2h vendas R$ 8.000 pedidos 40</code>") if dono else (
                  "1. Crie a sua loja virtual em 3 minutos: " + self.link(DEEP_LINK) + "\n2. Oficina ou loja física: " + self.link("dono") + "\n3. Leia o manual com calma (dá para salvar em PDF)")
        return ("🤝 <b>Seja bem-vindo ao Atende AI!</b>\n"
                "O Atende AI é a IA do Guilherme (byGui): um atendente automático que atende seus clientes no Telegram, monta orçamento ou pedido com os seus preços, "
                "acompanha cada etapa e te mostra os números do negócio. Você continua no controle de tudo.\n\n"
                "<b>O que você ganha</b> (objetivos que vamos medir juntos, sem promessa de número): resposta 24h · pedido automático com frete e Pix · "
                "menos carrinho abandonado · aviso antes de atrasar · pós-venda com avaliação · Secretário do dono · resumo diário às 19h.\n\n"
                "🌱 <b>Piloto fundador:</b> você está entre os primeiros a usar. Em 2 a 4 semanas medimos tempo de resposta, pedidos, conversão e satisfação, "
                "com check-in semanal. Seu nome, números e depoimento só aparecem num case com a sua autorização.\n\n"
                f"<b>Primeiros 3 passos</b>\n{passos}\n\n"
                f"📘 Manual do lojista: {self.PAGES}#/manual\n🧭 Missão e valores: /missao")

    def cmd_manual(self, cid, u):
        t = None
        if u.get("dono_de"):
            t = self.db.tenant(u.get("tenant_dono") or u["dono_de"][0])
        return self.tg.send(cid, self.boas_vindas(t))

    # ------------------------------------------------------------ plano e modelos
    def cmd_plano(self, cid, t):
        pro = t.get("plano") == "pro"
        lst = RECURSOS_PRO if pro else RECURSOS_BASICO
        txt = (f"⭐ <b>Plano {'Pro' if pro else 'Básico'}</b> · {E(t['nome'])}\n" + "\n".join(f"✅ {E(x)}" for x in lst))
        if pro:
            r = t.get("recursos") or {}
            txt += (f"\n\n⚙️ Ligados agora: carrinho abandonado {'✅' if r.get('carrinho_abandonado') else '—'} · pós-venda {'✅' if r.get('posvenda') else '—'} · "
                    f"alerta de SLA {'✅' if r.get('alerta_sla') else '—'} · resumo diário {E(r.get('resumo_diario') or '—')}"
                    f"\nPro desde {M.data_hora(t.get('planoDesde') or M.agora_ms())}. Durante o piloto, sem cobrança.")
        else:
            falta = [x for x in RECURSOS_PRO if x not in lst]
            txt += "\n\nNo Pro também: " + "; ".join(E(x) for x in falta[:6]) + ". Peça ao administrador da plataforma."
        return self.tg.send(cid, txt + "\n\nResumo do dia agora: /resumo · Textos prontos: /modelos")

    def cmd_modelos(self, cid, t):
        pol = t.get("politicas") or {}
        chave = (pol.get("pagamento") or {}).get("pixChave") or "(sua chave Pix)"
        ms = t.get("modelos") or [{"titulo": a, "texto": b} for a, b in MODELOS]
        ls = [f"<b>{n}. {E(m['titulo'])}</b>\n<code>{E(m['texto'].replace('{link}', self.link(t['id'])).replace('{pix}', chave))}</code>" for n, m in enumerate(ms, 1)]
        return self.tg.send(cid, "📝 <b>Modelos de mensagem</b> (toque no texto para copiar; {cliente}, {pedido} e {prazo} você troca na hora)\n\n" + "\n\n".join(ls))

    # ------------------------------------------------------------ resumo diário
    def resumo_texto(self, t, agora=None):
        agora = agora or M.agora_ms(); hoje = dia_iso(agora)
        tks = [x for x in self.db.d["tickets"] if x["tenant"] == t["id"]]
        criados = [x for x in tks if dia_iso(x.get("criado", 0)) == hoje]
        ped = [x for x in criados if x.get("tipo", "pedido") == "pedido"]
        pagos = [x for x in tks if x.get("tipo", "pedido") == "pedido" and any(h["status"] in ("Pago", "Aprovado") and dia_iso(h["ts"]) == hoje for h in x.get("historico", []))]
        fat = sum(x.get("totalFinal") or x.get("valorFinal") or 0 for x in pagos)
        if t["segmento"] != "ecommerce":
            fat = sum(x.get("valorFinal") or M.valor_medio(x) for x in pagos)
        aguard = [x for x in tks if x["status"] in ("Aguardando pagamento", "Orçado")]
        enviar = [x for x in tks if x["status"] in ("Pago", "Separando", "Aprovado", "Em serviço")]
        trocas = [x for x in tks if x.get("tipo") in ("troca", "atendimento") and x["status"] not in ("Resolvido",)]
        notas = [x["nps5"] for x in tks if x.get("nps5")]
        atv = (t.get("atividade") or {}).get(hoje, {})
        amanha = (datetime.fromtimestamp(agora / 1000, M.TZ) + timedelta(days=1)).strftime("%Y-%m-%d")
        tf = [x for x in self.db.d.get("tarefas", []) if x["tenant"] == t["id"] and x["status"] in ("executada", "aguardando_ok", "aguardando_dado")]
        agenda = [x for x in tf if x["tipo"] == "agenda.criar" and x["slots"].get("data") == amanha and x["status"] == "executada"]
        contas = [x for x in tf if x["tipo"] == "financeiro.pagar" and x["status"] == "aguardando_ok" and (x["slots"].get("vencimento") or "9") <= amanha]
        ls = [f"📊 <b>Resumo do dia · {E(t['nome'])}</b> ({datetime.fromtimestamp(agora / 1000, M.TZ).strftime('%d/%m')})",
              f"💬 Conversas hoje: <b>{atv.get('conv', 0)}</b> · mensagens de clientes: {atv.get('cli', 0)}",
              f"🛒 Pedidos novos: <b>{len(ped)}</b> · pagos hoje: <b>{len(pagos)}</b> · faturamento hoje: <b>{M.brl_c(fat)}</b>",
              f"⏳ Aguardando pagamento: <b>{len(aguard)}</b>" + (" (" + ", ".join(x["id"] for x in aguard[:5]) + ")" if aguard else ""),
              f"🚚 Para separar/enviar: <b>{len(enviar)}</b>" + (" (" + ", ".join(x["id"] for x in enviar[:5]) + ")" if enviar else ""),
              f"🔁 Trocas e atendimentos abertos: {len(trocas)}"]
        if notas:
            ls.append(f"⭐ Avaliação média: {sum(notas) / len(notas):.1f}/5 ({len(notas)} avaliações)".replace(".", ","))
        if agenda or contas:
            ls.append("🗂️ Amanhã: " + "; ".join([f"{x['slots'].get('assunto', 'compromisso')} com {x['slots'].get('pessoa', '')} às {x['slots']['hora']}" for x in agenda] +
                                                [f"pagar {x['slots'].get('credor')} (#{x['id']}, aguardando seu ok)" for x in contas]))
        ls.append("\nPedidos: /pedidos · Painel: /painel")
        return "\n".join(ls)

    def pro_vigiar(self, agora=None):
        agora = agora or M.agora_ms()
        d = datetime.fromtimestamp(agora / 1000, M.TZ)
        if d.hour < HORA_RESUMO:
            return False
        hoje = d.strftime("%Y-%m-%d"); mudou = False
        for t in self.db.d["tenants"].values():
            if t.get("plano") != "pro" or not (t.get("recursos") or {}).get("resumo_diario") or not t.get("donos") or t.get("resumoEnviadoEm") == hoje:
                continue
            txt = self.resumo_texto(t, agora)
            for cid in t["donos"]:
                self.tg.send(cid, txt)
            t["resumoEnviadoEm"] = hoje; mudou = True
        return mudou
