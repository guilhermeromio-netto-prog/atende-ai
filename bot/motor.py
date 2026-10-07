"""Atende AI — motor de regras (porta em Python do js/motor.js da demonstração).

Mesmo catálogo, mesmas intenções e perguntas: tudo vem de ../dados.json.
Sem dependências externas (somente a biblioteca padrão do Python 3.11+).
"""
from __future__ import annotations

import json
import os
import re
import time
import unicodedata
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

TZ = ZoneInfo("America/Sao_Paulo")
RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DADOS = json.load(open(os.path.join(RAIZ, "dados.json"), encoding="utf-8"))
STATUS = DADOS["status"]
PRIORIDADES = DADOS["prioridades"]
DIAS_CURTO = ["dom", "seg", "ter", "qua", "qui", "sex", "sáb"]


# ---------------------------------------------------------------- utilidades
def norm(s: str) -> str:
    s = unicodedata.normalize("NFD", str(s or "").lower())
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    return re.sub(r"\s+", " ", s).strip()


def cap(s: str) -> str:
    s = str(s or "").strip()
    return s[:1].upper() + s[1:]


def primeiro_nome(s: str) -> str:
    p = str(s or "").strip().split()
    return p[0] if p else "cliente"


def brl(v: float) -> str:
    v = int(round(v or 0))
    return "R$ " + f"{v:,}".replace(",", ".")


def faixa(a: float, b: float) -> str:
    return brl(a) if round(a) == round(b) else f"{brl(a)} a {brl(b)}"


def faixa_t(a: float, b: float) -> str:
    return "—" if not a and not b else faixa(a, b)


def dur(m: float) -> str:
    m = int(round(m or 0))
    if m < 60:
        return f"{m} min"
    h, r = divmod(m, 60)
    return f"{h}h{r:02d}" if r else f"{h}h"


def agora_ms() -> int:
    return int(time.time() * 1000)


def dt(ms: int) -> datetime:
    return datetime.fromtimestamp(ms / 1000, TZ)


def hora(ms: int) -> str:
    return dt(ms).strftime("%H:%M")


def data_hora(ms: int) -> str:
    d = dt(ms).date()
    hoje = datetime.now(TZ).date()
    if d == hoje:
        dia = "hoje"
    elif d == hoje + timedelta(days=1):
        dia = "amanhã"
    elif d == hoje - timedelta(days=1):
        dia = "ontem"
    else:
        dia = DIAS_CURTO[(dt(ms).weekday() + 1) % 7] + ", " + dt(ms).strftime("%d/%m")
    return f"{dia} às {hora(ms)}"


def restante(ms: int) -> str:
    neg = ms < 0
    mins = round(abs(ms) / 60000)
    d, rem = divmod(mins, 1440)
    h, m = divmod(rem, 60)
    s = f"{d}d {h}h" if d else (f"{h}h {m:02d}min" if h else f"{m}min")
    return ("estourado há " if neg else "faltam ") + s


def to_min(hhmm: str) -> int:
    h, _, m = str(hhmm).partition(":")
    return int(h) * 60 + int(m or 0)


def from_min(m: int) -> str:
    return f"{m // 60:02d}:{m % 60:02d}"


def _dia_semana(d: datetime) -> int:  # 0 = domingo, como no JS
    return (d.weekday() + 1) % 7


