"""Atende AI — Secretário do dono: uma mensagem do dono vira várias tarefas, com confirmação e prova.

Base: docs/secretario/ (memorial e spec do Secretário IA). Regras principais:
- separa intenções antes de executar; não inventa horário, valor nem pessoa;
- agenda só é gravada com pessoa + data + hora; o que falta é perguntado numa mensagem só;
- lembrete sem horário: hoje às 18:00 (America/Sao_Paulo), declarado (se já passou das 18h, amanhã às 18:00);
- conta a pagar fica em aguardando_ok e só muda para paga com o botão explícito do dono;
- toda tarefa tem prova (#AG-0003, #LB-0012, #CT-0004...).
"""
from __future__ import annotations

import html
import re
from datetime import datetime, timedelta

import motor as M

E = html.escape
TZ = M.TZ
STATUS = ["rascunho", "aguardando_dado", "aguardando_ok", "executada", "falhou", "cancelada"]
STATUS_TXT = {"rascunho": "rascunho", "aguardando_dado": "aguardando dado", "aguardando_ok": "aguardando seu ok", "executada": "executada",
              "falhou": "falhou", "cancelada": "cancelada"}
PREFIXO = {"agenda.criar": "AG", "lembrete.criar": "LB", "financeiro.pagar": "CT", "estoque.repor": "RP", "cliente.ligar": "LG"}
TIPO_TXT = {"agenda.criar": "Agenda", "lembrete.criar": "Lembrete", "financeiro.pagar": "Conta a pagar", "estoque.repor": "Repor estoque", "cliente.ligar": "Ligar para cliente"}
HORA_PADRAO = 18
PERIODO = {"manha": 9, "manhã": 9, "tarde": 15, "noite": 20}
DIAS_SEM = {"domingo": 6, "segunda": 0, "terca": 1, "terça": 1, "quarta": 2, "quinta": 3, "sexta": 4, "sabado": 5, "sábado": 5}
DIAS_CURTO = ["seg", "ter", "qua", "qui", "sex", "sáb", "dom"]
VERBOS = r"(?:me\s+)?(?:agend|marc|pag|lembr|lembre|repor|rep[oô]e|reabastec|encomend|comprar\s+mais|lig|retorn)"
DATA_RX = r"(?:hoje|amanh[ãa]|depois\s+de\s+amanh[ãa]|(?:na\s+|no\s+|nesta\s+|neste\s+|pr[oó]xim[ao]\s+)?(?:segunda|ter[çc]a|quarta|quinta|sexta|s[áa]bado|domingo)(?:-feira)?|dia\s+\d{1,2}(?:/\d{1,2})?|\d{1,2}/\d{1,2})"
HORA_RX = r"(?:(?:[àa]s?\s+)?\d{1,2}\s*(?:h|:)\s*\d{0,2}(?:\s*min)?|[àa]s\s+\d{1,2}\b|meio[\s-]dia|(?:de|à|a|pela)\s+(?:manh[ãa]|tarde|noite))"


# ------------------------------------------------------------ datas e horas
def agora_dt(agora_ms=None):
    return datetime.fromtimestamp((agora_ms or M.agora_ms()) / 1000, TZ)


def achar_data(txt, agora):
    t = txt.lower()
    hoje = agora.date()
    if re.search(r"depois\s+de\s+amanh[ãa]", t):
        return hoje + timedelta(days=2)
    if re.search(r"\bamanh[ãa]\b", t):
        return hoje + timedelta(days=1)
    if re.search(r"\bhoje\b", t):
        return hoje
    m = re.search(r"\b(?:dia\s+)?(\d{1,2})/(\d{1,2})\b", t)
    if m:
        d, mes = int(m.group(1)), int(m.group(2))
        try:
            x = hoje.replace(month=mes, day=d)
            return x if x >= hoje else x.replace(year=hoje.year + 1)
        except ValueError:
            return None
    m = re.search(r"\bdia\s+(\d{1,2})\b", t)
    if m:
        d = int(m.group(1))
        for k in range(0, 3):
            ano, mes = hoje.year + (hoje.month - 1 + k) // 12, (hoje.month - 1 + k) % 12 + 1
            try:
                x = hoje.replace(year=ano, month=mes, day=d)
            except ValueError:
                continue
            if x >= hoje:
                return x
        return None
    m = re.search(r"\b(segunda|ter[çc]a|quarta|quinta|sexta|s[áa]bado|domingo)\b", t)
    if m:
        alvo = DIAS_SEM[m.group(1).replace("ç", "c").replace("á", "a")] if m.group(1).replace("ç", "c").replace("á", "a") in DIAS_SEM else DIAS_SEM[m.group(1)]
        delta = (alvo - hoje.weekday()) % 7 or 7
        return hoje + timedelta(days=delta)
    return None


