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
    return {
        "cliente": primeiro_nome(t.get("cliente")),
        "servico": " + ".join(_minusc(i["nome"]) for i in t.get("itens", [])) or "o serviço",
        "prazo": data_hora(t["prazo"]),
        "valor": faixa(t["total"]["min"], t["total"]["max"]) if t.get("total") else "a confirmar",
        "negocio": tenant["nome"],
        "veiculo": t.get("veiculo") or "seu " + rot["objeto"],
        "placa": t.get("placa") or "",
    }


def proximo_status(t: dict) -> str | None:
    i = STATUS.index(t["status"]) if t["status"] in STATUS else -1
    return STATUS[i + 1] if 0 <= i < len(STATUS) - 1 else None


def mudar_status(t: dict, tenant: dict, status: str, ts: int | None = None, pular_chat=(), posvenda_atraso_min: int = 1440) -> list[dict]:
    """Muda o status e devolve as mensagens automáticas que devem sair AGORA para o cliente."""
    ts = ts or agora_ms()
    t["status"] = status
    t.setdefault("historico", []).append({"status": status, "ts": ts})
    if status == "Aprovado":
        t["aprovadoEm"] = ts
    if status == "Pronto":
        t["prontoEm"] = ts
    if status == "Entregue":
        t["entregueEm"] = ts
        t.setdefault("prontoEm", ts)
        t.setdefault("valorFinal", round(valor_medio(t)))
    saem = []
    v = vars_ticket(t, tenant)
    for r in tenant["automacoes"]:
        if r["gatilho"] != status or not r["ativo"]:
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