def soma_uteis(ms: int, minutos: int, horario: list) -> int:
    """Soma minutos úteis respeitando o horário [dom..sáb] = ["08:00","18:00"] | None."""
    if not horario or not any(horario):
        return ms + minutos * 60000
    d = dt(ms)
    resta = minutos
    guarda = 0
    while resta > 0 and guarda < 800:
        guarda += 1
        h = horario[_dia_semana(d)]
        if not h:
            d = (d + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
            continue
        ab, fe = to_min(h[0]), to_min(h[1])
        cur = d.hour * 60 + d.minute
        if cur < ab:
            d = d.replace(hour=ab // 60, minute=ab % 60, second=0, microsecond=0)
            continue
        if cur >= fe:
            d = (d + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
            continue
        usa = min(fe - cur, resta)
        d = d + timedelta(minutes=usa)
        resta -= usa
    return int(d.timestamp() * 1000)


def proximos_horarios(ms: int, horario: list, n: int = 3) -> list[int]:
    out = []
    d = (dt(ms) + timedelta(hours=1)).replace(minute=0, second=0, microsecond=0)
    guarda = 0
    while len(out) < n and guarda < 24 * 14:
        guarda += 1
        h = horario[_dia_semana(d)] if horario else None
        m = d.hour * 60
        if h and m >= to_min(h[0]) and m + 60 <= to_min(h[1]):
            out.append(int(d.timestamp() * 1000))
            d += timedelta(hours=3)
        else:
            d += timedelta(hours=1)
    return out


def template(txt: str, vars_: dict) -> str:
    return re.sub(r"\{(\w+)\}", lambda m: str(vars_.get(m.group(1), m.group(0))), str(txt or ""))


# ---------------------------------------------------------------- orçamento / SLA
def orcamento(segdef: dict, catalogo: list, servicos: list, veiculo: str = "") -> dict:
    fator, ajuste = 1.0, None
    v = norm(veiculo)
    for a in segdef.get("ajustes", []):
        if v and any(re.search(r"\b" + re.escape(p) + r"\b", v) for p in a["palavras"]):
            fator, ajuste = a["fator"], a["rotulo"]
    itens = []
    for sid in servicos:
        c = next((x for x in catalogo if x["id"] == sid), None)
        if not c:
            continue
        itens.append({"id": c["id"], "nome": c["nome"],
                      "pecasMin": round(c["pecasMin"] * fator), "pecasMax": round(c["pecasMax"] * fator),
                      "maoMin": c["maoMin"], "maoMax": c["maoMax"], "duracao": c["duracao"]})
    tot = {"min": sum(i["pecasMin"] + i["maoMin"] for i in itens), "max": sum(i["pecasMax"] + i["maoMax"] for i in itens)}
    return {"itens": itens, "total": tot, "duracao": sum(int(i["duracao"] or 0) for i in itens), "ajuste": ajuste}


def calc_prazo(tenant: dict, prio: str, inicio: int, duracao: int) -> int:
    sla = tenant["sla"].get(prio) or tenant["sla"]["media"]
    return soma_uteis(inicio, max(sla["conclusaoHoras"] * 60, duracao or 0), tenant["horario"])


def sla_estado(t: dict, agora: int | None = None) -> dict:
    agora = agora or agora_ms()
    if t.get("prontoEm"):
        ok = t["prontoEm"] <= t["prazo"]
        return {"cls": "ok" if ok else "erro", "texto": "SLA cumprido" if ok else "SLA estourado", "ativo": False}
    resta = t["prazo"] - agora
    janela = max(t["prazo"] - t["criado"], 1)
    if resta < 0:
        return {"cls": "erro", "texto": restante(resta), "ativo": True}
    if resta < janela * 0.25:
        return {"cls": "atencao", "texto": restante(resta), "ativo": True}
    return {"cls": "ok", "texto": restante(resta), "ativo": True}


def valor_medio(t: dict) -> float:
    tot = t.get("total") or {"min": 0, "max": 0}
    return (tot["min"] + tot["max"]) / 2


def _minusc(s: str) -> str:
    return s if re.match(r"^[A-ZÁÉÍÓÚ]{2}", s) else s[:1].lower() + s[1:]


def vars_ticket(t: dict, tenant: dict) -> dict:
    rot = DADOS["segmentos"][tenant["segmento"]]["rotulos"]
    if tenant["segmento"] == "ecommerce":
        return {"cliente": primeiro_nome(t.get("cliente")), "servico": itens_texto(t.get("itens", [])) or "seus itens",
                "prazo": data_hora(t["prazo"]), "valor": brl_c(t.get("totalFinal", valor_medio(t))), "negocio": tenant["nome"],
                "veiculo": "seu pedido", "placa": "", "pedido": t["id"], "rastreio": t.get("rastreio") or "não informado"}
    return {
        "cliente": primeiro_nome(t.get("cliente")),
        "servico": " + ".join(_minusc(i["nome"]) for i in t.get("itens", [])) or "o serviço",
        "prazo": data_hora(t["prazo"]),
        "valor": faixa(t["total"]["min"], t["total"]["max"]) if t.get("total") else "a confirmar",
        "negocio": tenant["nome"],
        "veiculo": t.get("veiculo") or "seu " + rot["objeto"],
        "placa": t.get("placa") or "",
        "pedido": t["id"], "rastreio": t.get("rastreio") or "",
    }


def status_de(seg: str, tipo: str | None = None) -> list:
    sd = DADOS["segmentos"].get(seg, {})
    if tipo in ("troca", "atendimento"):
        return sd.get("statusTroca", ["Novo", "Em análise", "Resolvido"])
    return sd.get("status", STATUS)


def proximo_status(t: dict) -> str | None:
    lista = status_de(t.get("seg", "oficina"), t.get("tipo"))
    i = lista.index(t["status"]) if t["status"] in lista else -1
    return lista[i + 1] if 0 <= i < len(lista) - 1 else None


def mudar_status(t: dict, tenant: dict, status: str, ts: int | None = None, pular_chat=(), posvenda_atraso_min: int = 1440) -> list[dict]:
    """Muda o status e devolve as mensagens automáticas que devem sair AGORA para o cliente."""
    ts = ts or agora_ms()
    t["status"] = status
    t.setdefault("historico", []).append({"status": status, "ts": ts})
    sd = DADOS["segmentos"][tenant["segmento"]]
    if t.get("tipo") in ("troca", "atendimento"):
        if status == "Resolvido":
            t["resolvidoEm"] = ts
        if status != "Novo":  # SLA de troca/atendimento = prazo para a 1ª análise
            t.setdefault("prontoEm", ts)
        return []
    if status == sd.get("statusAprovado", "Aprovado"):
        t["aprovadoEm"] = ts
        if tenant["segmento"] == "ecommerce":  # SLA de envio começa a contar no pagamento
            t["prazo"] = soma_dias_uteis(ts, envio_dias(tenant, t), tenant["horario"])
    if status == sd.get("statusPronto", "Pronto"):
        t["prontoEm"] = ts
    if status == "Entregue":
        t["entregueEm"] = ts
        t.setdefault("prontoEm", ts)
        t.setdefault("valorFinal", round(valor_medio(t)))
    saem = []
    v = vars_ticket(t, tenant)
    for r in tenant["automacoes"]:
        if r["gatilho"] != status or not r["ativo"] or r["id"] == "carrinho":
            continue
        texto = template(r["template"], v)
        estado, quando = "enviado", ts
        if r["id"] == "lembrete":
            estado = "agendado"
            quando = (t.get("agendamento") or ts + 3600000) - 2 * 3600000
        if r["id"] == "posvenda":
            quando = ts + posvenda_atraso_min * 60000
            estado = "agendado" if quando >= agora_ms() - 1000 else "enviado"
        ev = {"regra": r["id"], "nome": r["nome"], "ts": quando, "estado": estado, "texto": texto}
        t.setdefault("eventos", []).append(ev)
        if estado == "enviado" and r["id"] not in pular_chat:
            t.setdefault("chat", []).append({"de": "auto", "regra": r["id"], "texto": texto, "ts": quando})
            saem.append(ev)
    if status == "Em serviço":  # lembrete já não faz sentido: marca como cumprido
        for e in t.get("eventos", []):
            if e["regra"] == "lembrete" and e["estado"] == "agendado":
                e["estado"] = "cancelado"
    return saem


# ---------------------------------------------------------------- intenção / entidades
def detectar(segdef: dict, catalogo: list, texto: str):
    n = norm(texto)
    melhor, pts = None, 0.0
    for it in segdef["intents"]:
        s = 0.0
        for p in it["palavras"]:
            q = norm(p)
            if q in n:
                s += len(q.split(" ")) + 0.5
        if s > pts:
            melhor, pts = it, s
    melhor_c, pts_c = None, 0
    for c in catalogo:
        termos = list(c.get("palavras", [])) + [w for w in norm(c["nome"]).split(" ") if len(w) >= 5]
        s = sum(len(norm(p).split(" ")) for p in termos if norm(p) and norm(p) in n)
        if s > pts_c:
            melhor_c, pts_c = c, s
    if melhor and pts >= pts_c:
        # intenções do dados.json só valem se os serviços existirem no catálogo do negócio
        servs = [s for s in melhor["servicos"] if any(c["id"] == s for c in catalogo)]
        if servs:
            it = dict(melhor, servicos=servs, opcionais=[s for s in melhor["opcionais"] if any(c["id"] == s for c in catalogo)])
            return it, min(0.97, 0.6 + pts * 0.1)
    if melhor_c:
        return intent_de_item(melhor_c), min(0.9, 0.55 + pts_c * 0.1)
    return None, 0


def intent_de_item(c: dict) -> dict:
    return {"id": "cat-" + c["id"], "rotulo": c["nome"], "servicos": [c["id"]], "opcionais": [], "prioridade": "media",
            "explicacao": f'Temos "{c["nome"]}", com duração média de {dur(c["duracao"])}.'}


def extrair(segdef: dict, texto: str) -> dict:
    out = {}
    n = norm(texto)
    pl = re.search(r"\b([a-zA-Z]{3})-?(\d[a-zA-Z]\d{2}|\d{4})\b", texto)
    if pl:
        out["placa"] = (pl.group(1) + pl.group(2)).upper()
    for m in segdef.get("modelos", []):
        if re.search(r"(^|[^a-z0-9])" + re.escape(m) + r"([^a-z0-9]|$)", n):
            ano = re.search(r"\b(19[89]\d|20[0-3]\d)\b", n)
            nome = m.upper() if re.search(r"\d", m) else "-".join(cap(p) for p in m.split("-"))
            out["veiculo"] = nome + (" " + ano.group(1) if ano else "")
            break
    if re.search(r"urgent|socorro|guincho|parado|agora|hoje|preciso ja", n):
        out["urgencia"] = "alta"
    elif re.search(r"sem pressa|quando der|qualquer dia|tranquilo", n):
        out["urgencia"] = "baixa"
    elif re.search(r"semana|amanha", n):
        out["urgencia"] = "media"
    nm = re.search(r"(?:meu nome é|meu nome e|me chamo|aqui é o|aqui é a|sou o|sou a)\s+([A-Za-zÀ-ú]{2,}(?:\s+[A-Za-zÀ-ú]{2,})?)", texto, re.I)
    if nm:
        out["cliente"] = " ".join(cap(p) for p in nm.group(1).split())
    return out


def urgencia_de_resposta(txt: str):
    n = norm(txt)
    if "🚨" in txt or re.search(r"urgent|hoje|agora|\bja\b|socorro", n):
        return "alta"
    if "📅" in txt or re.search(r"semana|amanha", n):
        return "media"
    if "🙂" in txt or re.search(r"pressa|quando|tranquil|qualquer", n):
        return "baixa"
    return None


# ---------------------------------------------------------------- cadastro do dono
NUM = r"(\d{1,3}(?:\.\d{3})+(?:,\d{1,2})?|\d+(?:,\d{1,2})?)"
DIA = {"dom": 0, "seg": 1, "ter": 2, "qua": 3, "qui": 4, "sex": 5, "sab": 6}
PECA = re.compile(r"oleo|filtro|pastilha|disco|bateria|pneu|peca|lampada|palheta|correia|vela|tinta|chuveiro|torneira|cimento|kit|produto|material")


def _preco(s):
    return float(str(s).replace(".", "").replace(",", ".")) if s else None


def _eh_horario(n: str) -> bool:
    return bool(re.search(r"\b(seg|segunda|ter|terca|qua|quarta|qui|quinta|sex|sexta|sab|sabado|dom|domingo|feriado)", n)) and \
        bool(re.search(r"\d{1,2}\s*(h|:)", n) or re.search(r"fechad", n))


def parse_horario(chunk: str):
    n = norm(chunk)
    dias = []
    rg = re.search(r"\b(seg|ter|qua|qui|sex|sab|dom)\w*\.?\s*(?:a|ate|-|–)\s*(seg|ter|qua|qui|sex|sab|dom)", n)
    if rg:
        i, f = DIA[rg.group(1)], DIA[rg.group(2)]
        for _ in range(8):
            dias.append(i)
            if i == f:
                break
            i = (i + 1) % 7
    else:
        dias = [DIA[m] for m in re.findall(r"\b(seg|ter|qua|qui|sex|sab|dom)", n)]
    if re.search(r"\b(fechad|nao abr)", n):
        return {"dias": dias, "fechado": True} if dias else None
    h = re.search(r"(\d{1,2})(?:h|:)?(\d{2})?\s*h?\s*(?:as|a|ate|-|–)\s*(\d{1,2})(?:h|:)?(\d{2})?", n)
    if not dias or not h:
        return None
    ab = int(h.group(1)) * 60 + int(h.group(2) or 0)
    fe = int(h.group(3)) * 60 + int(h.group(4) or 0)
    if fe <= ab or fe > 24 * 60:
        return None
    return {"dias": dias, "abre": from_min(ab), "fecha": from_min(fe)}


def parse_servico(chunk: str, seg: str):
    resto = " " + chunk + " "
    out = {"pecasMin": 0, "pecasMax": 0, "maoMin": 0, "maoMax": 0, "duracao": 0}
    achou = False
    d = re.search(r"(\d+(?:[.,]\d+)?)\s*(?:horas|hora|hrs|hr|hs|h)(?![a-zà-ú])\s*(?:e\s*)?(\d{1,2})?\s*(?:minutos|min)?|(\d+)\s*(?:min|mins|minutos)\b|(\d+)\s*(?:dia|dias)\b", resto, re.I)
    if d:
        if d.group(1):
            out["duracao"] = round(float(d.group(1).replace(",", ".")) * 60) + int(d.group(2) or 0)
        elif d.group(3):
            out["duracao"] = int(d.group(3))
        elif d.group(4):
            out["duracao"] = int(d.group(4)) * 600
        resto = resto.replace(d.group(0), " ", 1)

    def faixa_re(rot):
        return re.compile(rot + r"\s*(?:de|:|=)?\s*(?:r\$\s*)?" + NUM + r"(?:\s*(?:a|até|ate|-|–)\s*(?:r\$\s*)?" + NUM + r")?", re.I)

    rp = faixa_re(r"(?:peças|pecas|peça|peca|produtos?|material|materiais)").search(resto)
    if rp:
        out["pecasMin"] = _preco(rp.group(1)); out["pecasMax"] = _preco(rp.group(2)) or out["pecasMin"]
        resto = resto.replace(rp.group(0), " ", 1); achou = True
    rm = faixa_re(r"(?:mão de obra|mao de obra|mão-de-obra|instalação|instalacao|serviço|servico|montagem)").search(resto)
    if rm:
        out["maoMin"] = _preco(rm.group(1)); out["maoMax"] = _preco(rm.group(2)) or out["maoMin"]
        resto = resto.replace(rm.group(0), " ", 1); achou = True
    if not (rp and rm):
        g = re.search(r"r\$\s*" + NUM + r"(?:\s*(?:a|até|ate|-|–)\s*(?:r\$\s*)?" + NUM + r")?", resto, re.I)
        if not g:
            g = re.search(r"\b" + NUM + r"\s*(?:reais)?(?:\s*(?:a|até|ate|-|–)\s*" + NUM + r")?\s*(?:reais)?", resto, re.I)
        if g:
            a = _preco(g.group(1)); b = _preco(g.group(2)) or a
            if a and a >= 5:
                nn = norm(resto)
                if rm:
                    out["pecasMin"], out["pecasMax"] = a, b
                elif rp:
                    out["maoMin"], out["maoMax"] = a, b
                elif PECA.search(nn) or (seg == "loja" and not re.search(r"instala|entrega|frete|corte|montag", nn)):
                    out["pecasMin"], out["pecasMax"] = a, b
                else:
                    out["maoMin"], out["maoMax"] = a, b
                resto = resto.replace(g.group(0), " ", 1); achou = True
    if not achou and not out["duracao"]:
        return None
    nome = re.sub(r"r\$", " ", resto, flags=re.I)
    nome = re.sub(r"\b(reais|custa|custando|cobro|cobramos|valor|preço|preco|por volta de|cerca de|em média|em media|leva|demora|dura|tempo|aprox\.?|aproximadamente|mais)\b", " ", nome, flags=re.I)
    nome = re.sub(r"[:=|•·()]", " ", nome)
    nome = re.sub(r"\s[-–]\s", " ", nome)
    nome = re.sub(r"\s+", " ", nome).strip()
    nome = re.sub(r"^(e|a|o|de|faço|faco|fazemos|temos|vendo|vendemos|também|tambem)\s+", "", nome, flags=re.I)
    nome = re.sub(r"\s+(de|por|a|e|com|em|no|na)$", "", nome, flags=re.I)
    nome = re.sub(r"[,.;-]+$", "", nome).strip()
    if len(nome) < 3:
        return None
    out["nome"] = cap(nome)
    out["palavras"] = [w for w in norm(nome).split(" ") if len(w) >= 4]
    for k in ("pecasMin", "pecasMax", "maoMin", "maoMax"):
        out[k] = int(round(out[k] or 0))
    return out


def parse_dono(texto: str, seg: str) -> dict:
    res = {"nome": None, "servicos": [], "horarios": []}
    nm = re.search(r"(?:se chama|chama-se|nome (?:dela |dele |do negócio |da empresa |da loja |da oficina )?(?:é|e)|^\s*nome\s*:)\s*[\"“']?([^\"”'\n;.!]+)", texto, re.I)
    if nm:
        res["nome"] = re.sub(r"\s+", " ", nm.group(1).strip())
    for b in [x.strip() for x in re.split(r"\n|;", texto) if x.strip()]:
        n = norm(b)
        if nm and nm.group(0).strip()[:12] in b:
            continue
        if _eh_horario(n):
            for p in re.split(r",|\s+e\s+(?=(?:seg|ter|qua|qui|sex|s[áa]b|dom))", b, flags=re.I):
                h = parse_horario(p)
                if h:
                    res["horarios"].append(h)
            continue
        qtd = len(re.findall(r"r\$", b, re.I))
        partes = re.split(r",\s*(?=[A-Za-zÀ-ú])|\s+e\s+(?=[A-Za-zÀ-ú]+[^$]*r\$)", b, flags=re.I) if qtd >= 2 and not re.search(r"m[ãa]o de obra|pe[çc]as|instala", b, re.I) else [b]
        for p in partes:
            s = parse_servico(p, seg)
            if s:
                res["servicos"].append(s)
    return res


# ================================================================ Loja virtual (ecommerce)
def brl_c(v: float) -> str:
    """R$ com centavos: 89.9 -> R$ 89,90"""
    v = round(float(v or 0) + 1e-9, 2)
    inteiro, cent = divmod(round(v * 100), 100)
    return "R$ " + f"{inteiro:,}".replace(",", ".") + f",{cent:02d}"


def itens_texto(itens: list) -> str:
    return " + ".join(f'{i.get("qtd", 1)}x {i["nome"]}' if "qtd" in i else i["nome"] for i in itens)


def politicas_padrao() -> dict:
    return json.loads(json.dumps(DADOS["segmentos"]["ecommerce"]["politicas"]))


def envio_dias(tenant: dict, t: dict | None = None) -> int:
    pol = tenant.get("politicas") or politicas_padrao()
    base = int(pol.get("envioDiasUteis", 1) or 1)
    if t and t.get("itens"):
        base = max([base] + [int(i.get("envioDias") or 0) for i in t["itens"]])
    return base


def soma_dias_uteis(ms: int, n: int, horario: list) -> int:
    """Fim do expediente do n-ésimo dia útil depois de ms (dias com horário de funcionamento)."""
    d = dt(ms)
    contados, guarda = 0, 0
    while guarda < 60:
        guarda += 1
        d = (d + timedelta(days=1)).replace(hour=12, minute=0, second=0, microsecond=0)
        h = horario[_dia_semana(d)] if horario else ["18:00", "18:00"]
        if h:
            contados += 1
            if contados >= max(1, n):
                fe = to_min(h[1])
                return int(d.replace(hour=fe // 60, minute=fe % 60).timestamp() * 1000)
    return ms + n * 86400000


REGIAO_UF = {"SP": "SP", "RJ": "Sudeste", "MG": "Sudeste", "ES": "Sudeste"}


def regiao_cep(cep: str, uf: str | None = None) -> str:
    if uf:
        return REGIAO_UF.get(uf.upper(), "Outros")
    c = re.sub(r"\D", "", cep or "")
    if not c:
        return "Outros"
    return "SP" if c[0] in "01" else ("Sudeste" if c[0] in "23" else "Outros")


def achar_cep(texto: str):
    m = re.search(r"\b(\d{5})-?(\d{3})\b", texto or "")
    return m.group(1) + "-" + m.group(2) if m else None


def viacep(cep: str):
    """Consulta pública opcional (cidade/UF). Falha silenciosa: cai na regra do 1º dígito."""
    if os.environ.get("ATENDE_SEM_REDE"):
        return None
    try:
        import urllib.request
        with urllib.request.urlopen(f"https://viacep.com.br/ws/{re.sub(r'[^0-9]', '', cep)}/json/", timeout=4) as r:
            d = json.loads(r.read().decode())
        return None if d.get("erro") else {"cidade": d.get("localidade"), "uf": d.get("uf")}
    except Exception:
        return None


def calc_frete(pol: dict, subtotal: float, regiao: str) -> dict:
    f = pol.get("frete", {})
    dias = int((f.get("prazosDias") or {}).get(regiao, 5) or 5)
    if f.get("gratisAcima") is not None and f.get("gratisAcima") != "" and subtotal >= float(f["gratisAcima"]):
        return {"valor": 0.0, "dias": dias, "gratis": True}
    if f.get("tipo") == "fixo":
        return {"valor": float(f.get("fixo") or 0), "dias": dias, "gratis": False}
    v = (f.get("regioes") or {}).get(regiao)
    if v is None:
        v = f.get("fixo") or 0
    return {"valor": float(v), "dias": dias, "gratis": False}


def texto_politicas(pol: dict) -> str:
    f, pg = pol.get("frete", {}), pol.get("pagamento", {})
    ls = []
    if f.get("tipo") == "fixo":
        ls.append(f"🚚 Frete fixo {brl_c(f.get('fixo') or 0)}")
    else:
        reg = f.get("regioes") or {}
        pz = f.get("prazosDias") or {}
        ls.append("🚚 Frete por região: " + "; ".join(f"{k} {brl_c(v)} ({pz.get(k, '?')} dias)" for k, v in reg.items()))
    if f.get("gratisAcima") not in (None, ""):
        ls.append(f"🎁 Frete grátis acima de {brl_c(f['gratisAcima'])}" if float(f["gratisAcima"]) > 0 else "🎁 Frete grátis para todo o Brasil")
    ls.append(f"📦 Envio em até {pol.get('envioDiasUteis', 1)} dia(s) útil(eis) após o pagamento")
    pag = []
    if pg.get("pixDescontoPct"):
        pag.append(f"Pix com {pg['pixDescontoPct']}% de desconto")
    else:
        pag.append("Pix")
    if pg.get("parcelas"):
        pag.append(f"cartão em até {pg['parcelas']}x")
    ls.append("💳 " + ", ".join(pag))
    ls.append("🔁 " + (pol.get("troca") or ""))
    return "\n".join(ls)


STOP = set("vcs voces voce vc tem tens tenho quero queria comprar compra um uma uns umas o a os as de do da dos das pra para por preco "
           "quanto custa custam valor estoque disponivel ai e me ver mostrar produto produtos algum alguma qual quais com sem no na em "
           "isso esse essa este esta sim nao ola oi bom dia boa tarde noite gostaria saber vende vendem tem? ola, por favor".split())
NUMS = {"um": 1, "uma": 1, "dois": 2, "duas": 2, "tres": 3, "quatro": 4, "cinco": 5, "seis": 6, "dez": 10}


def lev(a: str, b: str) -> int:
    if abs(len(a) - len(b)) > 2:
        return 3
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb)))
        prev = cur
    return prev[-1]


def _sing(w: str) -> str:
    return w[:-1] if len(w) > 4 and w.endswith("s") else w


def buscar_produtos(catalogo: list, texto: str) -> list:
    n = norm(texto)
    toks = [_sing(w) for w in re.findall(r"[a-z0-9\-]+", n) if w not in STOP and not w.isdigit() and len(w) >= 3]
    res = []
    for c in catalogo:
        termos = set()
        for p in [c["nome"]] + list(c.get("palavras", [])):
            termos.update(_sing(w) for w in re.findall(r"[a-z0-9\-]+", norm(p)) if len(w) >= 3 and w not in STOP)
        sc = 0
        for p in c.get("palavras", []):
            if " " in p and norm(p) in n:
                sc += 3
        for q in toks:
            best = 0
            for w in termos:
                if q == w:
                    best = 3; break
                if len(q) >= 4 and len(w) >= 4 and (w.startswith(q) or q.startswith(w)):
                    best = max(best, 2)
                elif len(q) >= 4 and len(w) >= 4 and lev(q, w) <= (2 if len(q) >= 7 else 1):
                    best = max(best, 2)
            sc += best
        if sc >= 2:
            res.append((c, sc))
    res.sort(key=lambda x: (-x[1], x[0]["estoque"] <= 0))
    if res:
        topo = res[0][1]
        res = [r for r in res if r[1] >= max(2, topo * 0.6)]
    return res


def achar_qtd(texto: str):
    n = norm(texto)
    m = re.search(r"\b(\d{1,2})\s*(?:x|un|unid|unidades|pecas)?\b(?!\s*(?:dias|%|reais|mil))", n)
    if m and not achar_cep(texto) and int(m.group(1)) > 0:
        return int(m.group(1))
    for k, v in NUMS.items():
        if re.search(r"\b" + k + r"\b", n):
            return v
    return None


def resumo_carrinho(catalogo: list, carrinho: dict, pol: dict, regiao: str | None, pagamento: str | None) -> dict:
    itens = []
    for pid, q in carrinho.items():
        c = next((x for x in catalogo if x["id"] == pid), None)
        if c and q > 0:
            itens.append({"id": pid, "nome": c["nome"], "qtd": q, "preco": float(c["preco"]), "envioDias": c.get("envioDias", 1),
                          "pecasMin": float(c["preco"]) * q, "pecasMax": float(c["preco"]) * q, "maoMin": 0, "maoMax": 0, "duracao": 0})
    sub = round(sum(i["preco"] * i["qtd"] for i in itens), 2)
    fr = calc_frete(pol, sub, regiao) if regiao else None
    desc = round(sub * float(pol.get("pagamento", {}).get("pixDescontoPct") or 0) / 100, 2) if pagamento == "pix" else 0.0
    total = round(sub + (fr["valor"] if fr else 0) - desc, 2)
    return {"itens": itens, "subtotal": sub, "frete": fr, "desconto": desc, "total": total}


def parse_produto(chunk: str):
    resto = " " + chunk + " "
    out = {"estoque": None, "envioDias": None}
    e = re.search(r"(?:estoque|qtd|quantidade)\s*:?\s*(\d+)|(\d+)\s*(?:unidades|unid|un|pe[çc]as|em estoque)\b", resto, re.I)
    if e:
        out["estoque"] = int(e.group(1) or e.group(2)); resto = resto.replace(e.group(0), " ", 1)
    v = re.search(r"(?:entrega|envio|prazo|despacho|postagem|envia)\s*(?:em|de)?\s*(\d+)\s*(?:dias?|d)\b(?:\s*[uú]teis)?", resto, re.I)
    if v:
        out["envioDias"] = int(v.group(1)); resto = resto.replace(v.group(0), " ", 1)
    g = re.search(r"r\$\s*" + NUM, resto, re.I) or re.search(r"\b" + NUM + r"\s*reais", resto, re.I) or re.search(r"\b" + NUM + r"\b", resto)
    if not g:
        return None
    preco = _preco(g.group(1))
    if not preco or preco < 1:
        return None
    resto = resto.replace(g.group(0), " ", 1)
    nome = re.sub(r"r\$|\breais\b|\b(custa|por|valor|pre[çc]o|vendo|tenho|cada)\b", " ", resto, flags=re.I)
    nome = re.sub(r"[:=|•·()]", " ", nome)
    nome = re.sub(r"\s+", " ", nome).strip(" ,.;-")
    nome = re.sub(r"\s+(de|por|a|e|com|em)$", "", nome, flags=re.I)
    if len(nome) < 3:
        return None
    out.update({"nome": cap(nome), "preco": round(preco, 2), "palavras": [w for w in norm(nome).split(" ") if len(w) >= 4]})
    return out


REG_NOMES = r"(sp|sao paulo|capital|sudeste|outros|outras regioes|demais regioes|demais|resto do brasil|brasil)"


def _reg(nome: str) -> str:
    return "SP" if nome in ("sp", "sao paulo", "capital") else ("Sudeste" if nome == "sudeste" else "Outros")


def parse_ecom(texto: str) -> dict:
    """Produtos e políticas da loja virtual a partir do texto do dono."""
    res = {"nome": None, "produtos": [], "politicas": [], "mudancas": {}}
    nm = re.search(r"(?:se chama|chama-se|nome (?:da loja |do negócio |da empresa )?(?:é|e)|^\s*nome\s*:)\s*[\"“']?([^\"”'\n;.!]+)", texto, re.I)
    if nm:
        res["nome"] = re.sub(r"\s+", " ", nm.group(1).strip())
    ch = {}
    for b in [x.strip() for x in re.split(r"\n|;|\.\s+(?=\S)", texto) if x.strip()]:
        n = norm(b)
        if nm and nm.group(0).strip()[:12] in b:
            continue
        regs = re.findall(r"(?:frete\s+)?(?:para |pra )?" + REG_NOMES + r"\s*:?\s*(?:r\$\s*)?" + NUM + r"(?:\s*(?:reais)?\s*(?:em\s*)?(\d+)\s*dias?)?", n)
        if "frete" in n or (regs and "estoque" not in n):
            f = ch.setdefault("frete", {})
            g = re.search(r"frete gratis (?:acima|a partir) de (?:r\$\s*)?" + NUM, n)
            if g:
                f["gratisAcima"] = _preco(g.group(1)); res["politicas"].append(f"🎁 Frete grátis acima de {brl_c(f['gratisAcima'])}")
            elif re.search(r"frete gratis", n) and not regs:
                f["gratisAcima"] = 0; res["politicas"].append("🎁 Frete grátis para todo o Brasil")
            fx = re.search(r"frete (?:fixo|unico)\s*(?:de)?\s*(?:r\$\s*)?" + NUM, n)
            if fx:
                f["tipo"] = "fixo"; f["fixo"] = _preco(fx.group(1)); res["politicas"].append(f"🚚 Frete fixo {brl_c(f['fixo'])}")
            if regs:
                f["tipo"] = "regiao"
                for nome_r, val, dias in regs:
                    r = _reg(nome_r)
                    f.setdefault("regioes", {})[r] = _preco(val)
                    if dias:
                        f.setdefault("prazosDias", {})[r] = int(dias)
                    res["politicas"].append(f"🚚 Frete {r}: {brl_c(_preco(val))}" + (f" · {dias} dias" if dias else ""))
            continue
        if re.search(r"\bpix\b|cartao|parcel|chave|link de pagamento|boleto", n):
            pg = ch.setdefault("pagamento", {})
            d = re.search(r"pix\D{0,25}?(\d{1,2})\s*%", n) or re.search(r"(\d{1,2})\s*%\D{0,25}pix", n)
            if d:
                pg["pixDescontoPct"] = int(d.group(1)); res["politicas"].append(f"💸 Pix com {pg['pixDescontoPct']}% de desconto")
            pc = re.search(r"(\d{1,2})\s*x\b", n) or re.search(r"ate (\d{1,2}) vezes", n)
            if pc:
                pg["parcelas"] = int(pc.group(1)); res["politicas"].append(f"💳 Cartão em até {pg['parcelas']}x")
            ck = re.search(r"chave(?:\s+pix)?\s*(?:é|e|:|=)?\s*(.+)$", b, re.I)
            if ck and len(ck.group(1).strip()) >= 5:
                pg["pixChave"] = ck.group(1).strip()[:120]; res["politicas"].append("🔑 Chave Pix cadastrada")
            lk = re.search(r"(https?://\S+)", b)
            if lk and not ck:
                pg["linkCartao"] = lk.group(1)[:200]; res["politicas"].append("🔗 Link de pagamento cadastrado")
            continue
        if re.search(r"\btroca|devolu|arrependimento", n) and not re.search(r"r\$", n):
            ch["troca"] = cap(b.strip())[:400]; res["politicas"].append("🔁 Política de troca atualizada")
            continue
        ev = re.search(r"(?:envio|despacho|postagem|enviamos|postamos|despachamos)\D{0,15}(\d+)\s*dias?", n)
        if ev and not re.search(r"r\$|estoque", n):
            ch["envioDiasUteis"] = int(ev.group(1)); res["politicas"].append(f"📦 Envio em até {ch['envioDiasUteis']} dia(s) útil(eis)")
            continue
        p = parse_produto(b)
        if p:
            res["produtos"].append(p)
    res["mudancas"] = ch
    return res


def aplicar_politicas(pol: dict, ch: dict) -> None:
    for k, v in ch.items():
        if isinstance(v, dict):
            alvo = pol.setdefault(k, {})
            for kk, vv in v.items():
                if isinstance(vv, dict):
                    alvo.setdefault(kk, {}).update(vv)
                else:
                    alvo[kk] = vv
        else:
            pol[k] = v