def achar_hora(txt):
    """(hora, minuto, declarado_por_periodo) ou None. Só horários válidos (0–23h, 0–59 min)."""
    t = txt.lower()
    if re.search(r"meio[\s-]dia", t):
        return 12, 0, False
    for rx in (r"\b(\d{1,2})\s*:\s*(\d{2})\b", r"\b(\d{1,2})\s*h\s*(\d{2})\b", r"\b(\d{1,2})\s*h(?:oras?)?\b", r"\b[àa]s\s+(\d{1,2})\b(?!\s*/)"):
        m = re.search(rx, t)
        if m:
            h = int(m.group(1)); mi = int(m.group(2)) if m.lastindex and m.lastindex >= 2 and m.group(2) else 0
            if re.search(r"\b(da\s+tarde|da\s+noite)\b", t) and h < 12:
                h += 12
            if 0 <= h <= 23 and 0 <= mi <= 59:
                return h, mi, False
            return None
    m = re.search(r"\b(?:de|à|a|pela|hoje\s+[àa])\s+(manh[ãa]|tarde|noite)\b", t) or re.search(r"\b(manh[ãa]|tarde|noite)\b", t)
    if m:
        return PERIODO[m.group(1).replace("ã", "a") if m.group(1).replace("ã", "a") in PERIODO else m.group(1)], 0, True
    return None


def ts_de(data, hm):
    return int(datetime(data.year, data.month, data.day, hm[0], hm[1], tzinfo=TZ).timestamp() * 1000)


def fmt_hora(h, mi):
    return f"{h}h" if mi == 0 else f"{h}h{mi:02d}"


def fmt_quando(ms, agora_ms=None):
    d = datetime.fromtimestamp(ms / 1000, TZ)
    hoje = agora_dt(agora_ms).date()
    if d.date() == hoje:
        dia = "hoje"
    elif d.date() == hoje + timedelta(days=1):
        dia = "amanhã"
    else:
        dia = f"{DIAS_CURTO[d.weekday()]}, {d.strftime('%d/%m')}"
    return f"{dia} às {fmt_hora(d.hour, d.minute)}"


def fmt_data(iso, agora_ms=None):
    d = datetime.fromisoformat(iso).date()
    hoje = agora_dt(agora_ms).date()
    if d == hoje:
        return "hoje"
    if d == hoje + timedelta(days=1):
        return "amanhã"
    return f"{DIAS_CURTO[d.weekday()]}, {d.strftime('%d/%m')}"


def padrao_lembrete(agora):
    """Hoje às 18:00; se já passou, amanhã às 18:00."""
    d = agora.date() if agora.hour < HORA_PADRAO else agora.date() + timedelta(days=1)
    return ts_de(d, (HORA_PADRAO, 0))


# ------------------------------------------------------------ extração
def limpar(s):
    s = re.sub(DATA_RX, " ", s, flags=re.I)
    s = re.sub(HORA_RX, " ", s, flags=re.I)
    s = re.sub(r"\b(vence|vencimento|com vencimento)\b.*$", " ", s, flags=re.I)
    s = re.sub(r"r\$\s*\d[\d.]*(?:,\d{1,2})?", " ", s, flags=re.I)
    s = re.sub(r"\s+", " ", s).strip(" ,.;:-")
    return s


def valor_de(txt):
    m = re.search(r"r\$\s*(\d[\d.]*(?:,\d{1,2})?)", txt, flags=re.I)
    return float(m.group(1).replace(".", "").replace(",", ".")) if m else None


def pessoa_de(txt):
    m = re.search(r"\b(?:com|pro|pra|para|ao|à|a)\s+(?:o\s+|a\s+|seu\s+|dona?\s+|sr\.?\s+|sra\.?\s+)?(?:cliente\s+)?([A-Za-zÀ-ú][\wÀ-ú']+(?:\s+(?!hoje|amanh|dia\b|às|as\b|de\b|da\b|do\b|no\b|na\b|e\b)[A-ZÀ-Ú][\wÀ-ú']+){0,2})", txt)
    if not m:
        return None
    nome = m.group(1)
    if M.norm(nome) in ("hoje", "amanha", "cliente", "fornecedor", "dia", "segunda", "terca", "quarta", "quinta", "sexta", "sabado", "domingo", "reuniao", "conta"):
        return None
    return " ".join(M.cap(p) for p in nome.split())


