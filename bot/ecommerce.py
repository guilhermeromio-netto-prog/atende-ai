"""Atende AI — fluxo da Loja virtual (ecommerce) no bot do Telegram.

Mixin usado pela classe Bot (atende_bot.py). Mesmo motor/regras de motor.py e dados.json.
Nunca simula pagamento: só mostra as instruções que o lojista cadastrou e avisa o lojista
quando o cliente diz que pagou; quem confirma é o lojista.
"""
from __future__ import annotations

import html
import os
import re

import motor as M

E = html.escape
ABANDONO_MIN = int(os.environ.get("ATENDE_ABANDONO_MIN", "10"))  # modo teste: lembrete 10 min depois
MOTIVOS = [("Defeito", "mot:defeito"), ("Arrependimento (7 dias)", "mot:arrependimento"), ("Produto errado", "mot:errado"), ("Outro motivo", "mot:outro")]
MOTIVO_TXT = {"defeito": "Defeito", "arrependimento": "Arrependimento (7 dias)", "errado": "Produto errado", "outro": "Outro motivo"}


def kb(*linhas):
    return [list(l) for l in linhas]


class EcomMixin:
    # ------------------------------------------------------------ utilidades
    def ecom_pol(self, t):
        return t.setdefault("politicas", M.politicas_padrao())

    def ecom_menu(self):
        return kb([("🔎 Produtos e preços", "menu:produtos")], [("🚚 Frete e prazo", "menu:frete"), ("🛒 Meu carrinho", "menu:carrinho")],
                  [("📦 Rastrear pedido", "menu:rastreio"), ("🔁 Troca/devolução", "menu:troca")], [("🙋 Falar com atendente", "atendente")])

    def ecom_out(self, cid, conv, texto, teclado=None):
        if conv.get("respSeg") is None and conv.get("ultima"):
            conv["respSeg"] = max(1, round((M.agora_ms() - conv["ultima"]) / 1000))
        alvo = conv.setdefault("chat", [])
        alvo.append({"de": "bot", "texto": re.sub(r"<[^>]+>", "", texto), "ts": M.agora_ms()})
        del alvo[:-80]
        return self.tg.send(cid, texto, teclado)

    def ecom_iniciar(self, cid, u, t):
        u["conv"] = {"tenant": t["id"], "seg": "ecommerce", "etapa": "menu", "dados": {}, "carrinho": {}, "carrinhoEm": None,
                     "lembrado": False, "ticket": None, "chat": [], "volta": None}
        priv = self.abertura(u, t)
        aviso = "\n\n⚠️ <i>Loja de exemplo para teste: os produtos são fictícios e nenhum pagamento deve ser feito.</i>" if t.get("exemplo") else ""
        return self.tg.send(cid, f"Olá! 👋 Aqui é o atendimento automático da <b>{E(t['nome'])}</b> 🛒\n"
                                 f"Pergunte do seu jeito: “tem fone bluetooth?”, “quanto é o frete pro meu CEP?”, “cadê meu pedido?”.\n"
                                 f"Ou toque numa opção:{aviso}\n\n<i>Assistente automático (modo de teste). Escreva “atendente” para falar com uma pessoa.</i>" + priv, self.ecom_menu())

    # ------------------------------------------------------------ entrada do cliente
    def ecom_texto(self, cid, u, t, txt, valor=None):
        conv = u["conv"]
        if conv.get("seg") != "ecommerce":
            self.ecom_iniciar(cid, u, t); conv = u["conv"]
        conv.setdefault("chat", []).append({"de": "cliente", "texto": txt, "ts": M.agora_ms()})
        conv["ultima"] = M.agora_ms()
        n = M.norm(txt)
        cat = t["catalogo"]
        out = lambda texto, teclado=None: self.ecom_out(cid, conv, texto, teclado)  # noqa: E731
        v = valor or ""
        # botões
        if v == "atendente" or (not v and re.search(r"atendente|humano|falar com (alguem|uma pessoa)|pessoa de verdade", n)):
            return self.ecom_humano(cid, u, conv, t, txt, out)
        if v.startswith("menu:"):
            op = v[5:]
            if op == "produtos":
                return self.ecom_listar(conv, t, sorted(cat, key=lambda c: c.get("estoque", 0) <= 0), "🗂️ <b>Nossos produtos</b>", out)
            if op == "frete":
                conv["etapa"] = "cep"; conv["volta"] = "frete"
                return out("📮 Qual é o seu CEP? (ex.: 01310-100)")
            if op == "carrinho":
                return self.ecom_carrinho(conv, t, out)
            if op == "rastreio":
                return self.ecom_pedir_numero(cid, conv, t, out, "rastreio")
            if op == "troca":
                return self.ecom_pedir_numero(cid, conv, t, out, "troca")
        if v.startswith("add:"):
            return self.ecom_add(conv, t, v[4:], 1, out)
        if v.startswith(("inc:", "dec:")):
            pid = v[4:]
            q = conv["carrinho"].get(pid, 0) + (1 if v.startswith("inc:") else -1)
            c = next((x for x in cat if x["id"] == pid), None)
            if c and q > int(c.get("estoque", 0)):
                return out(f"Só temos {c.get('estoque', 0)} unidade(s) de {E(c['nome'])} em estoque.", self.ecom_kb_carrinho(conv))
            if q <= 0:
                conv["carrinho"].pop(pid, None)
            else:
                conv["carrinho"][pid] = q
            conv["carrinhoEm"] = M.agora_ms(); conv["lembrado"] = False
            return self.ecom_carrinho(conv, t, out)
        if v == "limpar":
            conv["carrinho"] = {}
            return out("🗑️ Carrinho esvaziado.", self.ecom_menu())
        if v == "checkout":
            return self.ecom_checkout(cid, u, conv, t, out)
        if v.startswith("pg:"):
            conv["dados"]["pagamento"] = v[3:]
            return self.ecom_checkout(cid, u, conv, t, out)
        if v == "confirmar":
            return self.ecom_confirmar(cid, u, conv, t, out)
        if v.startswith("pago:"):
            return self.ecom_ja_paguei(cid, conv, t, v[5:], out)
        if v.startswith("rt:"):
            return self.ecom_mostrar_pedido(cid, t, v[3:], out)
        if v.startswith("tr:"):
            conv["dados"]["pedidoRef"] = v[3:]; conv["etapa"] = "troca_motivo"
            return out(f"Qual o motivo da troca/devolução do pedido {E(v[3:])}?", kb(*[[m] for m in MOTIVOS]))
        if v == "tr-sem":
            conv["dados"]["pedidoRef"] = ""; conv["etapa"] = "troca_motivo"
            return out("Sem problema. Qual o motivo da troca/devolução?", kb(*[[m] for m in MOTIVOS]))
        if v.startswith("mot:"):
            return self.ecom_abrir_troca(cid, u, conv, t, MOTIVO_TXT.get(v[4:], "Outro motivo"), txt, out)

        etapa = conv.get("etapa")
        cep = M.achar_cep(txt)
        # respostas esperadas por etapa
        if etapa in ("cep", "checkout_cep") and cep:
            info = self.ecom_aplicar_cep(conv, cep)
            if conv.get("volta") == "checkout" or etapa == "checkout_cep":
                out(info.strip())
                return self.ecom_checkout(cid, u, conv, t, out)
            conv["etapa"] = "menu"
            return out(info + self.ecom_texto_frete(conv, t), kb([("🔎 Ver produtos", "menu:produtos"), ("🛒 Meu carrinho", "menu:carrinho")]))
        if etapa == "checkout_nome" and not v and len(txt) >= 2 and not cep:
            nome = re.sub(r"^(meu nome (é|e)|me chamo|sou (o|a))\s+", "", txt, flags=re.I).strip()
            conv["dados"]["cliente"] = " ".join(M.cap(p) for p in nome.split()[:4])[:60]
            return self.ecom_checkout(cid, u, conv, t, out)
        if etapa == "checkout_endereco" and not v and len(txt) >= 5:
            conv["dados"]["endereco"] = txt.strip()[:160]
            return self.ecom_checkout(cid, u, conv, t, out)
        if etapa == "checkout_pagamento" and re.search(r"pix|cart", n):
            conv["dados"]["pagamento"] = "pix" if "pix" in n else "cartao"
            return self.ecom_checkout(cid, u, conv, t, out)
        if etapa == "confirmar" and re.match(r"^(sim|confirmo|confirmar|pode|ok|fechado|isso)", n):
            return self.ecom_confirmar(cid, u, conv, t, out)
        if etapa == "rastreio":
            num = self.ecom_achar_pedido(t, txt)
            if num:
                conv["etapa"] = "menu"
                return self.ecom_mostrar_pedido(cid, t, num, out)
        if etapa == "troca_pedido":
            num = self.ecom_achar_pedido(t, txt)
            if num or re.search(r"nao (tenho|sei|lembro)", n):
                conv["dados"]["pedidoRef"] = num or ""; conv["etapa"] = "troca_motivo"
                return out("Qual o motivo da troca/devolução?", kb(*[[m] for m in MOTIVOS]))
        if etapa == "troca_motivo" and len(txt) >= 3:
            return self.ecom_abrir_troca(cid, u, conv, t, "Outro motivo", txt, out)

        # intenção livre
        it, _ = self._ecom_intencao(n)
        achados = M.buscar_produtos(cat, txt)
        if it == "rastreio":
            num = self.ecom_achar_pedido(t, txt)
            if num:
                return self.ecom_mostrar_pedido(cid, t, num, out)
            return self.ecom_pedir_numero(cid, conv, t, out, "rastreio")
        if it == "troca":
            return self.ecom_pedir_numero(cid, conv, t, out, "troca")
        if it == "frete" and not achados:
            if cep:
                info = self.ecom_aplicar_cep(conv, cep)
                return out(info + self.ecom_texto_frete(conv, t), kb([("🔎 Ver produtos", "menu:produtos"), ("🛒 Meu carrinho", "menu:carrinho")]))
            conv["etapa"] = "cep"; conv["volta"] = "frete"
            return out("📮 Me passa o seu CEP que eu calculo o frete e o prazo. (ex.: 01310-100)")
        if it == "pagamento" and not achados:
            return out("💳 <b>Formas de pagamento</b>\n" + E(next((l for l in M.texto_politicas(self.ecom_pol(t)).split("\n") if l.startswith("💳")), "💳 Pix ou cartão")) +
                       "\nO pagamento é combinado com a loja depois que você confirma o pedido.", self.ecom_menu())
        if achados:
            qtd = M.achar_qtd(txt)
            if it == "comprar" and len(achados) == 1 or (qtd and achados[0][1] >= 3 and (len(achados) == 1 or achados[0][1] > achados[1][1])):
                return self.ecom_add(conv, t, achados[0][0]["id"], qtd or 1, out)
            return self.ecom_listar(conv, t, [c for c, _ in achados[:6]], "🔎 <b>Encontrei:</b>", out)
        if it == "comprar":
            if conv["carrinho"]:
                return self.ecom_carrinho(conv, t, out)
            return self.ecom_listar(conv, t, cat, "🛒 Ótimo! Escolha o produto:", out)
        if cep:
            info = self.ecom_aplicar_cep(conv, cep)
            return out(info + self.ecom_texto_frete(conv, t), self.ecom_menu())
        return out("Não encontrei isso no catálogo. Posso te mostrar os produtos ou ajudar com frete, pedido e troca:", self.ecom_menu())

    def _ecom_intencao(self, n):
        melhor, pts = None, 0
        for it in M.DADOS["segmentos"]["ecommerce"]["intents"]:
            s = sum(len(M.norm(p).split()) + 0.5 for p in it["palavras"] if M.norm(p) in n)
            if s > pts:
                melhor, pts = it["id"], s
        return melhor, pts

    # ------------------------------------------------------------ produtos e carrinho
    def ecom_linha_prod(self, c):
        est = int(c.get("estoque", 0))
        disp = f"✅ {est} em estoque" if est > 0 else "❌ esgotado"
        return f"• <b>{E(c['nome'])}</b> — {M.brl_c(c['preco'])} · {disp} · envio em {c.get('envioDias', 1)} dia(s) útil(eis)"

    def ecom_listar(self, conv, t, lista, titulo, out):
        if not lista:
            return out("O catálogo ainda está vazio. Fale com um atendente:", kb([("🙋 Falar com atendente", "atendente")]))
        conv["etapa"] = "menu"
        texto = titulo + "\n" + "\n".join(self.ecom_linha_prod(c) for c in lista[:10])
        bts = [[(f"🛒 {c['nome'] if len(c['nome']) <= 30 else c['nome'][:29].strip() + '…'} · {M.brl_c(c['preco'])}", f"add:{c['id']}")] for c in lista[:8] if int(c.get("estoque", 0)) > 0]
        if not bts:
            return out(texto + "\n\nEsse item está esgotado no momento. Posso mostrar outros produtos ou chamar um atendente para avisar quando voltar.",
                       kb([("🔎 Ver outros produtos", "menu:produtos")], [("🙋 Falar com atendente", "atendente")]))
        if conv["carrinho"]:
            bts.append([("🛒 Ver carrinho", "menu:carrinho"), ("✅ Fechar pedido", "checkout")])
        return out(texto + "\n\nToque para adicionar ao carrinho:", bts)

    def ecom_add(self, conv, t, pid, qtd, out):
        c = next((x for x in t["catalogo"] if x["id"] == pid), None)
        if not c:
            return out("Esse produto não está mais no catálogo.", self.ecom_menu())
        est = int(c.get("estoque", 0))
        if est <= 0:
            return out(f"😕 {E(c['nome'])} está esgotado no momento.", kb([("🔎 Ver outros produtos", "menu:produtos")], [("🙋 Avise-me / atendente", "atendente")]))
        if not conv["carrinho"]:
            t.setdefault("metricas", {}).setdefault("carrinhos", 0)
            t["metricas"]["carrinhos"] += 1
        nova = min(est, conv["carrinho"].get(pid, 0) + qtd)
        conv["carrinho"][pid] = nova
        conv["carrinhoEm"] = M.agora_ms(); conv["lembrado"] = False; conv["ultimo"] = pid
        aviso = f" (limitei a {est}, o que temos em estoque)" if nova < qtd else ""
        return self.ecom_carrinho(conv, t, out, f"✅ Adicionei {nova if aviso else qtd}x {E(c['nome'])}{aviso}.\n\n")

    def ecom_kb_carrinho(self, conv):
        u = conv.get("ultimo")
        linhas = []
        if u and u in conv["carrinho"]:
            linhas.append([("➕ 1", f"inc:{u}"), ("➖ 1", f"dec:{u}")])
        linhas += [[("🔎 Continuar comprando", "menu:produtos")], [("✅ Fechar pedido", "checkout")], [("🗑️ Esvaziar", "limpar")]]
        return linhas

    def ecom_texto_carrinho(self, conv, t, r):
        ls = [f"{i['qtd']}x {E(i['nome'])} — {M.brl_c(i['preco'] * i['qtd'])}" for i in r["itens"]]
        ls.append(f"<b>Subtotal: {M.brl_c(r['subtotal'])}</b>")
        f = self.ecom_pol(t).get("frete", {})
        if r["frete"]:
            ls.append(f"🚚 Frete ({E(conv['dados'].get('regiao', ''))}): " + ("grátis 🎉" if r["frete"]["gratis"] else M.brl_c(r["frete"]["valor"])))
        elif f.get("gratisAcima") not in (None, ""):
            falta = float(f["gratisAcima"]) - r["subtotal"]
            ls.append("🎁 Você já tem frete grátis!" if falta <= 0 else f"🎁 Faltam {M.brl_c(falta)} para frete grátis")
        return "\n".join(ls)

    def ecom_carrinho(self, conv, t, out, prefixo=""):
        if not conv["carrinho"]:
            return out(prefixo + "🛒 Seu carrinho está vazio.", kb([("🔎 Ver produtos", "menu:produtos")]))
        r = M.resumo_carrinho(t["catalogo"], conv["carrinho"], self.ecom_pol(t), conv["dados"].get("regiao"), None)
        conv["etapa"] = "menu"
        return out(prefixo + "🛒 <b>Seu carrinho</b>\n" + self.ecom_texto_carrinho(conv, t, r), self.ecom_kb_carrinho(conv))

    # ------------------------------------------------------------ frete / CEP
    def ecom_aplicar_cep(self, conv, cep):
        info = M.viacep(cep)
        d = conv["dados"]
        d["cep"] = cep
        d["cidade"] = info["cidade"] if info else ""
        d["uf"] = info["uf"] if info else ""
        d["regiao"] = M.regiao_cep(cep, d["uf"] or None)
        local = f"{d['cidade']}/{d['uf']}" if info else f"região {d['regiao']}"
        return f"📍 CEP {cep} · {E(local)}\n"

    def ecom_info_cep(self, conv, cep):
        return self.ecom_aplicar_cep(conv, cep).strip()

    def ecom_texto_frete(self, conv, t):
        pol = self.ecom_pol(t)
        sub = M.resumo_carrinho(t["catalogo"], conv["carrinho"], pol, None, None)["subtotal"] if conv["carrinho"] else 0
        fr = M.calc_frete(pol, sub, conv["dados"]["regiao"])
        envio = M.envio_dias(t)
        txt = f"🚚 Frete: <b>{'grátis' if fr['gratis'] else M.brl_c(fr['valor'])}</b>" + (" (para o seu carrinho atual)" if conv["carrinho"] else "")
        f = pol.get("frete", {})
        if not fr["gratis"] and f.get("gratisAcima") not in (None, "") and float(f["gratisAcima"]) > 0:
            txt += f"\n🎁 Grátis em compras acima de {M.brl_c(f['gratisAcima'])}"
        txt += f"\n📦 Prazo: envio em até {envio} dia(s) útil(eis) após o pagamento + cerca de {fr['dias']} dia(s) útil(eis) de transporte."
        return txt

    # ------------------------------------------------------------ fechamento
    def ecom_checkout(self, cid, u, conv, t, out):
        if not conv["carrinho"]:
            return out("Seu carrinho está vazio. Vamos escolher algo?", kb([("🔎 Ver produtos", "menu:produtos")]))
        d = conv["dados"]
        conv["volta"] = "checkout"
        if not d.get("cliente"):
            conv["etapa"] = "checkout_nome"
            return out("Para fechar o pedido, qual é o seu nome completo?")
        if not d.get("cep"):
            conv["etapa"] = "checkout_cep"
            return out("📮 Qual o CEP de entrega? (ex.: 01310-100)")
        if not d.get("endereco"):
            conv["etapa"] = "checkout_endereco"
            return out("🏠 Rua, número e complemento para a entrega:")
        if not d.get("pagamento"):
            conv["etapa"] = "checkout_pagamento"
            pg = self.ecom_pol(t).get("pagamento", {})
            pix = f"⚡ Pix ({pg['pixDescontoPct']}% de desconto)" if pg.get("pixDescontoPct") else "⚡ Pix"
            card = f"💳 Cartão (até {pg['parcelas']}x)" if pg.get("parcelas") else "💳 Cartão"
            return out("Como você prefere pagar?", kb([(pix, "pg:pix")], [(card, "pg:cartao")]))
        r = M.resumo_carrinho(t["catalogo"], conv["carrinho"], self.ecom_pol(t), d["regiao"], d["pagamento"])
        conv["etapa"] = "confirmar"
        pg = self.ecom_pol(t).get("pagamento", {})
        ls = ["🧾 <b>Resumo do pedido</b>"] + [f"{i['qtd']}x {E(i['nome'])} — {M.brl_c(i['preco'] * i['qtd'])}" for i in r["itens"]]
        ls.append(f"Subtotal: {M.brl_c(r['subtotal'])}")
        ls.append(f"🚚 Frete ({E(d.get('cidade') or d['regiao'])}): " + ("grátis" if r["frete"]["gratis"] else M.brl_c(r["frete"]["valor"])))
        if r["desconto"]:
            ls.append(f"⚡ Desconto Pix ({pg.get('pixDescontoPct')}%): −{M.brl_c(r['desconto'])}")
        ls.append(f"<b>Total: {M.brl_c(r['total'])}</b>" + (f" · ou em até {pg['parcelas']}x no cartão" if d["pagamento"] == "cartao" and pg.get("parcelas") else ""))
        ls.append(f"📦 Envio em até {M.envio_dias(t, {'itens': r['itens']})} dia(s) útil(eis) após o pagamento + ~{r['frete']['dias']} dia(s) de transporte")
        ls.append(f"🏠 {E(d['endereco'])} · CEP {d['cep']}")
        ls.append(f"👤 {E(d['cliente'])} · pagamento: {'Pix' if d['pagamento'] == 'pix' else 'cartão'}")
        return out("\n".join(ls), kb([("✅ Confirmar pedido", "confirmar")], [("✏️ Alterar carrinho", "menu:carrinho"), ("🙋 Atendente", "atendente")]))

    def ecom_confirmar(self, cid, u, conv, t, out):
        d = conv["dados"]
        if not conv["carrinho"] or not d.get("pagamento") or not d.get("regiao"):
            return self.ecom_checkout(cid, u, conv, t, out)
        r = M.resumo_carrinho(t["catalogo"], conv["carrinho"], self.ecom_pol(t), d["regiao"], d["pagamento"])
        for i in r["itens"]:  # confere estoque de novo
            c = next(x for x in t["catalogo"] if x["id"] == i["id"])
            if i["qtd"] > int(c.get("estoque", 0)):
                return out(f"😕 Só restam {c.get('estoque', 0)} unidade(s) de {E(c['nome'])}. Ajuste o carrinho:", self.ecom_kb_carrinho(conv))
        agora = M.agora_ms()
        tk = {"id": self.novo_id(t), "tenant": t["id"], "seg": "ecommerce", "tipo": "pedido", "canal": "telegram", "chat_id": cid,
              "cliente": d["cliente"], "telegram": u.get("username"), "veiculo": "", "placa": "", "bairro": "",
              "problema": next((m["texto"] for m in conv.get("chat", []) if m["de"] == "cliente" and not m["texto"].startswith(("🛒", "✅", "➕", "➖"))), "Pedido pelo chat"),
              "intent": "comprar", "servicos": [i["id"] for i in r["itens"]], "opcionais": [], "itens": r["itens"],
              "subtotal": r["subtotal"], "frete": r["frete"]["valor"], "freteGratis": r["frete"]["gratis"], "freteDias": r["frete"]["dias"],
              "desconto": r["desconto"], "totalFinal": r["total"], "total": {"min": r["total"], "max": r["total"]},
              "pagamento": d["pagamento"], "cep": d["cep"], "cidade": d.get("cidade", ""), "uf": d.get("uf", ""), "regiao": d["regiao"],
              "endereco": d["endereco"], "prioridade": "media", "status": "Novo", "criado": agora, "humano": False,
              "tempoRespostaSeg": conv.get("respSeg") or 1, "chat": list(conv.get("chat", [])), "eventos": [],
              "historico": [{"status": "Novo", "ts": agora}], "alertas": {}, "rastreio": ""}
        tk["prazo"] = M.soma_dias_uteis(agora, M.envio_dias(t, tk) + 1, t["horario"])  # inclui 1 dia para o pagamento
        self.db.d["tickets"].insert(0, tk)
        conv["carrinho"] = {}; conv["ticket"] = tk["id"]; conv["etapa"] = "pagamento"
        for ev in M.mudar_status(tk, t, "Aguardando pagamento"):
            self.tg.send(cid, "🤖 " + E(ev["texto"]))
        self.tg.send(cid, self.ecom_instrucoes(t, tk), kb([("💸 Já paguei", f"pago:{tk['id']}")], [("🙋 Falar com atendente", "atendente")]))
        tk["chat"].append({"de": "bot", "texto": "Instruções de pagamento enviadas.", "ts": M.agora_ms()})
        self.avisar_donos(t, "🛒 <b>Novo pedido aguardando pagamento</b>\n\n" + self.ecom_resumo_ticket(tk, t), self.ecom_botoes_ticket(tk))

    def ecom_instrucoes(self, t, tk):
        pg = self.ecom_pol(t).get("pagamento", {})
        ls = [f"💰 <b>Pagamento do pedido {tk['id']}: {M.brl_c(tk['totalFinal'])}</b>"]
        if tk["pagamento"] == "pix":
            if pg.get("pixChave"):
                ls.append(f"Pague por Pix usando a chave cadastrada pela loja:\n<code>{E(pg['pixChave'])}</code>\nDepois toque em “Já paguei”.")
            else:
                ls.append("A loja ainda não cadastrou a chave Pix aqui. A equipe vai te mandar os dados de pagamento por esta conversa.")
        else:
            if pg.get("linkCartao"):
                ls.append(f"Pague no cartão pelo link da loja: {E(pg['linkCartao'])}\nDepois toque em “Já paguei”.")
            else:
                ls.append("A equipe da loja vai te enviar o link de pagamento no cartão por esta conversa.")
        ls.append("<i>O pedido só é separado depois que a loja confirmar o pagamento.</i>")
        if t.get("exemplo"):
            ls.append("⚠️ <b>Loja de exemplo:</b> não faça nenhum pagamento real.")
        return "\n".join(ls)

    def ecom_ja_paguei(self, cid, conv, t, tid, out):
        tk = self.db.ticket(tid)
        if not tk or tk.get("chat_id") != cid:
            return out("Não encontrei esse pedido.")
        if tk["status"] != "Aguardando pagamento":
            return out(f"O pedido {tk['id']} está como <b>{E(tk['status'])}</b>.")
        tk["pagamentoInformadoEm"] = M.agora_ms()
        tk["chat"].append({"de": "cliente", "texto": "Já paguei", "ts": M.agora_ms()})
        self.avisar_donos(t, f"💸 <b>{E(tk['cliente'])} informou que pagou o pedido {tk['id']}</b> ({M.brl_c(tk['totalFinal'])}, {('Pix' if tk['pagamento'] == 'pix' else 'cartão')}).\nConfira no seu banco antes de confirmar.",
                          [[("✅ Confirmar pagamento", f"av:{tk['id']}")], [("💬 Responder cliente", f"rp:{tk['id']}")]])
        return out("Obrigado! 🙌 Avisei a loja. Assim que o pagamento for conferido, você recebe a confirmação aqui.")

    # ------------------------------------------------------------ rastreio / troca
    def ecom_achar_pedido(self, t, txt):
        m = re.search(r"(?:ec-?)?\s*(\d{4,6})\b", M.norm(txt))
        if not m:
            return None
        alvo = "EC-" + m.group(1)
        return alvo if any(x["id"] == alvo and x["tenant"] == t["id"] for x in self.db.d["tickets"]) else None

    def ecom_pedir_numero(self, cid, conv, t, out, modo):
        meus = [x for x in self.db.d["tickets"] if x["tenant"] == t["id"] and x.get("chat_id") == cid and x.get("tipo") == "pedido"][:5]
        conv["etapa"] = "rastreio" if modo == "rastreio" else "troca_pedido"
        pref = "rt:" if modo == "rastreio" else "tr:"
        bts = [[(f"{x['id']} · {x['status']} · {M.brl_c(x['totalFinal'])}", pref + x["id"])] for x in meus]
        if modo == "troca":
            bts.append([("Não tenho o número", "tr-sem")])
        txt = "📦 Qual o número do pedido? (ex.: EC-3005)" if modo == "rastreio" else "🔁 Vamos resolver. Qual o número do pedido?"
        if meus:
            txt += "\nOu toque num dos seus pedidos:"
        return out(txt, bts or None)

    def ecom_mostrar_pedido(self, cid, t, tid, out):
        tk = self.db.ticket(tid)
        if not tk or tk["tenant"] != t["id"]:
            return out("Não encontrei esse pedido. Confira o número (ex.: EC-3005).")
        ls = [f"📦 <b>Pedido {tk['id']}</b> · status: <b>{E(tk['status'])}</b>", E(M.itens_texto(tk.get("itens", [])))]
        if tk.get("rastreio"):
            ls.append(f"🔎 Código de rastreio: <code>{E(tk['rastreio'])}</code>")
        if tk["status"] in ("Pago", "Separando"):
            ls.append(f"Envio previsto até {M.data_hora(tk['prazo'])}.")
        teclado = None
        if tk["status"] == "Aguardando pagamento" and tk.get("chat_id") == cid:
            ls.append("Ainda aguardando a confirmação do pagamento.")
            teclado = kb([("💸 Já paguei", f"pago:{tk['id']}")])
        return out("\n".join(ls), teclado)

    def ecom_abrir_troca(self, cid, u, conv, t, motivo, detalhe, out):
        d = conv["dados"]; agora = M.agora_ms()
        ref = self.db.ticket(d.get("pedidoRef") or "")
        tk = {"id": self.novo_id(t), "tenant": t["id"], "seg": "ecommerce", "tipo": "troca", "canal": "telegram", "chat_id": cid,
              "cliente": d.get("cliente") or (ref or {}).get("cliente") or (u.get("nome") or "Cliente").strip(), "telegram": u.get("username"),
              "veiculo": "", "placa": "", "bairro": "", "problema": detalhe if motivo == "Outro motivo" else f"{motivo}" + (f" · pedido {ref['id']}" if ref else ""),
              "motivo": motivo, "pedidoRef": d.get("pedidoRef") or "", "itens": (ref or {}).get("itens", []), "servicos": [],
              "total": {"min": 0, "max": 0}, "prioridade": "media", "status": "Novo", "criado": agora, "humano": False,
              "tempoRespostaSeg": conv.get("respSeg") or 1, "chat": list(conv.get("chat", [])), "eventos": [],
              "historico": [{"status": "Novo", "ts": agora}], "alertas": {}}
        tk["prazo"] = M.soma_dias_uteis(agora, 2, t["horario"])
        self.db.d["tickets"].insert(0, tk)
        conv["etapa"] = "menu"; conv["dados"].pop("pedidoRef", None)
        out(f"✅ Abri a solicitação <b>{tk['id']}</b> ({E(motivo)}).\n\n<b>Nossa política:</b> {E(self.ecom_pol(t).get('troca', ''))}\n\nA equipe vai responder por aqui com as instruções de envio.", self.ecom_menu())
        self.avisar_donos(t, "🔁 <b>Nova solicitação de troca/devolução</b>\n\n" + self.ecom_resumo_ticket(tk, t), self.ecom_botoes_ticket(tk))

    def ecom_humano(self, cid, u, conv, t, txt, out):
        agora = M.agora_ms()
        tk = self.db.ticket(conv.get("ticket") or "")
        if not tk or tk["status"] in ("Entregue", "Resolvido"):
            tk = {"id": self.novo_id(t), "tenant": t["id"], "seg": "ecommerce", "tipo": "atendimento", "canal": "telegram", "chat_id": cid,
                  "cliente": conv["dados"].get("cliente") or (u.get("nome") or "Cliente").strip(), "telegram": u.get("username"),
                  "veiculo": "", "placa": "", "bairro": "", "problema": txt, "itens": [], "servicos": [], "total": {"min": 0, "max": 0},
                  "prioridade": "media", "status": "Novo", "criado": agora, "humano": True, "humanoEm": agora,
                  "tempoRespostaSeg": conv.get("respSeg") or 1, "chat": list(conv.get("chat", [])), "eventos": [],
                  "historico": [{"status": "Novo", "ts": agora}], "alertas": {}}
            tk["prazo"] = M.soma_uteis(agora, (t["sla"].get("media") or {}).get("respostaMin", 15), t["horario"])
            self.db.d["tickets"].insert(0, tk)
            conv["ticket"] = tk["id"]
        else:
            tk["humano"] = True; tk["humanoEm"] = agora
        conv["etapa"] = "humano"
        sla = (t["sla"].get("media") or {}).get("respostaMin", 15)
        out(f"Combinado! Chamei a equipe da {E(t['nome'])}. A resposta chega em até {sla} min em horário de atendimento. Protocolo: <b>{tk['id']}</b>."
            if t.get("donos") else f"Registrei seu pedido de atendimento (protocolo <b>{tk['id']}</b>). Esta loja de teste ainda não tem atendente conectado.")
        self.avisar_donos(t, "🙋 <b>Cliente pediu atendente</b>\n\n" + self.ecom_resumo_ticket(tk, t), [[("💬 Responder cliente", f"rp:{tk['id']}")]] + self.ecom_botoes_ticket(tk)[:1])

    # ------------------------------------------------------------ dono
    def ecom_resumo_ticket(self, tk, t):
        s = M.sla_estado(tk)
        icone = {"ok": "🟢", "atencao": "🟡", "erro": "🔴"}[s["cls"]]
        tipo = {"pedido": "Pedido", "troca": "Troca/devolução", "atendimento": "Atendimento"}.get(tk.get("tipo"), "Pedido")
        ls = [f"<b>{tipo} {tk['id']}</b> · {E(tk['status'])}", f"👤 {E(tk.get('cliente') or 'Cliente')}" + (f" (@{E(tk['telegram'])})" if tk.get("telegram") else "")]
        if tk.get("tipo") == "pedido":
            ls += [f"• {i['qtd']}x {E(i['nome'])} — {M.brl_c(i['preco'] * i['qtd'])}" for i in tk.get("itens", [])]
            ls.append(f"Frete: {'grátis' if tk.get('freteGratis') else M.brl_c(tk.get('frete', 0))}" + (f" · desconto Pix −{M.brl_c(tk['desconto'])}" if tk.get("desconto") else ""))
            ls.append(f"💰 <b>Total {M.brl_c(tk['totalFinal'])}</b> · {'Pix' if tk.get('pagamento') == 'pix' else 'cartão'}" + (" · cliente informou pagamento ✅" if tk.get("pagamentoInformadoEm") and tk["status"] == "Aguardando pagamento" else ""))
            local = f"{tk['cidade']}/{tk['uf']}" if tk.get("cidade") else f"região {tk.get('regiao', '')}"
            ls.append(f"🏠 {E(tk.get('endereco', ''))} · {E(local)} · CEP {E(tk.get('cep', ''))}")
            if tk.get("rastreio"):
                ls.append(f"🔎 Rastreio: {E(tk['rastreio'])}")
            ls.append(f"{icone} SLA de envio: {s['texto']} (até {M.data_hora(tk['prazo'])})")
        else:
            if tk.get("motivo"):
                ls.append(f"Motivo: {E(tk['motivo'])}" + (f" · pedido {E(tk['pedidoRef'])}" if tk.get("pedidoRef") else ""))
            if tk.get("motivo") in (None, "Outro motivo"):
                ls.append(f"💬 “{E(tk.get('problema') or '')}”")
            ls.append(f"{icone} Prazo de resposta: {s['texto']}")
        if tk.get("nps5"):
            ls.append(f"⭐ Avaliação: {tk['nps5']}/5")
        return "\n".join(ls)

    def ecom_botoes_ticket(self, tk):
        prox = M.proximo_status(tk)
        b = []
        if prox == "Pago":
            b.append([("✅ Confirmar pagamento", f"av:{tk['id']}")])
        elif prox == "Enviado":
            b.append([("📦 Informar rastreio e enviar", f"rs:{tk['id']}")])
        elif prox:
            b.append([(("✅ Marcar como resolvido" if prox == "Resolvido" else f"▶ Avançar para {prox}"), f"av:{tk['id']}")])
        b.append([("💬 Responder cliente", f"rp:{tk['id']}"), ("🔄 Atualizar", f"vp:{tk['id']}")])
        return b

    def ecom_texto_dono(self, cid, u, t, txt):
        res = M.parse_ecom(txt)
        out = []
        if res["nome"]:
            t["nome"] = res["nome"][:60]; out.append(f"🏷️ Nome da loja: {E(t['nome'])}")
        for p in res["produtos"]:
            ex = next((c for c in t["catalogo"] if M.norm(c["nome"]) == M.norm(p["nome"])), None)
            alvo = ex or {"id": re.sub(r"[^a-z0-9]+", "-", M.norm(p["nome"])).strip("-")[:20] + "-" + os.urandom(2).hex(), "nome": p["nome"],
                          "categoria": "Cadastrado no chat", "estoque": 10, "envioDias": self.ecom_pol(t).get("envioDiasUteis", 1), "palavras": []}
            alvo["preco"] = p["preco"]; alvo["pecasMin"] = alvo["pecasMax"] = p["preco"]; alvo["maoMin"] = alvo["maoMax"] = 0; alvo["duracao"] = 0
            if p["estoque"] is not None:
                alvo["estoque"] = p["estoque"]
            if p["envioDias"] is not None:
                alvo["envioDias"] = p["envioDias"]
            alvo["palavras"] = sorted(set(alvo.get("palavras", []) + p["palavras"]))
            alvo.pop("exemplo", None)
            if not ex:
                t["catalogo"].append(alvo)
            out.append(("✏️ Atualizei: " if ex else "✅ Cadastrei: ") + f"{E(alvo['nome'])} · {M.brl_c(alvo['preco'])} · estoque {alvo['estoque']} · envio {alvo['envioDias']} dia(s)")
        if res["mudancas"]:
            M.aplicar_politicas(self.ecom_pol(t), res["mudancas"])
            out += [E(x) for x in res["politicas"]]
        if not out:
            return self.tg.send(cid, "Não entendi como produto ou política. Exemplos:\n<code>Fone bluetooth R$ 89 estoque 12 entrega 3 dias</code>\n"
                                     "<code>Frete grátis acima de R$ 199</code>\n<code>Frete fixo R$ 19,90</code>\n<code>Frete SP R$ 15 2 dias, Sudeste R$ 22 4 dias, outros R$ 35 8 dias</code>\n"
                                     "<code>Pix com 5% de desconto, cartão em até 6x</code>\n<code>Chave pix: sua-chave</code>\n<code>Envio em 1 dia útil</code>\n<code>Troca em até 7 dias por arrependimento</code>")
        return self.tg.send(cid, "Entendi!\n" + "\n".join(out) + "\n\nVer tudo: /catalogo e /politicas")

    def ecom_catalogo(self, cid, t):
        if not t["catalogo"]:
            return self.tg.send(cid, "Seu catálogo está vazio. Escreva, por exemplo: <code>Fone bluetooth R$ 89 estoque 12 entrega 3 dias</code>")
        ls = [f"{n}. <b>{E(c['nome'])}</b> — {M.brl_c(c['preco'])} · estoque {c.get('estoque', 0)} · envio {c.get('envioDias', 1)}d" + (" · exemplo" if c.get("exemplo") else "")
              for n, c in enumerate(t["catalogo"], 1)]
        return self.tg.send(cid, f"🗂️ <b>Produtos de {E(t['nome'])}</b>\n" + "\n".join(ls) +
                            "\n\nPara incluir ou alterar: <code>Nome R$ 99 estoque 10 entrega 2 dias</code> · remover: <code>/remover 3</code> · políticas: /politicas")

    # ------------------------------------------------------------ vigia: carrinho abandonado
    def ecom_vigiar_carrinhos(self, agora):
        mudou = False
        for cid, u in self.db.d["usuarios"].items():
            conv = u.get("conv") or {}
            if conv.get("seg") != "ecommerce" or not conv.get("carrinho") or conv.get("lembrado") or not conv.get("carrinhoEm"):
                continue
            if agora - conv["carrinhoEm"] < ABANDONO_MIN * 60000 or conv.get("etapa") in ("humano",):
                continue
            t = self.db.tenant(conv["tenant"])
            if not t:
                continue
            conv["lembrado"] = True; mudou = True
            t.setdefault("metricas", {}).setdefault("abandonados", 0)
            t["metricas"]["abandonados"] += 1
            regra = next((r for r in t.get("automacoes", []) if r["id"] == "carrinho"), None)
            if regra and not regra["ativo"]:
                continue
            itens = M.itens_texto(M.resumo_carrinho(t["catalogo"], conv["carrinho"], self.ecom_pol(t), None, None)["itens"])
            texto = M.template(regra["template"] if regra else "Seus itens ainda estão no carrinho: {servico}.", {"negocio": t["nome"], "servico": itens, "cliente": ""})
            conv.setdefault("chat", []).append({"de": "auto", "regra": "carrinho", "texto": texto, "ts": agora})
            self.tg.send(int(cid), "🤖 " + E(texto), kb([("🛒 Ver carrinho", "menu:carrinho")], [("✅ Fechar pedido", "checkout")]))
        return mudou
