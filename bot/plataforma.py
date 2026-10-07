"""Atende AI — camada da plataforma: administrador, termo do piloto (LGPD), exclusão de dados e piloto.

Mixin usado pela classe Bot (atende_bot.py). Segredos de administração ficam só em bot/data/admin.json (fora do git).
"""
from __future__ import annotations

import html
import json
import os
import re
import secrets
import time

import motor as M

E = html.escape
TERMO_VERSAO = 1
DIA_MS = 86400000
TENTATIVAS_MAX = 5
BLOQUEIO_MS = 3600000
CMD_ADMIN = [("plataforma", "Admin: indicadores globais"), ("lojas", "Admin: todas as lojas"), ("loja", "Admin: detalhe de uma loja (/loja slug)"),
             ("piloto", "Admin: marcar loja como piloto (/piloto slug)"), ("admin_conectar", "Admin: abrir o Modo plataforma na web"),
             ("excluir_loja", "Admin: excluir loja (/excluir_loja slug)")]
REMOVIDO = "[removido a pedido do titular]"


def carregar_admin(data_dir):
    """Cria (na 1ª execução) e lê o código de administrador e a chave da API admin. Nunca vai para o git nem para o log."""
    p = os.path.join(data_dir, "admin.json")
    if os.path.exists(p):
        return json.load(open(p, encoding="utf-8"))
    cfg = {"codigo": "ADM" + secrets.token_hex(6).upper(), "chave_api": secrets.token_urlsafe(24), "criado": M.agora_ms()}
    fd = os.open(p, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        json.dump(cfg, f)
    return cfg


def dia(ms):
    return time.strftime("%Y-%m-%d", time.localtime(ms / 1000))


def termo_texto(pages):
    return ("📄 <b>Termo de uso do piloto · Atende AI</b>\n"
            "• Os dados do seu negócio e dos seus clientes (cadastro, conversas e pedidos) ficam na plataforma Atende AI, operada por Guilherme Romio Netto (byGui), num servidor de teste.\n"
            "• Eles são usados só para operar o atendimento e calcular as métricas do piloto (tempo de resposta, pedidos, conversão, avaliação). Não vendemos nem repassamos a terceiros.\n"
            "• Seus clientes são avisados na 1ª mensagem e podem pedir a exclusão com /excluir_dados. Você também pode pedir a exclusão da sua loja com /excluir_dados.\n"
            "• O bot não processa pagamentos: ele só repassa as instruções que você cadastrar. Modo de teste, sem garantia de disponibilidade.\n"
            f"Política completa: {pages}#/privacidade\n\nPara continuar, toque em <b>Aceito</b>.")


# ------------------------------------------------------------ métricas por loja e globais
def _passou(x, st):
    return any(h["status"] == st for h in x.get("historico", []))


def faturamento(t, tks):
    if t["segmento"] == "ecommerce":
        return round(sum(x.get("totalFinal", 0) for x in tks if x.get("tipo", "pedido") == "pedido" and _passou(x, "Pago")), 2)
    return round(sum(x.get("valorFinal") or M.valor_medio(x) for x in tks if x["status"] == "Entregue"), 2)


def convertidos(t, tks):
    if t["segmento"] == "ecommerce":
        return [x for x in tks if x.get("tipo", "pedido") == "pedido" and _passou(x, "Pago")]
    return [x for x in tks if _passou(x, "Aprovado")]


def ultima_atividade(t, tks, usuarios):
    ts = [t.get("criado", 0), t.get("ultimaAtividade", 0)]
    for x in tks:
        ts += [h["ts"] for h in x.get("historico", [])] + [m.get("ts", 0) for m in x.get("chat", [])[-1:]]
    for u in usuarios.values():
        c = u.get("conv") or {}
        if c.get("tenant") == t["id"]:
            ts.append(c.get("ultima", 0))
    return max(ts)


def nps(tks):
    notas = [x["nps5"] for x in tks if x.get("nps5")]
    if not notas:
        return {"n": 0, "nps": None, "media": None}
    prom = len([n for n in notas if n == 5]); det = len([n for n in notas if n <= 3])
    return {"n": len(notas), "nps": round((prom - det) / len(notas) * 100), "media": round(sum(notas) / len(notas), 1)}


def saude_piloto(t, tks, agora=None):
    agora = agora or M.agora_ms()
    info = t.get("pilotoInfo") or {}
    inicio = info.get("inicio") or t.get("criado") or agora
    dias_total = max(1, int((agora - inicio) // DIA_MS) + 1)
    atv = {d: v for d, v in (t.get("atividade") or {}).items() if d >= dia(inicio)}
    msgs = sum(v.get("cli", 0) + v.get("dono", 0) for v in atv.values())
    no_periodo = [x for x in tks if x.get("criado", 0) >= inicio]
    ult30 = [x for x in tks if x.get("criado", 0) >= agora - 30 * DIA_MS]
    resp_bot = [x.get("tempoRespostaSeg", 0) for x in no_periodo if x.get("tempoRespostaSeg")]
    resp_hum = [x["respostaHumanaSeg"] for x in no_periodo if x.get("respostaHumanaSeg")]
    antes = info.get("antes") or {}
    return {"piloto": bool(t.get("piloto")), "inicio": inicio, "dias": dias_total, "dias_ativos": len([v for v in atv.values() if v.get("cli", 0) + v.get("dono", 0)]),
            "mensagens": msgs, "mensagens_dia": round(msgs / dias_total, 1), "pedidos": len(no_periodo),
            "convertidos": len(convertidos(t, no_periodo)), "nps": nps(no_periodo),
            "antes": antes,
            "depois": {"respostaBotSeg": round(sum(resp_bot) / len(resp_bot)) if resp_bot else None,
                       "respostaHumanaMin": round(sum(resp_hum) / len(resp_hum) / 60, 1) if resp_hum else None,
                       "vendas30d": faturamento(t, ult30), "pedidos30d": len(ult30)}}


def resumo_loja(t, tks, usuarios, agora=None):
    met = t.get("metricas") or {}
    conv = max(met.get("conversas", 0), len(tks))
    cvt = convertidos(t, tks)
    resp = [x.get("tempoRespostaSeg", 0) for x in tks if x.get("tempoRespostaSeg")]
    return {"id": t["id"], "nome": t["nome"], "segmento": t["segmento"], "exemplo": bool(t.get("exemplo")), "piloto": bool(t.get("piloto")),
            "donos": len(t.get("donos", [])), "criado": t.get("criado"), "conversas": conv, "pedidos": len(tks), "convertidos": len(cvt),
            "conversao": round(len(cvt) / conv * 100) if conv else None, "faturamento": faturamento(t, tks),
            "tempoRespostaSeg": round(sum(resp) / len(resp)) if resp else None, "ultimaAtividade": ultima_atividade(t, tks, usuarios),
            "termoAceitoEm": max([x["aceitoEm"] for x in t.get("termos", [])] or [0]) or None,
            "exclusaoSolicitadaEm": (t.get("exclusao") or {}).get("solicitadaEm"), "nps": nps(tks)}


def ticket_admin(x):
    """Visão mínima para o operador da plataforma: sem nome, contato, endereço ou mensagens."""
    s = M.sla_estado(x)
    return {"id": x["id"], "tipo": x.get("tipo", "pedido"), "status": x["status"], "criado": x.get("criado"), "prazo": x.get("prazo"),
            "valor": x.get("totalFinal") or x.get("valorFinal") or round(M.valor_medio(x), 2), "sla": s["cls"], "humano": bool(x.get("humano")),
            "nps5": x.get("nps5"), "canal": x.get("canal", "telegram")}


def plataforma(d, agora=None):
    agora = agora or M.agora_ms()
    lojas = []
    for t in d["tenants"].values():
        tks = [x for x in d["tickets"] if x["tenant"] == t["id"]]
        lojas.append(resumo_loja(t, tks, d["usuarios"], agora))
    reais = [x for x in lojas if not x["exemplo"]]
    tks = d["tickets"]
    resp = [x.get("tempoRespostaSeg", 0) for x in tks if x.get("tempoRespostaSeg")]
    conv = sum(x["conversas"] for x in lojas); cvt = sum(x["convertidos"] for x in lojas)
    return {"lojas": len(lojas), "lojas_reais": len(reais), "lojas_ativas_7d": len([x for x in lojas if x["ultimaAtividade"] >= agora - 7 * DIA_MS]),
            "pilotos": len([x for x in lojas if x["piloto"]]), "conversas": conv, "pedidos": len(tks), "convertidos": cvt,
            "conversao": round(cvt / conv * 100) if conv else None, "faturamento_intermediado": round(sum(x["faturamento"] for x in lojas), 2),
            "faturamento_lojas_reais": round(sum(x["faturamento"] for x in reais), 2),
            "tempoRespostaSeg": round(sum(resp) / len(resp)) if resp else None, "nps": nps(tks), "usuarios": len(d["usuarios"]),
            "admins": len((d.get("plataforma") or {}).get("admins", [])), "geradoEm": agora}


def export_admin(d):
    agora = M.agora_ms()
    lojas = []
    for t in d["tenants"].values():
        tks = sorted([x for x in d["tickets"] if x["tenant"] == t["id"]], key=lambda x: -x.get("criado", 0))
        r = resumo_loja(t, tks, d["usuarios"], agora)
        r["saude"] = saude_piloto(t, tks, agora)
        r["recentes"] = [ticket_admin(x) for x in tks[:10]]
        r["atividade"] = {k: v for k, v in sorted((t.get("atividade") or {}).items())[-30:]}
        lojas.append(r)
    return {"plataforma": plataforma(d, agora), "lojas": lojas, "geradoEm": agora}


def parse_antes(txt):
    n = M.norm(txt); r = {}
    m = re.search(r"respo\w*\D{0,20}?(\d+(?:[.,]\d+)?)\s*(h|hora|horas|min|minutos?|m)\b", n)
    if m:
        v = float(m.group(1).replace(",", ".")); r["respostaMin"] = round(v * 60 if m.group(2).startswith("h") else v)
    m = re.search(r"(?:vend|fatur)\w*\D{0,20}?(?:r\$\s*)?(\d[\d.]*(?:,\d{1,2})?)\s*(mil|k)?", n)
    if m:
        v = float(m.group(1).replace(".", "").replace(",", ".")); r["vendasMes"] = round(v * 1000 if m.group(2) else v, 2)
    m = re.search(r"pedid\w*\D{0,12}?(\d+)", n)
    if m:
        r["pedidosMes"] = int(m.group(1))
    return r


class PlataformaMixin:
    # ------------------------------------------------------------ estado
    def plat(self):
        return self.db.d.setdefault("plataforma", {"admins": [], "tentativas": {}})

    def eh_admin(self, cid):
        return cid in self.plat().get("admins", [])

    def avisar_admins(self, texto, teclado=None):
        for a in self.plat().get("admins", []):
            self.tg.send(a, texto, teclado)

    def comandos_chat(self, cid, u):
        base = self.CMD_DONO if u.get("dono_de") else self.CMD_CLIENTE
        cmds = list(base) + (CMD_ADMIN if self.eh_admin(cid) else [])
        self.tg.call("setMyCommands", commands=[{"command": c, "description": d[:256]} for c, d in cmds],
                     scope={"type": "chat", "chat_id": cid})

    def registrar_atividade(self, cid):
        u = self.db.d["usuarios"].get(str(cid))
        if not u:
            return
        dono = u.get("modo") == "dono" and u.get("dono_de")
        t = self.db.tenant((u.get("tenant_dono") or u["dono_de"][0]) if dono else (u.get("tenant") or ""))
        if not t:
            return
        agora = M.agora_ms()
        atv = t.setdefault("atividade", {})
        d = atv.setdefault(dia(agora), {"cli": 0, "dono": 0})
        d["dono" if dono else "cli"] += 1
        for k in sorted(atv)[:-120]:
            atv.pop(k)
        t["ultimaAtividade"] = agora

    def abertura(self, u, t):
        """Conta a conversa e devolve a nota de privacidade (só na 1ª conversa deste cliente com este negócio)."""
        t.setdefault("metricas", {}).setdefault("conversas", 0)
        t["metricas"]["conversas"] += 1
        avisos = u.setdefault("privacidade", {})
        if t["id"] in avisos:
            return ""
        avisos[t["id"]] = M.agora_ms()
        return (f"\n🔒 <i>Seus dados (nome, mensagens e pedidos) ficam na plataforma Atende AI e são usados só para este atendimento. "
                f"Para apagar: /excluir_dados · {self.PAGES}#/privacidade</i>")

    # ------------------------------------------------------------ termo do piloto
    def termo_ok(self, cid, t):
        return any(x.get("chat") == cid and x.get("versao", 0) >= TERMO_VERSAO for x in t.get("termos", []))

    def exigir_termo(self, cid, u, pend):
        u["termo_pendente"] = pend
        return self.tg.send(cid, termo_texto(self.PAGES), [[("✅ Aceito", "termo:ok")], [("Não aceito", "termo:nao")]])

    def termo_resposta(self, cid, u, aceito):
        pend = u.pop("termo_pendente", None)
        if not pend:
            return self.tg.send(cid, "Não há nada aguardando aceite. Área do dono: /dono")
        if not aceito:
            return self.tg.send(cid, "Tudo bem. Sem o aceite não ativamos o negócio para você, e nada foi criado. Você pode continuar como cliente; para tentar de novo, envie /dono.")
        agora = M.agora_ms()
        u["termo"] = {"versao": TERMO_VERSAO, "aceitoEm": agora}
        tipo = pend.get("tipo")
        if tipo == "criar":
            nome = pend["nome"]; slug = self.slugify(nome)
            while self.db.tenant(slug):
                slug = self.slugify(nome)[:22] + "-" + secrets.token_hex(2)
            t = self.novo_tenant(slug, nome, pend["seg"], pend.get("modo") == "ex")
            self.db.d["tenants"][slug] = t
        else:
            t = self.db.tenant(pend.get("slug") or "")
            if not t:
                return self.tg.send(cid, "Esse negócio não existe mais. Envie /dono para começar de novo.")
            if tipo == "claim" and t["donos"] and cid not in t["donos"]:
                return self.tg.send(cid, "Esse negócio já tem dono. Peça o código de atendente para ele e envie /dono CÓDIGO.")
        t.setdefault("termos", []).append({"chat": cid, "aceitoEm": agora, "versao": TERMO_VERSAO})
        self.tg.send(cid, f"✅ Termo aceito em {M.data_hora(agora)}. Obrigado!")
        if tipo == "existente":
            u["modo"] = "dono"
            return self.cmd_painel(cid, u)
        return self.virar_dono(cid, u, t, coadmin=(tipo == "codigo"))

    # ------------------------------------------------------------ exclusão de dados (LGPD)
    def cmd_excluir(self, cid, u):
        bts = [("🗑️ Apagar meus dados de cliente", "exc:cli")]
        for slug in u.get("dono_de", []):
            t = self.db.tenant(slug)
            if t:
                bts.append((f"📨 Pedir exclusão da loja {t['nome'][:24]}", f"exc:loja:{slug}"))
        bts.append(("Cancelar", "exc:cancel"))
        return self.tg.send(cid, "🗑️ <b>Exclusão de dados</b>\nComo cliente: apagamos seu nome, @usuário, mensagens, endereço, CEP, placa e o histórico das suas conversas em todos os negócios. "
                                 "Os pedidos continuam só como números anônimos (valor e status), para as contas da loja.\n"
                                 + ("Como dono: o pedido de exclusão da loja vai para o administrador da plataforma, que confirma e te avisa.\n" if u.get("dono_de") else "")
                                 + "\nO que você quer fazer?", linhas_(bts))

    def apagar_cliente(self, cid):
        agora = M.agora_ms(); n = 0; avisar = {}
        for x in self.db.d["tickets"]:
            if x.get("chat_id") != cid:
                continue
            n += 1
            for k in ("cliente",):
                x[k] = "Cliente (dados removidos)"
            for k in ("telegram", "telefone", "veiculo", "placa", "bairro", "endereco", "cep", "rastreio"):
                if x.get(k):
                    x[k] = ""
            if x.get("problema"):
                x["problema"] = REMOVIDO
            x["chat_id"] = None; x["chat"] = []
            for e in x.get("eventos", []):
                e["texto"] = ""
            x["anonimizadoEm"] = agora
            avisar.setdefault(x["tenant"], []).append(x["id"])
        u = self.db.d["usuarios"].get(str(cid))
        if u and (u.get("dono_de") or self.eh_admin(cid)):
            for k in ("conv", "tenant", "nome", "username", "privacidade", "respondendo"):
                u.pop(k, None)
            u["tenant"] = None; u["conv"] = None
        else:
            self.db.d["usuarios"].pop(str(cid), None)
        for slug, ids in avisar.items():
            t = self.db.tenant(slug)
            if t:
                self.avisar_donos(t, f"🔒 Um cliente pediu a exclusão dos dados pessoais (LGPD). Pedido(s) {', '.join(ids)}: nome, contato e mensagens foram removidos; valores e status continuam.")
        return n

    def excluir_callback(self, cid, u, dado):
        if dado == "exc:cancel":
            return self.tg.send(cid, "Ok, nada foi apagado.")
        if dado == "exc:cli":
            return self.tg.send(cid, "Tem certeza? Isso não pode ser desfeito.", [[("Sim, apagar meus dados", "exc:cli:ok")], [("Cancelar", "exc:cancel")]])
        if dado == "exc:cli:ok":
            n = self.apagar_cliente(cid)
            return self.tg.send(cid, f"✅ Pronto. Apagamos seus dados pessoais{f' e anonimizamos {n} pedido(s)' if n else ''}. "
                                     "Se você escrever de novo, uma nova conversa começa do zero.")
        if dado.startswith("exc:loja:"):
            slug = dado[9:]; t = self.db.tenant(slug)
            if not t or slug not in u.get("dono_de", []):
                return self.tg.send(cid, "Essa loja não é sua.")
            t["exclusao"] = {"solicitadaEm": M.agora_ms(), "por": cid}
            quem = ("@" + u["username"]) if u.get("username") else (u.get("nome") or str(cid))
            self.avisar_admins(f"🗑️ <b>Pedido de exclusão de loja</b>\n{E(t['nome'])} (<code>{slug}</code>) · pedido por {E(quem)}.\n"
                               f"Para executar: /excluir_loja {slug}", [[("🗑️ Excluir agora", f"adm:del:{slug}")]])
            return self.tg.send(cid, f"📨 Pedido de exclusão da loja <b>{E(t['nome'])}</b> registrado em {M.data_hora(t['exclusao']['solicitadaEm'])}. "
                                     "O administrador da plataforma confirma e te avisa por aqui. Até lá, a loja continua funcionando.")

    def excluir_loja(self, cid, slug):
        t = self.db.tenant(slug)
        if not t:
            return self.tg.send(cid, "Loja não encontrada. Veja /lojas.")
        donos = list(t.get("donos", []))
        n = len([x for x in self.db.d["tickets"] if x["tenant"] == slug])
        self.db.d["tickets"] = [x for x in self.db.d["tickets"] if x["tenant"] != slug]
        self.db.d["tenants"].pop(slug)
        for u in self.db.d["usuarios"].values():
            if slug in u.get("dono_de", []):
                u["dono_de"].remove(slug)
            for k in ("tenant_dono", "tenant"):
                if u.get(k) == slug:
                    u[k] = None
            if (u.get("conv") or {}).get("tenant") == slug:
                u["conv"] = None
            if u.get("modo") == "dono" and not u.get("dono_de"):
                u["modo"] = "cliente"
        for d in donos:
            self.tg.send(d, f"🗑️ A loja <b>{E(t['nome'])}</b> e os {n} pedido(s) dela foram excluídos da plataforma Atende AI, como você pediu.")
        return self.tg.send(cid, f"🗑️ Loja <b>{E(t['nome'])}</b> excluída: {n} pedido(s) apagados, {len(donos)} dono(s) avisados.")

    # ------------------------------------------------------------ administrador
    def cmd_admin(self, cid, u, arg, msg_id=None):
        if self.eh_admin(cid) and not arg:
            return self.cmd_plataforma(cid)
        tent = self.plat().setdefault("tentativas", {}).setdefault(str(cid), {"n": 0, "ate": 0})
        agora = M.agora_ms()
        if tent["ate"] > agora:
            return self.tg.send(cid, "Acesso negado. Muitas tentativas: tente de novo mais tarde.")
        if not arg:
            return self.tg.send(cid, "Área restrita ao administrador da plataforma. Envie <code>/admin SEU_CÓDIGO</code>.")
        if not secrets.compare_digest(arg.strip().upper().encode(), self.admin_cfg["codigo"].encode()):
            tent["n"] += 1
            if tent["n"] >= TENTATIVAS_MAX:
                tent["n"] = 0; tent["ate"] = agora + BLOQUEIO_MS
            return self.tg.send(cid, "Acesso negado: código inválido.")
        self.plat()["tentativas"].pop(str(cid), None)
        if cid not in self.plat()["admins"]:
            self.plat()["admins"].append(cid)
        if msg_id:
            self.tg.call("deleteMessage", _t=10, chat_id=cid, message_id=msg_id)  # tira o código do histórico do chat
        self.comandos_chat(cid, u)
        return self.tg.send(cid, "🛡️ <b>Você agora é administrador da plataforma Atende AI.</b>\n"
                                 "/plataforma — indicadores globais\n/lojas — todas as lojas\n/loja slug — detalhe\n/piloto slug — marcar loja como piloto (<code>/piloto slug off</code> desmarca)\n"
                                 "/admin_conectar — abrir o Modo plataforma na web\n/excluir_loja slug — excluir loja (pede confirmação)\n\n"
                                 "<i>A mensagem com o código foi apagada deste chat.</i>")

    def comando_admin(self, cid, u, cmd, arg):
        if not self.eh_admin(cid):
            return self.tg.send(cid, "Acesso negado: comando restrito ao administrador da plataforma.")
        if cmd == "plataforma":
            return self.cmd_plataforma(cid)
        if cmd == "lojas":
            return self.cmd_lojas(cid)
        if cmd == "loja":
            return self.cmd_loja(cid, arg.strip())
        if cmd == "piloto":
            return self.cmd_piloto(cid, arg)
        if cmd == "admin_conectar":
            url = self.tunnel_url()
            if not url:
                return self.tg.send(cid, "O túnel da API não está ativo agora; o Modo plataforma na web fica com dados de demonstração.")
            import urllib.parse
            link = f"{self.PAGES}?api={urllib.parse.quote(url, safe='')}&admin={self.admin_cfg['chave_api']}#/admin"
            return self.tg.send(cid, f"🛡️ <b>Modo plataforma ao vivo</b>\n{E(link)}\n\n⚠️ Este link tem a chave de administrador (lê todas as lojas). Não compartilhe.\nO endereço muda quando o servidor de teste reinicia; peça /admin_conectar de novo.")
        if cmd == "excluir_loja":
            t = self.db.tenant(arg.strip())
            if not t:
                return self.tg.send(cid, "Use <code>/excluir_loja slug</code> (veja os slugs em /lojas).")
            n = len([x for x in self.db.d["tickets"] if x["tenant"] == t["id"]])
            return self.tg.send(cid, f"⚠️ Excluir <b>{E(t['nome'])}</b> (<code>{t['id']}</code>) e {n} pedido(s)? Isso não pode ser desfeito.",
                                [[("🗑️ Sim, excluir", f"adm:del:{t['id']}")], [("Cancelar", "exc:cancel")]])

    def admin_callback(self, cid, u, dado):
        if not self.eh_admin(cid):
            return self.tg.send(cid, "Acesso negado: comando restrito ao administrador da plataforma.")
        if dado.startswith("adm:loja:"):
            return self.cmd_loja(cid, dado[9:])
        if dado.startswith("adm:del:"):
            return self.excluir_loja(cid, dado[8:])

    def cmd_plataforma(self, cid):
        p = plataforma(self.db.d)
        tr = p["tempoRespostaSeg"]; nn = p["nps"]
        return self.tg.send(cid, "🛡️ <b>Plataforma Atende AI</b> · visão global\n"
                                 f"Lojas: <b>{p['lojas']}</b> ({p['lojas_reais']} reais, {p['lojas']-p['lojas_reais']} de exemplo) · ativas nos últimos 7 dias: <b>{p['lojas_ativas_7d']}</b> · pilotos: {p['pilotos']}\n"
                                 f"Conversas: <b>{p['conversas']}</b> · pedidos/atendimentos: <b>{p['pedidos']}</b> · convertidos: {p['convertidos']}\n"
                                 f"Conversão: <b>{str(p['conversao']) + '%' if p['conversao'] is not None else '—'}</b>\n"
                                 f"Faturamento intermediado: <b>{M.brl_c(p['faturamento_intermediado'])}</b> (lojas reais: {M.brl_c(p['faturamento_lojas_reais'])})\n"
                                 f"1ª resposta média: <b>{(str(tr) + ' s') if tr is not None else '—'}</b> · NPS: <b>{nn['nps'] if nn['nps'] is not None else '—'}</b> ({nn['n']} avaliações)\n"
                                 f"Usuários: {p['usuarios']} · admins: {p['admins']}\n\nLojas: /lojas · Web: /admin_conectar")

    def cmd_lojas(self, cid):
        d = self.db.d; ls = []; bts = []
        ic = {"oficina": "🔧", "ecommerce": "🛒"}
        for t in sorted(d["tenants"].values(), key=lambda t: -ultima_atividade(t, [x for x in d["tickets"] if x["tenant"] == t["id"]], d["usuarios"])):
            r = resumo_loja(t, [x for x in d["tickets"] if x["tenant"] == t["id"]], d["usuarios"])
            tags = (" · 🧪 piloto" if r["piloto"] else "") + (" · exemplo" if r["exemplo"] else "") + (" · ⚠️ exclusão pedida" if r["exclusaoSolicitadaEm"] else "")
            ls.append(f"{ic.get(t['segmento'], '🏬')} <b>{E(t['nome'])}</b> (<code>{t['id']}</code>){tags}\n"
                      f"   donos {r['donos']} · pedidos {r['pedidos']} · {M.brl_c(r['faturamento'])} · última atividade {M.data_hora(r['ultimaAtividade'])}")
            bts.append((f"{ic.get(t['segmento'], '🏬')} {t['nome'][:30]}", f"adm:loja:{t['id']}"))
        return self.tg.send(cid, f"🏪 <b>{len(ls)} loja(s) na plataforma</b>\n" + "\n".join(ls[:25]), linhas_(bts[:20], 2))

    def cmd_loja(self, cid, slug):
        t = self.db.tenant(slug)
        if not t:
            return self.tg.send(cid, "Use <code>/loja slug</code> (veja os slugs em /lojas).")
        tks = sorted([x for x in self.db.d["tickets"] if x["tenant"] == slug], key=lambda x: -x.get("criado", 0))
        r = resumo_loja(t, tks, self.db.d["usuarios"]); s = saude_piloto(t, tks); k = self.kpis(t, tks)
        ant = s["antes"]; dep = s["depois"]
        ls = [f"🏪 <b>{E(t['nome'])}</b> (<code>{slug}</code>) · {self.SEG_TXT.get(t['segmento'], t['segmento'])}" + (" · 🧪 piloto" if r["piloto"] else "") + (" · exemplo" if r["exemplo"] else ""),
              f"Donos: {r['donos']} · termo aceito: {M.data_hora(r['termoAceitoEm']) if r['termoAceitoEm'] else 'não'} · criada {M.data_hora(t.get('criado') or 0)}",
              f"Conversas {r['conversas']} · pedidos {r['pedidos']} · convertidos {r['convertidos']} · conversão {str(r['conversao']) + '%' if r['conversao'] is not None else '—'}",
              f"Faturamento: <b>{M.brl_c(r['faturamento'])}</b> · 1ª resposta {k.get('tempo_resposta')} · SLA {k.get('sla_cumprido')} · avaliação {k.get('avaliacao')}",
              f"\n<b>Saúde do piloto</b> (desde {M.data_hora(s['inicio'])}): {s['dias_ativos']}/{s['dias']} dias ativos · {str(s['mensagens_dia']).replace('.', ',')} msg/dia · {s['pedidos']} pedidos · NPS {s['nps']['nps'] if s['nps']['nps'] is not None else '—'}",
              f"Antes × depois: resposta {str(ant.get('respostaMin')) + ' min' if ant.get('respostaMin') is not None else '?'} → bot {str(dep['respostaBotSeg']) + ' s' if dep['respostaBotSeg'] is not None else '—'}"
              f" (equipe {str(dep['respostaHumanaMin']) + ' min' if dep['respostaHumanaMin'] is not None else '—'}) · vendas/mês {M.brl_c(ant['vendasMes']) if ant.get('vendasMes') is not None else '?'} → {M.brl_c(dep['vendas30d'])} (30 dias)"]
        if r["exclusaoSolicitadaEm"]:
            ls.append(f"⚠️ Exclusão pedida em {M.data_hora(r['exclusaoSolicitadaEm'])}: /excluir_loja {slug}")
        if tks:
            ls.append("\n<b>Recentes</b>")
            for x in tks[:6]:
                a = ticket_admin(x)
                ls.append(f"• {a['id']} · {E(a['status'])} · {M.brl_c(a['valor']) if a['valor'] else '—'} · {M.data_hora(a['criado'] or 0)}")
        bts = [[("🧪 Tirar do piloto" if r["piloto"] else "🧪 Marcar como piloto", f"adm:pil:{slug}:{'off' if r['piloto'] else 'on'}")]]
        return self.tg.send(cid, "\n".join(ls), bts)

    def cmd_piloto(self, cid, arg):
        partes = arg.split()
        t = self.db.tenant(partes[0]) if partes else None
        if not t:
            pil = [x["id"] for x in self.db.d["tenants"].values() if x.get("piloto")]
            return self.tg.send(cid, "Use <code>/piloto slug</code> para marcar (ou <code>/piloto slug off</code>). Pilotos agora: " + (", ".join(pil) or "nenhum") + ". Slugs em /lojas.")
        return self.marcar_piloto(cid, t, not (len(partes) > 1 and partes[1].lower() in ("off", "nao", "não", "sair")))

    def marcar_piloto(self, cid, t, on):
        t["piloto"] = on
        info = t.setdefault("pilotoInfo", {"antes": {}})
        if on and not info.get("inicio"):
            info["inicio"] = M.agora_ms()
            self.avisar_donos(t, f"🧪 <b>{E(t['nome'])}</b> entrou no piloto do Atende AI!\nPara medirmos o antes e o depois, conte como era antes do bot:\n"
                                 "<code>/antes resposta 2h vendas R$ 8.000 pedidos 40</code>\n(tempo médio para responder um cliente, vendas por mês e pedidos por mês)")
        return self.tg.send(cid, f"{'🧪 Marcada como piloto' if on else 'Removida do piloto'}: <b>{E(t['nome'])}</b> (<code>{t['id']}</code>)." +
                            (f" Início do piloto: {M.data_hora(info['inicio'])}. Os donos foram convidados a preencher o “antes” com /antes." if on else ""))

    # ------------------------------------------------------------ dono: antes do piloto
    def cmd_antes(self, cid, t, arg):
        info = t.setdefault("pilotoInfo", {"antes": {}})
        antes = info.setdefault("antes", {})
        if arg:
            novo = parse_antes(arg)
            if not novo:
                return self.tg.send(cid, "Não entendi. Exemplo: <code>/antes resposta 2h vendas R$ 8.000 pedidos 40</code>")
            antes.update(novo); antes["registradoEm"] = M.agora_ms()
        s = saude_piloto(t, [x for x in self.db.d["tickets"] if x["tenant"] == t["id"]])
        dep = s["depois"]
        return self.tg.send(cid, ("✅ Anotado!\n" if arg else "") + "📈 <b>Antes × depois</b> (piloto)\n"
                                 f"Tempo para responder um cliente: antes <b>{str(antes.get('respostaMin')) + ' min' if antes.get('respostaMin') is not None else '?'}</b> → agora o bot responde em <b>{str(dep['respostaBotSeg']) + ' s' if dep['respostaBotSeg'] is not None else '—'}</b>\n"
                                 f"Vendas por mês: antes <b>{M.brl_c(antes['vendasMes']) if antes.get('vendasMes') is not None else '?'}</b> → últimos 30 dias <b>{M.brl_c(dep['vendas30d'])}</b>\n"
                                 f"Pedidos por mês: antes <b>{antes.get('pedidosMes', '?')}</b> → últimos 30 dias <b>{dep['pedidos30d']}</b>\n\n"
                                 "Para preencher ou corrigir: <code>/antes resposta 2h vendas R$ 8.000 pedidos 40</code>")


def linhas_(botoes, por_linha=1):
    return [botoes[i:i + por_linha] for i in range(0, len(botoes), por_linha)]