def tipo_de(c):
    n = M.norm(c)
    if re.search(r"r\$\s*\d", n) and re.search(r"\b\d+\s*(h|min|hora|horas)\b|\bestoque\b|\bentrega\b|\ba\s+\d+", n) and not re.search(r"\b(lembr|agend|marcar|pagar|pague|repor|ligar)", n):
        return None  # parece cadastro de catálogo (“Troca de óleo R$ 180 1h”), não pedido ao secretário
    if re.search(r"\blembr|nao esquecer|nao me deixa esquecer", n):
        return "lembrete.criar"
    if re.search(r"\b(agendar|agende|agenda|marcar|marque|marca)\s+(?:uma?\s+|o\s+|a\s+)?(reuni|visita|consulta|compromisso|horario|encontro|call|conversa|almoco|cafe|com\b|\w+\s+com\b)", n) \
            or re.search(r"\breuniao\b|\bcompromisso\b", n):
        return "agenda.criar"
    if re.search(r"\bpag(ar|o|ue)\b|\bboleto\b|\bfatura\b|\bconta de\b|\bvence\b", n):
        return "financeiro.pagar"
    if re.search(r"\b(repor|repoe|reabastec\w*|encomend\w*|comprar mais|pedir mais|reposicao)\b|\bpedir .* (ao|pro|para o) fornecedor", n):
        return "estoque.repor"
    if re.search(r"\b(ligar|retornar|telefonar)\b", n):
        return "cliente.ligar"
    return None


def quebrar(texto, juntar=True):
    partes = re.split(r"[;\n]+|,\s*|\.\s+|\s+e\s+(?=" + VERBOS + r")|\s+tamb[ée]m\s+", texto.strip(), flags=re.I)
    out = []
    for p in partes:
        p = (p or "").strip(" .")
        if not p:
            continue
        if juntar and out and not tipo_de(p) and not re.match(r"^(?:e\s+)?" + VERBOS, p, re.I):
            out[-1] = out[-1] + ", " + p  # complemento do item anterior (ex.: "vence dia 12")
        else:
            out.append(re.sub(r"^e\s+", "", p, flags=re.I))
    return out


def slots_de(tipo, c, agora, catalogo=None):
    s = {}
    d = achar_data(c, agora); h = achar_hora(c)
    if tipo == "agenda.criar":
        m = re.search(r"\b(?:agendar|marcar|agende|marque|agenda)\s+(?:uma?\s+)?([a-zà-ú]+)", c, re.I)
        assunto = m.group(1).lower() if m and M.norm(m.group(1)) not in ("com", "pra", "para", "hoje", "amanha") else ("reunião" if re.search(r"reuni", c, re.I) else "compromisso")
        s["assunto"] = assunto
        p = pessoa_de(c)
        if p:
            s["pessoa"] = p
        if d:
            s["data"] = d.isoformat()
        if h:
            s["hora"] = f"{h[0]:02d}:{h[1]:02d}"
    elif tipo == "financeiro.pagar":
        cr = re.sub(r"^(?:me\s+)?(?:pagar|pague|pago|paga)\s+(?:a\s+|o\s+|as\s+|os\s+)?", "", c.strip(), flags=re.I)
        cr = limpar(cr)
        if cr:
            s["credor"] = cr[:60].lower() if cr.lower().startswith(("conta", "boleto", "fatura")) else cr[:60]
        v = valor_de(c)
        if v:
            s["valor"] = v
        dv = d if re.search(r"venc|dia\s+\d|\d/\d|amanh|hoje|segunda|ter|quarta|quinta|sexta|sábado|sabado|domingo", c, re.I) else None
        if dv:
            s["vencimento"] = dv.isoformat()
    elif tipo in ("lembrete.criar", "estoque.repor", "cliente.ligar"):
        if tipo == "lembrete.criar":
            it = re.sub(r"^.*?\b(?:lembrar|lembre|lembra|lembrete|n[ãa]o\s+esquecer)\w*\s+(?:-?me\s+)?(?:de\s+|da\s+|do\s+|que\s+)?", "", c, flags=re.I)
        elif tipo == "estoque.repor":
            it = re.sub(r"^.*?\b(?:repor|rep[oô]e|reabastecer|encomendar|comprar mais|pedir mais|pedir)\s+(?:o\s+|a\s+|os\s+|as\s+)?(?:estoque\s+de\s+|estoque\s+do\s+|estoque\s+da\s+)?", "", c, flags=re.I)
            it = re.sub(r"\s+(ao|pro|para o)\s+fornecedor.*$", "", it, flags=re.I)
            q = re.search(r"\b(\d{1,4})\s*(?:un\w*|pe[çc]as?|caixas?|x)?\b", it)
            if q and not re.search(r"\d\s*h|\d:\d", it):
                s["quantidade"] = int(q.group(1)); it = it.replace(q.group(0), " ")
        else:
            it = re.sub(r"^.*?\b(?:ligar|retornar|telefonar)\s+", "", c, flags=re.I)
            p = pessoa_de(c)
            tid = re.search(r"\b((?:OF|LJ|EC)-\d+)\b", c, re.I)
            if tid:
                s["pedido"] = tid.group(1).upper()
            if p and not re.match(r"^(d[oae]s?|EC|OF|LJ)\b", p, re.I):
                s["pessoa"] = p
            elif tid:
                s["pessoa"] = "cliente do " + tid.group(1).upper()
        it = limpar(it)
        if tipo != "cliente.ligar" and it:
            s["item"] = it[:80]
        if tipo == "estoque.repor" and catalogo and s.get("item"):
            achados = M.buscar_produtos(catalogo, s["item"]) if any("preco" in c_ for c_ in catalogo) else []
            if not achados:
                n = M.norm(s["item"])
                achados = [c_ for c_ in catalogo if M.norm(c_.get("nome", "")) in n or n in M.norm(c_.get("nome", ""))]
            if achados:
                s["produto"] = achados[0].get("nome"); s["produto_id"] = achados[0].get("id")
                if "estoque" in achados[0]:
                    s["estoque_atual"] = achados[0]["estoque"]
        if d or h:
            dd = d or agora.date()
            hh = h or (HORA_PADRAO, 0, True)
            s["quando"] = ts_de(dd, hh[:2]); s["quando_declarado"] = "padrao" if not h else ("periodo" if h[2] else False)
            if s["quando"] < int(agora.timestamp() * 1000):  # "às 9" já passou hoje → amanhã
                s["quando"] += 86400000
    return s


def faltando(tipo, s):
    req = {"agenda.criar": ["pessoa", "data", "hora"], "financeiro.pagar": ["credor", "vencimento"], "lembrete.criar": ["item"],
           "estoque.repor": ["item"], "cliente.ligar": ["pessoa"]}[tipo]
    return [k for k in req if not s.get(k)]


FALTA_TXT = {"pessoa": "com quem", "data": "dia", "hora": "hora", "credor": "qual conta", "vencimento": "vencimento", "item": "o quê"}


def falta_txt(f):
    ws = [FALTA_TXT[x] for x in f]
    if ws == ["dia", "hora"]:
        return "falta dia e hora"
    return "falta " + (", ".join(ws[:-1]) + " e " + ws[-1] if len(ws) > 1 else ws[0])


def titulo(tipo, s):
    if tipo == "agenda.criar":
        a = M.cap(s.get("assunto") or "compromisso")
        return a + (f" com {s['pessoa']}" if s.get("pessoa") else "")
    if tipo == "financeiro.pagar":
        return M.cap(s.get("credor") or "conta")
    if tipo == "lembrete.criar":
        return M.cap(s.get("item") or "lembrete")
    if tipo == "estoque.repor":
        return "Repor " + (s.get("produto") or s.get("item") or "estoque") + (f" ({s['quantidade']} un.)" if s.get("quantidade") else "")
    return "Ligar para " + (s.get("pessoa") or "cliente")


def extrair(texto, agora_ms=None, catalogo=None):
    agora = agora_dt(agora_ms)
    out, ignorados = [], []
    for c in quebrar(texto):
        tp = tipo_de(c)
        if not tp:
            ignorados.append(c); continue
        s = slots_de(tp, c, agora, catalogo)
        out.append({"tipo": tp, "slots": s, "origem": c})
    return out, ignorados


def chaves(t):
    """Palavras que identificam a tarefa numa resposta (ex.: 'João', 'luz', 'leite')."""
    s = t["slots"]; base = " ".join(str(s.get(k) or "") for k in ("pessoa", "credor", "item", "produto"))
    stop = {"conta", "de", "da", "do", "das", "dos", "comprar", "pagar", "repor", "ligar", "para", "pro", "cliente", "o", "a", "boleto", "fatura"}
    return {w for w in re.findall(r"[a-z0-9]+", M.norm(base)) if w not in stop and len(w) >= 3}


class SecretarioMixin:
    # ------------------------------------------------------------ estado
    def sec_tarefas(self, tenant_id=None, chat=None):
        return [x for x in self.db.d.setdefault("tarefas", []) if (tenant_id is None or x["tenant"] == tenant_id) and (chat is None or x["chat"] == chat)]

    def sec_novo_id(self, tipo):
        self.db.d["sec_seq"] = self.db.d.get("sec_seq", 0) + 1
        return f"{PREFIXO[tipo]}-{self.db.d['sec_seq']:04d}"

    def sec_status(self, tk, st, **extra):
        tk["status"] = st; tk["atualizado"] = M.agora_ms(); tk.update(extra)
        tk.setdefault("historico", []).append({"status": st, "ts": tk["atualizado"]})

    def sec_avaliar(self, tk, agora_ms=None):
        """Decide o status pelo que já se sabe. Nunca executa pagamento."""
        agora_ms = agora_ms or M.agora_ms()
        s = tk["slots"]; f = faltando(tk["tipo"], s)
        tk["falta"] = f
        if f:
            if tk["status"] != "aguardando_dado":
                self.sec_status(tk, "aguardando_dado")
            return
        if tk["tipo"] == "agenda.criar":
            ini = ts_de(datetime.fromisoformat(s["data"]).date(), tuple(int(x) for x in s["hora"].split(":")))
            s["inicio"] = ini
            tk["disparo"] = max(ini - 30 * 60000, agora_ms + 60000) if ini > agora_ms else None
            tk["disparado"] = False
            self.sec_status(tk, "executada")
        elif tk["tipo"] == "financeiro.pagar":
            v = datetime.fromisoformat(s["vencimento"]).date()
            tk["disparo"] = max(ts_de(v, (9, 0)), agora_ms + 60000); tk["disparado"] = False
            if tk["status"] != "aguardando_ok":
                self.sec_status(tk, "aguardando_ok")
        else:
            if not s.get("quando"):
                s["quando"] = padrao_lembrete(agora_dt(agora_ms)); s["quando_declarado"] = "padrao"
            tk["disparo"] = s["quando"]; tk["disparado"] = False
            if tk["status"] != "executada":
                self.sec_status(tk, "executada")

    # ------------------------------------------------------------ textos
    def sec_linha_lista(self, tk):
        s = tk["slots"]
        if tk["falta"]:
            return f"{titulo(tk['tipo'], s)} — {falta_txt(tk['falta'])}."
        if tk["tipo"] == "agenda.criar":
            return f"{titulo(tk['tipo'], s)} — {fmt_data(s['data'])} às {fmt_hora(*[int(x) for x in s['hora'].split(':')])}."
        if tk["tipo"] == "financeiro.pagar":
            return f"{titulo(tk['tipo'], s)} — vence {fmt_data(s['vencimento'])}; pagamento só com o seu ok."
        return f"{titulo(tk['tipo'], s)} — posso lembrar {fmt_quando(s['quando'])}."

    def sec_card(self, tk):
        s = tk["slots"]; pid = f"#{tk['id']}"
        kb = []
        if tk["status"] == "aguardando_dado":
            txt = f"⏳ <b>{pid}</b> · {E(titulo(tk['tipo'], s))} — {E(falta_txt(tk['falta']))}. Aguardando sua resposta."
            kb = [[("❌ Cancelar", f"sec:x:{tk['id']}")]]
        elif tk["status"] == "cancelada":
            txt = f"🚫 <b>{pid}</b> · {E(titulo(tk['tipo'], s))} cancelada."
        elif tk["tipo"] == "agenda.criar":
            txt = (f"✅ <b>Tarefa concluída:</b> {E(titulo(tk['tipo'], s).lower() if s.get('assunto') else titulo(tk['tipo'], s))} agendada para "
                   f"{fmt_data(s['data'])} às {fmt_hora(*[int(x) for x in s['hora'].split(':')])}.\nProva: <b>{pid}</b> (agenda do Atende AI"
                   + (f"; aviso 30 min antes" if tk.get("disparo") else "") + ").")
            kb = [[("❌ Cancelar", f"sec:x:{tk['id']}")]]
        elif tk["tipo"] == "financeiro.pagar":
            if tk.get("pagoEm"):
                txt = f"✅ <b>{pid}</b> · {E(titulo(tk['tipo'], s))} marcada como paga por você em {M.data_hora(tk['pagoEm'])}."
            else:
                txt = (f"🧾 <b>{E(titulo(tk['tipo'], s))}</b> registrada" + (f" ({M.brl_c(s['valor'])})" if s.get("valor") else "") +
                       f", vence {fmt_data(s['vencimento'])}. O pagamento espera a sua confirmação.\nNão pago nada sem o seu ok: o Atende AI não movimenta dinheiro. "
                       f"Vou te lembrar {fmt_quando(tk['disparo'])}.\nProva: <b>{pid}</b> · status: aguardando seu ok")
                kb = [[("✅ Já paguei (marcar como paga)", f"sec:pago:{tk['id']}")], [("❌ Cancelar", f"sec:x:{tk['id']}")]]
        else:
            quando = fmt_quando(s["quando"]) + {"padrao": " (horário padrão, America/Sao_Paulo)", "periodo": " (horário do período: manhã 9h, tarde 15h, noite 20h)", True: " (horário padrão, America/Sao_Paulo)"}.get(s.get("quando_declarado"), "")
            extra = ""
            if tk["tipo"] == "estoque.repor" and s.get("estoque_atual") is not None:
                extra = f" Estoque atual: {s['estoque_atual']} un."
            if tk["tipo"] == "cliente.ligar" and s.get("pedido"):
                extra = f" Pedido {E(s['pedido'])}."
            nome = {"lembrete.criar": "Lembrete criado", "estoque.repor": "Reposição anotada", "cliente.ligar": "Ligação anotada"}[tk["tipo"]]
            txt = f"✅ <b>{nome}:</b> {E(titulo(tk['tipo'], s)[0].lower() + titulo(tk['tipo'], s)[1:])} {quando}.{extra}\nProva: <b>{pid}</b>"
            kb = [[("⏰ +1h", f"sec:adiar:{tk['id']}"), ("❌ Cancelar", f"sec:x:{tk['id']}")]]
        return txt, kb

    # ------------------------------------------------------------ fluxo
    def sec_tentar(self, cid, u, t, txt):
        """Devolve True se a mensagem do dono foi tratada pelo Secretário."""
        agora = M.agora_ms()
        lote = [x for x in self.sec_tarefas(t["id"], cid) if x["id"] in (u.get("sec_lote") or {}).get("ids", []) and x["status"] not in ("cancelada",)]
        if lote and agora - u["sec_lote"].get("ts", 0) < 6 * 3600000 and self.sec_completar(cid, u, t, txt, lote):
            return True
        itens, ignorados = extrair(txt, agora, t.get("catalogo"))
        if not itens:
            return False
        tks = []
        for it in itens:
            tk = {"id": self.sec_novo_id(it["tipo"]), "tenant": t["id"], "chat": cid, "tipo": it["tipo"], "slots": it["slots"], "origem": txt[:300],
                  "trecho": it["origem"][:160], "status": "rascunho", "criado": agora, "atualizado": agora, "historico": [{"status": "rascunho", "ts": agora}]}
            self.sec_avaliar(tk, agora)
            self.db.d.setdefault("tarefas", []).append(tk); tks.append(tk)
        u["sec_lote"] = {"ids": [x["id"] for x in tks], "ts": agora}
        ls = [f"📝 <b>Encontrei {len(tks)} pedido{'s' if len(tks) > 1 else ''}:</b>"] + [f"{n}. {E(self.sec_linha_lista(x))}" for n, x in enumerate(tks, 1)]
        if ignorados:
            ls.append("Não entendi: " + "; ".join(f"“{E(i[:60])}”" for i in ignorados) + ".")
        falt = [x for x in tks if x["falta"]]
        if falt:
            pedidos = []
            for x in falt:
                pedidos.append(f"{falta_txt(x['falta']).replace('falta ', '')} de “{E(titulo(x['tipo'], x['slots']))}”")
            ex = ", ".join(self.sec_exemplo(x) for x in falt)
            ls.append(f"\nPara concluir, me responda <b>numa mensagem só</b>: {'; '.join(pedidos)}.\nEx.: <i>{E(ex)}</i>")
        else:
            ls.append("\nTudo claro: confira os cartões abaixo.")
        self.tg.send(cid, "\n".join(ls))
        for x in tks:
            self.tg.send(cid, *self.sec_card(x))
        return True

    def sec_exemplo(self, x):
        s = x["slots"]
        if x["tipo"] == "agenda.criar":
            return f"{s.get('pessoa') or 'com o Pedro'} amanhã 15h"
        if x["tipo"] == "financeiro.pagar":
            return f"{(list(chaves(x)) or ['conta'])[0]} vence dia 12"
        return f"{(s.get('item') or 'isso')} hoje 18h"

    def sec_completar(self, cid, u, t, txt, lote):
        agora = M.agora_ms(); ag = agora_dt(agora)
        mexidas = []
        for c in quebrar(txt, juntar=False) if len(lote) > 1 else [txt]:
            alvo = None
            ws = set(re.findall(r"[a-z0-9]+", M.norm(c)))
            for x in lote:
                if chaves(x) & ws:
                    alvo = x; break
            if not alvo:
                abertas = [x for x in lote if x["status"] == "aguardando_dado"]
                if len(abertas) == 1:
                    alvo = abertas[0]
                elif re.search(r"venc", c, re.I):
                    alvo = next((x for x in abertas if x["tipo"] == "financeiro.pagar"), None)
                elif achar_hora(c):
                    alvo = next((x for x in abertas if x["tipo"] == "agenda.criar"), None)
            if not alvo:
                continue
            novo = slots_de(alvo["tipo"], (c if alvo["tipo"] != "financeiro.pagar" or re.search(r"venc", c, re.I) else "vence " + c), ag, t.get("catalogo"))
            s = alvo["slots"]; mudou = False
            for k in ("data", "hora", "vencimento", "valor", "quando", "quando_declarado"):
                if novo.get(k) is not None and novo.get(k) != s.get(k):
                    s[k] = novo[k]; mudou = True
            if alvo["tipo"] == "agenda.criar" and not s.get("pessoa") and novo.get("pessoa"):
                s["pessoa"] = novo["pessoa"]; mudou = True
            if alvo["tipo"] == "financeiro.pagar" and not s.get("credor") and novo.get("credor"):
                s["credor"] = novo["credor"]; mudou = True
            if mudou:
                if alvo["tipo"] in ("lembrete.criar", "estoque.repor", "cliente.ligar") and novo.get("quando"):
                    alvo["disparo"] = s["quando"]; alvo["disparado"] = False
                self.sec_avaliar(alvo, agora)
                if alvo not in mexidas:
                    mexidas.append(alvo)
        if not mexidas:
            return False
        for x in mexidas:
            self.tg.send(cid, *self.sec_card(x))
        rest = [x for x in lote if x["status"] == "aguardando_dado"]
        if rest:
            self.tg.send(cid, "Ainda falta: " + "; ".join(f"{falta_txt(x['falta']).replace('falta ', '')} de “{E(titulo(x['tipo'], x['slots']))}” (#{x['id']})" for x in rest) + ".")
        return True

    def sec_callback(self, cid, u, dado):
        _, acao, tid = dado.split(":", 2)
        tk = next((x for x in self.db.d.get("tarefas", []) if x["id"] == tid), None)
        if not tk or tk["chat"] != cid:
            return self.tg.send(cid, "Essa tarefa não é sua ou não existe mais.")
        if acao == "x":
            if tk["status"] == "cancelada":
                return self.tg.send(cid, f"#{tid} já estava cancelada.")
            if tk["tipo"] == "financeiro.pagar" and tk.get("pagoEm"):
                return self.tg.send(cid, f"#{tid} já foi marcada como paga.")
            self.sec_status(tk, "cancelada"); tk["disparo"] = None
            return self.tg.send(cid, *self.sec_card(tk))
        if acao == "pago":
            if tk["tipo"] != "financeiro.pagar" or tk["status"] != "aguardando_ok":
                return self.tg.send(cid, f"#{tid} não está aguardando confirmação de pagamento.")
            self.sec_status(tk, "executada", pagoEm=M.agora_ms(), pagoPor=cid); tk["disparo"] = None
            return self.tg.send(cid, *self.sec_card(tk))
        if acao in ("adiar", "feito"):
            if acao == "feito":
                tk["concluidoEm"] = M.agora_ms(); tk["disparo"] = None
                return self.tg.send(cid, f"👍 #{tid} · {E(titulo(tk['tipo'], tk['slots']))}: feito.")
            base = max(M.agora_ms(), tk.get("disparo") or 0) if not tk.get("disparado") else M.agora_ms()
            tk["disparo"] = base + 3600000; tk["disparado"] = False
            if tk["tipo"] in ("lembrete.criar", "estoque.repor", "cliente.ligar"):
                tk["slots"]["quando"] = tk["disparo"]; tk["slots"]["quando_declarado"] = False
            return self.tg.send(cid, f"⏰ #{tid} adiado: vou lembrar {fmt_quando(tk['disparo'])}.")

    def sec_vigiar(self, agora=None):
        agora = agora or M.agora_ms(); mudou = False
        for tk in self.db.d.get("tarefas", []):
            if not tk.get("disparo") or tk.get("disparado") or tk["disparo"] > agora or tk["status"] not in ("executada", "aguardando_ok"):
                continue
            s = tk["slots"]
            if tk["tipo"] == "agenda.criar":
                txt = f"⏰ <b>Daqui a pouco:</b> {E(titulo(tk['tipo'], s))} às {fmt_hora(*[int(x) for x in s['hora'].split(':')])} (#{tk['id']})."
                kb = None
            elif tk["tipo"] == "financeiro.pagar":
                txt = f"⏰ <b>Conta a pagar:</b> {E(titulo(tk['tipo'], s))} vence {fmt_data(s['vencimento'])} (#{tk['id']}). Continua aguardando o seu ok; eu não pago nada sozinho."
                kb = [[("✅ Já paguei (marcar como paga)", f"sec:pago:{tk['id']}")]]
            else:
                txt = f"⏰ <b>Lembrete:</b> {E(titulo(tk['tipo'], s))} (#{tk['id']})."
                if tk["tipo"] == "cliente.ligar" and s.get("pedido"):
                    txt += f" Pedido {E(s['pedido'])}."
                kb = [[("✅ Feito", f"sec:feito:{tk['id']}"), ("⏰ +1h", f"sec:adiar:{tk['id']}")]]
            r = self.tg.send(tk["chat"], txt, kb)
            tk["disparado"] = True; tk["disparadoEm"] = agora; mudou = True
            if r is None:
                self.sec_status(tk, "falhou", erro="Telegram não entregou o lembrete")
        return mudou

    # ------------------------------------------------------------ comandos
    def sec_listar(self, cid, t, qual):
        tks = self.sec_tarefas(t["id"])
        if qual == "agenda":
            xs = sorted([x for x in tks if x["tipo"] == "agenda.criar" and x["status"] in ("executada", "aguardando_dado")], key=lambda x: x["slots"].get("inicio") or 9e15)
            cab, vazio = "📅 <b>Agenda</b>", "Nada na agenda. Escreva, por exemplo: <code>Agendar reunião com João amanhã 15h</code>"
            linha = lambda x: f"• {E(titulo(x['tipo'], x['slots']))} — " + (f"{fmt_data(x['slots']['data'])} às {fmt_hora(*[int(v) for v in x['slots']['hora'].split(':')])}" if x["status"] == "executada" else E(falta_txt(x["falta"]))) + f" (#{x['id']})"  # noqa: E731
        elif qual == "contas":
            xs = sorted([x for x in tks if x["tipo"] == "financeiro.pagar" and x["status"] != "cancelada"], key=lambda x: (bool(x.get("pagoEm")), x["slots"].get("vencimento") or "9"))
            cab, vazio = "🧾 <b>Contas a pagar</b> (só mudam para paga com o seu ok)", "Nenhuma conta anotada. Ex.: <code>Pagar conta de luz dia 12</code>"
            linha = lambda x: f"• {E(titulo(x['tipo'], x['slots']))}" + (f" {M.brl_c(x['slots']['valor'])}" if x["slots"].get("valor") else "") + " — " + (("paga ✅" if x.get("pagoEm") else f"vence {fmt_data(x['slots']['vencimento'])} · aguardando seu ok") if x["slots"].get("vencimento") else E(falta_txt(x["falta"]))) + f" (#{x['id']})"  # noqa: E731
        else:
            xs = sorted([x for x in tks if x["tipo"] in ("lembrete.criar", "estoque.repor", "cliente.ligar") and x["status"] in ("executada", "aguardando_dado") and not x.get("concluidoEm")], key=lambda x: x["slots"].get("quando") or 9e15)
            cab, vazio = "⏰ <b>Lembretes e tarefas</b>", "Nenhum lembrete. Ex.: <code>Lembrar de comprar leite</code>"
            linha = lambda x: f"• {E(titulo(x['tipo'], x['slots']))} — " + (fmt_quando(x["slots"]["quando"]) + (" (já avisei)" if x.get("disparado") else "") if x["slots"].get("quando") else E(falta_txt(x["falta"]))) + f" (#{x['id']})"  # noqa: E731
        if not xs:
            return self.tg.send(cid, f"{cab}\n{vazio}")
        kb = [[(f"✅ Paguei {x['id']}", f"sec:pago:{x['id']}")] for x in xs if qual == "contas" and x["status"] == "aguardando_ok"][:6]
        return self.tg.send(cid, f"{cab}\n" + "\n".join(linha(x) for x in xs[:20]) + "\n\n<i>Escreva vários pedidos numa mensagem só: eu separo, pergunto o que falta e confirmo cada um.</i>", kb or None)


def tarefa_publica(x):
    return {k: v for k, v in x.items() if k not in ("chat",)}
