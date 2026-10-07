#!/usr/bin/env python3
"""Atende AI — bot de teste no Telegram (long polling), mesmo motor da demonstração.

- Sem dependências: só a biblioteca padrão do Python 3.11+.
- Token: variável de ambiente TELEGRAM_BOT_TOKEN (nunca gravada em arquivo nem no log).
- Dados: bot/data/db.json (fora do git).
- API somente leitura em 127.0.0.1:8787 (exposta por túnel opcional) com chave por negócio.
"""
from __future__ import annotations

import html
import json
import os
import re
import secrets
import sys
import threading
import time
import traceback
import urllib.error
import urllib.parse
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import motor as M  # noqa: E402

AQUI = os.path.dirname(os.path.abspath(__file__))
DATA = os.environ.get("ATENDE_DATA") or os.path.join(AQUI, "data")
os.makedirs(DATA, exist_ok=True)
DB_PATH = os.path.join(DATA, "db.json")
TUNNEL_FILE = os.path.join(DATA, "tunnel_url.txt")
API_PORT = int(os.environ.get("ATENDE_API_PORT", "8787"))
POSVENDA_MIN = int(os.environ.get("ATENDE_POSVENDA_MIN", "2"))  # modo teste: pós-venda 2 min depois da entrega
BOT_USER = os.environ.get("ATENDE_BOT_USER", "Applojas10_bot")
PAGES = "https://guilhermeromio-netto-prog.github.io/atende-ai/"
CORS_OK = {"https://guilhermeromio-netto-prog.github.io", "http://localhost:8765", "http://127.0.0.1:8765"}
E = html.escape


def log(*a):
    msg = " ".join(str(x) for x in a)
    tok = TG.token if "TG" in globals() and TG and TG.token else None
    if tok:
        msg = msg.replace(tok, "***")
    print(time.strftime("%Y-%m-%d %H:%M:%S"), msg, flush=True)


# ============================================================ Telegram
class Telegram:
    def __init__(self, token: str):
        self.token = re.sub(r"\s+", "", token or "")  # remove qualquer espaço/quebra de linha
        self.base = "https://api.telegram.org/bot" + self.token + "/"

    def call(self, method: str, _t: int = 40, **params):
        data = json.dumps({k: v for k, v in params.items() if v is not None}).encode()
        req = urllib.request.Request(self.base + method, data=data, headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=_t) as r:
                res = json.loads(r.read().decode())
        except urllib.error.HTTPError as e:
            corpo = e.read().decode(errors="replace")[:300]
            log("Telegram", method, "HTTP", e.code, corpo)
            return None
        except Exception as e:  # rede instável: o laço principal tenta de novo
            log("Telegram", method, "erro", type(e).__name__)
            return None
        return res.get("result") if res.get("ok") else None

    def send(self, chat_id, texto, teclado=None):
        markup = None
        if teclado:
            markup = {"inline_keyboard": [[{"text": r, "callback_data": d} for r, d in linha] for linha in teclado]}
        return self.call("sendMessage", chat_id=chat_id, text=texto[:4000], parse_mode="HTML",
                         disable_web_page_preview=True, reply_markup=markup)


def linhas(botoes, por_linha=1):
    """[(rotulo, dado), ...] -> teclado em linhas"""
    return [botoes[i:i + por_linha] for i in range(0, len(botoes), por_linha)]


# ============================================================ Banco (JSON)
class DB:
    def __init__(self, path):
        self.path = path
        self.lock = threading.RLock()
        if os.path.exists(path):
            self.d = json.load(open(path, encoding="utf-8"))
        else:
            self.d = {"versao": 1, "offset": 0, "seq": 3000, "tenants": {}, "usuarios": {}, "tickets": []}
            for slug, seg in (("oficina-pista-livre", "oficina"), ("casa-forte", "loja")):
                self.d["tenants"][slug] = novo_tenant(slug, M.DADOS["segmentos"][seg]["negocio"]["nome"], seg, True)
            self.save()

    def save(self):
        with self.lock:
            tmp = self.path + ".tmp"
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(self.d, f, ensure_ascii=False)
            os.replace(tmp, self.path)

    def user(self, chat_id, frm=None):
        u = self.d["usuarios"].setdefault(str(chat_id), {"modo": "cliente", "tenant": None, "dono_de": [], "conv": None})
        if frm:
            u["nome"] = (frm.get("first_name") or "") + (" " + frm["last_name"] if frm.get("last_name") else "")
            u["username"] = frm.get("username")
        return u

    def tenant(self, slug):
        return self.d["tenants"].get(slug)

    def ticket(self, tid):
        return next((t for t in self.d["tickets"] if t["id"] == tid), None)


def novo_tenant(slug, nome, seg, exemplo=True):
    sd = M.DADOS["segmentos"][seg]
    return {"id": slug, "nome": nome, "segmento": seg, "donos": [], "codigo": secrets.token_hex(3).upper(),
            "chave_api": secrets.token_urlsafe(18), "criado": M.agora_ms(),
            "horario": json.loads(json.dumps(sd["negocio"]["horario"])),
            "catalogo": json.loads(json.dumps(sd["catalogo"])) if exemplo else [],
            "automacoes": json.loads(json.dumps(M.DADOS["automacoes"][seg])),
            "sla": json.loads(json.dumps(M.DADOS["sla"][seg]))}


def slugify(s):
    return re.sub(r"[^a-z0-9]+", "-", M.norm(s)).strip("-")[:28] or "negocio"


# ============================================================ IA opcional (Grok)
class IA:
    def __init__(self):
        self.key = None
        self.ok = False
        self.modelo = os.environ.get("XAI_MODEL", "grok-3-mini")
        try:
            d = json.load(open("/home/box/agent-data/box-secrets.json"))
            self.key = (d.get("card", {}).get("XAI_API_KEY") or os.environ.get("XAI_API_KEY") or "").strip() or None
        except Exception:
            self.key = (os.environ.get("XAI_API_KEY") or "").strip() or None

    def _post(self, mensagens, max_tokens=120):
        req = urllib.request.Request("https://api.x.ai/v1/chat/completions",
                                     data=json.dumps({"model": self.modelo, "messages": mensagens, "max_tokens": max_tokens, "temperature": 0}).encode(),
                                     headers={"Content-Type": "application/json", "Authorization": "Bearer " + self.key})
        with urllib.request.urlopen(req, timeout=20) as r:
            return json.loads(r.read().decode())["choices"][0]["message"]["content"]

    def testar(self):
        if not self.key:
            log("IA: sem XAI_API_KEY; usando só regras")
            return
        try:
            self._post([{"role": "user", "content": "Responda só OK"}], 5)
            self.ok = True
            log("IA: Grok disponível (", self.modelo, ")")
        except urllib.error.HTTPError as e:
            log("IA: Grok indisponível, HTTP", e.code, "→ usando só regras")
        except Exception as e:
            log("IA: Grok indisponível,", type(e).__name__, "→ usando só regras")

    def classificar(self, texto, catalogo):
        """Devolve id do item do catálogo ou None. Nunca define preço: preço sempre vem do catálogo."""
        if not self.ok:
            return None
        lista = "\n".join(f'{c["id"]}: {c["nome"]}' for c in catalogo)
        try:
            r = self._post([{"role": "system", "content": "Classifique o relato do cliente em UM id do catálogo. Responda só o id ou NENHUM."},
                            {"role": "user", "content": f"Catálogo:\n{lista}\n\nRelato: {texto}"}], 20)
            rid = r.strip().split()[0].strip(".,;:\"'")
            return rid if any(c["id"] == rid for c in catalogo) else None
        except Exception as e:
            log("IA: falha na classificação,", type(e).__name__)
            return None


# ============================================================ Bot
CMD_CLIENTE = [("start", "Começar o atendimento"), ("trocar", "Escolher outro negócio"), ("nova", "Nova conversa"),
               ("dono", "Sou dono de um negócio"), ("ajuda", "Como funciona")]
CMD_DONO = [("painel", "Resumo e indicadores"), ("pedidos", "Pedidos em aberto"), ("catalogo", "Ver catálogo"),
            ("horario", "Ver horário"), ("link", "Link para seus clientes"), ("conectar", "Ligar o dashboard web"),
            ("codigo", "Código para outro atendente"), ("cliente", "Testar como cliente"), ("dono", "Voltar ao modo dono"),
            ("ajuda", "Comandos")]
ETAPA_TXT = {"problema": "entendendo o problema", "pergunta": "coletando dados", "orcado": "orçamento enviado",
             "agendar": "escolhendo horário", "fim": "agendado", "humano": "com atendente"}


class Bot:
    def __init__(self, tg: Telegram, db: DB, ia: IA):
        self.tg, self.db, self.ia = tg, db, ia

    # ---------------------------------------------------------------- utilidades
    def link(self, slug):
        return f"https://t.me/{BOT_USER}?start={slug}"

    def novo_id(self, t):
        self.db.d["seq"] += 1
        return ("OF-" if t["segmento"] == "oficina" else "LJ-") + str(self.db.d["seq"])

    def avisar_donos(self, tenant, texto, teclado=None):
        for cid in tenant.get("donos", []):
            self.tg.send(cid, texto, teclado)

    def resumo_ticket(self, t, tenant):
        s = M.sla_estado(t)
        icone = {"ok": "🟢", "atencao": "🟡", "erro": "🔴"}[s["cls"]]
        rot = M.DADOS["segmentos"][tenant["segmento"]]["rotulos"]
        partes = [f"<b>Pedido {t['id']}</b> · {E(t['status'])}", f"👤 {E(t.get('cliente') or 'Cliente')}"]
        if t.get("veiculo") or t.get("placa"):
            partes.append(f"🚗 {E(t.get('veiculo') or '')} {E(t.get('placa') or '')}".rstrip())
        if t.get("bairro"):
            partes.append(f"📍 {E(t['bairro'])}")
        partes.append(f"💬 “{E(t.get('problema') or '')}”")
        for i in t.get("itens", []):
            partes.append(f"• {E(i['nome'])}: {rot['pecas'].lower()} {M.faixa_t(i['pecasMin'], i['pecasMax'])} · {rot['mao'].lower()} {M.faixa_t(i['maoMin'], i['maoMax'])}")
        if t.get("total", {}).get("max"):
            partes.append(f"💰 Total: <b>{M.faixa(t['total']['min'], t['total']['max'])}</b>")
        partes.append(f"{icone} SLA: {s['texto']} (prazo {M.data_hora(t['prazo'])}, prioridade {M.PRIORIDADES[t['prioridade']].lower()})")
        if t.get("agendamento"):
            partes.append(f"📅 Agendado: {M.data_hora(t['agendamento'])}")
        if t.get("humano"):
            partes.append("🙋 Cliente pediu atendente")
        if t.get("nps5"):
            partes.append(f"⭐ Avaliação: {t['nps5']}/5")
        return "\n".join(partes)

    def botoes_ticket(self, t):
        b = []
        prox = M.proximo_status(t)
        if prox:
            b.append([(f"▶ Avançar para {prox}", f"av:{t['id']}")])
        b.append([("💬 Responder cliente", f"rp:{t['id']}"), ("🔄 Atualizar", f"vp:{t['id']}")])
        return b

    def comandos_dono(self, chat_id):
        self.tg.call("setMyCommands", commands=[{"command": c, "description": d} for c, d in CMD_DONO],
                     scope={"type": "chat", "chat_id": chat_id}, language_code=None)

    # ---------------------------------------------------------------- entrada
    def processar(self, upd):
        with self.db.lock:
            try:
                if "message" in upd and "text" in upd["message"]:
                    self.on_mensagem(upd["message"])
                elif "callback_query" in upd:
                    self.on_callback(upd["callback_query"])
            except Exception:
                log("ERRO ao processar update:", traceback.format_exc())
            finally:
                self.db.save()

    def on_mensagem(self, msg):
        if msg.get("chat", {}).get("type") != "private":
            return
        cid = msg["chat"]["id"]
        u = self.db.user(cid, msg.get("from"))
        txt = msg["text"].strip()
        if txt.startswith("/"):
            cmd, _, arg = txt[1:].partition(" ")
            cmd = cmd.split("@")[0].lower()
            return self.comando(cid, u, cmd, arg.strip())
        if u.get("aguardando") == "novo_nome":
            return self.criar_negocio_nome(cid, u, txt)
        if u["modo"] == "dono" and u.get("dono_de"):
            return self.texto_dono(cid, u, txt)
        return self.texto_cliente(cid, u, txt)

    # ---------------------------------------------------------------- comandos
    def comando(self, cid, u, cmd, arg):
        if cmd == "start":
            if arg in ("dono", "admin"):
                return self.cmd_dono(cid, u, "")
            if arg and self.db.tenant(arg):
                u["tenant"] = arg; u["modo"] = "cliente"
                return self.iniciar_conversa(cid, u)
            if u.get("dono_de") and u["modo"] == "dono":
                return self.cmd_painel(cid, u)
            if not u.get("tenant"):
                return self.escolher_negocio(cid, "Olá! 👋 Eu sou o Atende AI, o atendimento automático de oficinas e lojas. Com qual negócio você quer falar?")
            return self.iniciar_conversa(cid, u)
        if cmd == "dono":
            return self.cmd_dono(cid, u, arg)
        if cmd == "ajuda":
            return self.cmd_ajuda(cid, u)
        if cmd == "trocar":
            return self.escolher_negocio(cid, "Com qual negócio você quer falar?")
        if cmd == "nova":
            u["modo"] = "cliente" if not (u["modo"] == "dono" and u.get("dono_de")) else u["modo"]
            if u["modo"] == "cliente":
                return self.iniciar_conversa(cid, u)
        if cmd == "cliente":
            if not u.get("dono_de"):
                return self.iniciar_conversa(cid, u)
            u["modo"] = "cliente"; u["tenant"] = u.get("tenant_dono")
            self.tg.send(cid, "🧪 <b>Modo cliente ligado.</b> Agora você conversa como um cliente do seu negócio. Para voltar: /dono")
            return self.iniciar_conversa(cid, u)
        # comandos do dono
        if not u.get("dono_de"):
            return self.tg.send(cid, "Esse comando é para donos de negócio. Se você é dono, envie /dono.")
        u["modo"] = "dono"
        tenant = self.db.tenant(u.get("tenant_dono") or u["dono_de"][0])
        if cmd == "painel":
            return self.cmd_painel(cid, u)
        if cmd == "pedidos":
            return self.cmd_pedidos(cid, tenant)
        if cmd == "catalogo":
            return self.cmd_catalogo(cid, tenant)
        if cmd == "remover":
            return self.cmd_remover(cid, tenant, arg)
        if cmd == "horario":
            return self.cmd_horario(cid, tenant)
        if cmd == "link":
            return self.tg.send(cid, f"🔗 Link para seus clientes falarem com o atendimento da <b>{E(tenant['nome'])}</b>:\n{self.link(tenant['id'])}\n\nColoque no Instagram, no Google Meu Negócio ou num QR code no balcão.")
        if cmd == "codigo":
            return self.tg.send(cid, f"🔑 Código de atendente: <code>{tenant['codigo']}</code>\nOutra pessoa da equipe envia <code>/dono {tenant['codigo']}</code> para receber os pedidos também.")
        if cmd == "conectar":
            return self.cmd_conectar(cid, tenant)
        return self.tg.send(cid, "Não conheço esse comando. Veja /ajuda.")

    def cmd_ajuda(self, cid, u):
        if u.get("dono_de") and u["modo"] == "dono":
            return self.tg.send(cid, "<b>Modo dono</b>\nEscreva naturalmente para cadastrar:\n• <code>Troca de óleo R$ 180 1h</code>\n• <code>Pastilha de freio peças R$ 160 a 320 mão de obra R$ 120 1h30</code>\n• <code>Seg a sex 8h às 18h; sábado 8h às 12h</code>\n• <code>Minha oficina se chama Auto Center Silva</code>\n\n" +
                                "\n".join(f"/{c} — {d}" for c, d in CMD_DONO) + "\n/remover N — remove o item N do catálogo")
        return self.tg.send(cid, "<b>Como funciona</b>\nConte o problema do seu jeito (ex.: “barulho ao frear”). Eu pergunto o que falta, monto o orçamento com os preços do negócio e você aprova com um toque.\n\n/nova — recomeçar\n/trocar — escolher outro negócio\n/dono — sou dono de um negócio\n\n<i>Assistente automático em modo de teste. Os valores são estimativas do catálogo do negócio.</i>")

    def escolher_negocio(self, cid, texto):
        bts = [(("🔧 " if t["segmento"] == "oficina" else "🏬 ") + t["nome"], f"t:{slug}") for slug, t in self.db.d["tenants"].items()]
        return self.tg.send(cid, texto, linhas(bts[:20]))

    def cmd_dono(self, cid, u, arg):
        if arg:
            t = next((t for t in self.db.d["tenants"].values() if t["codigo"] == arg.strip().upper()), None)
            if not t:
                return self.tg.send(cid, "Código não encontrado. Confira com o dono do negócio.")
            return self.virar_dono(cid, u, t, coadmin=True)
        if u.get("dono_de"):
            u["modo"] = "dono"
            return self.cmd_painel(cid, u)
        livres = [t for t in self.db.d["tenants"].values() if not t["donos"]]
        bts = [(f"Assumir: {t['nome']} ({'oficina' if t['segmento'] == 'oficina' else 'loja'}, exemplo)", f"claim:{t['id']}") for t in livres]
        bts.append(("➕ Criar meu negócio do zero", "novo"))
        return self.tg.send(cid, "👋 <b>Área do dono</b>\nVocê pode assumir um negócio de exemplo (já vem com catálogo, bom para testar) ou criar o seu.\n\nSe outra pessoa já é dona e te passou um código, envie <code>/dono CÓDIGO</code>.", linhas(bts))

    def virar_dono(self, cid, u, t, coadmin=False):
        if cid not in t["donos"]:
            t["donos"].append(cid)
        if t["id"] not in u["dono_de"]:
            u["dono_de"].append(t["id"])
        u["tenant_dono"] = t["id"]; u["modo"] = "dono"
        self.comandos_dono(cid)
        self.tg.send(cid, f"✅ Você agora {'atende' if coadmin else 'é dono(a) de'} <b>{E(t['nome'])}</b>.\n\n"
                          f"1️⃣ Cadastre ou ajuste serviços escrevendo, ex.: <code>Alinhamento R$ 150 1h</code>\n"
                          f"2️⃣ Mande este link para seus clientes: {self.link(t['id'])}\n"
                          f"3️⃣ Quando um cliente pedir orçamento, você recebe aqui, com botões para avançar o pedido.\n\n"
                          f"Para testar você mesmo como cliente: /cliente · Comandos: /ajuda")
        return self.cmd_catalogo(cid, t)

    def criar_negocio_nome(self, cid, u, txt):
        nome = txt.strip()[:60]
        if len(nome) < 3:
            return self.tg.send(cid, "Qual é o nome do seu negócio?")
        u["aguardando"] = None; u["novo_nome"] = nome
        return self.tg.send(cid, f"Ótimo: <b>{E(nome)}</b>. Que tipo de negócio é?", linhas([
            ("🔧 Oficina (começar com catálogo de exemplo)", "seg:oficina:ex"), ("🔧 Oficina (catálogo vazio)", "seg:oficina:vazio"),
            ("🏬 Loja (começar com catálogo de exemplo)", "seg:loja:ex"), ("🏬 Loja (catálogo vazio)", "seg:loja:vazio")]))

    def cmd_painel(self, cid, u):
        t = self.db.tenant(u.get("tenant_dono") or u["dono_de"][0])
        k = kpis(t, [x for x in self.db.d["tickets"] if x["tenant"] == t["id"]])
        txt = (f"📊 <b>{E(t['nome'])}</b> · painel\n"
               f"Atendimentos: <b>{k['atendimentos']}</b> ({k['automaticos']} sem atendente)\n"
               f"Taxa de aprovação: <b>{k['taxa_aprovacao']}</b>\n"
               f"1ª resposta média: <b>{k['tempo_resposta']}</b>\n"
               f"SLA cumprido: <b>{k['sla_cumprido']}</b> · em risco agora: {k['em_risco']}\n"
               f"Faturamento previsto: <b>{M.brl(k['previsto'])}</b> · realizado: <b>{M.brl(k['realizado'])}</b>\n"
               f"Avaliação média: <b>{k['avaliacao']}</b>\n\n"
               f"Pedidos: /pedidos · Catálogo: /catalogo · Link dos clientes: /link · Dashboard web: /conectar")
        return self.tg.send(cid, txt)

    def cmd_pedidos(self, cid, t):
        abertos = [x for x in self.db.d["tickets"] if x["tenant"] == t["id"] and x["status"] != "Entregue"]
        if not abertos:
            return self.tg.send(cid, f"Nenhum pedido em aberto. Mande o link {self.link(t['id'])} para um cliente (ou teste com /cliente).")
        abertos.sort(key=lambda x: x["prazo"])
        bts = []
        for x in abertos[:12]:
            s = M.sla_estado(x)
            ic = {"ok": "🟢", "atencao": "🟡", "erro": "🔴"}[s["cls"]]
            bts.append((f"{ic} {x['id']} · {x['status']} · {(x.get('cliente') or 'Cliente')[:18]}", f"vp:{x['id']}"))
        return self.tg.send(cid, f"📋 <b>{len(abertos)} pedido(s) em aberto</b> (ordenados pelo prazo). Toque para ver e avançar:", linhas(bts))

    def cmd_catalogo(self, cid, t):
        rot = M.DADOS["segmentos"][t["segmento"]]["rotulos"]
        if not t["catalogo"]:
            return self.tg.send(cid, "Seu catálogo está vazio. Escreva, por exemplo: <code>Troca de óleo R$ 180 1h</code>")
        ls = [f"{n}. <b>{E(c['nome'])}</b> — {M.faixa(c['pecasMin'] + c['maoMin'], c['pecasMax'] + c['maoMax'])} · {M.dur(c['duracao'])}" for n, c in enumerate(t["catalogo"], 1)]
        return self.tg.send(cid, f"🗂️ <b>Catálogo de {E(t['nome'])}</b> ({rot['pecas'].lower()} + {rot['mao'].lower()})\n" + "\n".join(ls) +
                            "\n\nPara incluir ou alterar, escreva: <code>Nome do serviço R$ 150 1h</code>. Para remover: <code>/remover 3</code>")

    def cmd_remover(self, cid, t, arg):
        try:
            i = int(arg) - 1
            c = t["catalogo"].pop(i)
        except Exception:
            return self.tg.send(cid, "Use <code>/remover N</code>, com o número do item em /catalogo.")
        return self.tg.send(cid, f"🗑️ Removido: {E(c['nome'])}")

    def cmd_horario(self, cid, t):
        dias = ["Domingo", "Segunda", "Terça", "Quarta", "Quinta", "Sexta", "Sábado"]
        ls = [f"{dias[d]}: {('%s às %s' % tuple(t['horario'][d])) if t['horario'][d] else 'fechado'}" for d in [1, 2, 3, 4, 5, 6, 0]]
        return self.tg.send(cid, "🕗 <b>Horário</b>\n" + "\n".join(ls) + "\n\nPara mudar, escreva: <code>Seg a sex 8h às 18h; sábado 8h às 12h</code>")

    def cmd_conectar(self, cid, t):
        url = tunnel_url()
        if not url:
            return self.tg.send(cid, "O túnel da API não está ativo agora, então o dashboard web não consegue ler os dados ao vivo. Os pedidos continuam funcionando aqui no Telegram.")
        link = f"{PAGES}?api={urllib.parse.quote(url, safe='')}&negocio={t['id']}&chave={t['chave_api']}#/dashboard"
        return self.tg.send(cid, f"🖥️ <b>Dashboard ao vivo</b>\nAbra no computador ou celular:\n{E(link)}\n\n⚠️ Esse link tem a chave de leitura dos seus pedidos. Não compartilhe.\nModo teste: o endereço muda quando o servidor de teste reinicia; peça /conectar de novo.")

    # ---------------------------------------------------------------- dono: texto livre
    def texto_dono(self, cid, u, txt):
        t = self.db.tenant(u.get("tenant_dono") or u["dono_de"][0])
        if u.get("respondendo"):
            tk = self.db.ticket(u["respondendo"])
            u["respondendo"] = None
            if tk and tk.get("chat_id"):
                tk.setdefault("chat", []).append({"de": "atendente", "texto": txt, "ts": M.agora_ms()})
                if tk.get("humano") and not tk.get("respostaHumanaSeg"):
                    tk["respostaHumanaSeg"] = round((M.agora_ms() - tk.get("humanoEm", tk["criado"])) / 1000)
                self.tg.send(tk["chat_id"], f"👤 <b>{E(t['nome'])}</b> (atendente):\n{E(txt)}")
                return self.tg.send(cid, f"✉️ Enviado para {E(tk.get('cliente') or 'o cliente')} ({tk['id']}).")
        res = M.parse_dono(txt, t["segmento"])
        out = []
        if res["nome"]:
            t["nome"] = res["nome"][:60]; out.append(f"🏷️ Nome do negócio: {E(t['nome'])}")
        for sv in res["servicos"]:
            ex = next((c for c in t["catalogo"] if M.norm(c["nome"]) == M.norm(sv["nome"])), None)
            alvo = ex or {"id": slugify(sv["nome"])[:20] + "-" + secrets.token_hex(2), "nome": sv["nome"], "categoria": "Cadastrado no chat",
                          "pecasMin": 0, "pecasMax": 0, "maoMin": 0, "maoMax": 0, "duracao": 60, "palavras": []}
            if sv["pecasMin"] or sv["pecasMax"] or sv["maoMin"] or sv["maoMax"]:
                for k in ("pecasMin", "pecasMax", "maoMin", "maoMax"):
                    alvo[k] = sv[k]
            if sv["duracao"]:
                alvo["duracao"] = sv["duracao"]
            alvo["palavras"] = sorted(set(alvo.get("palavras", []) + sv["palavras"]))
            if not ex:
                t["catalogo"].append(alvo)
            out.append(("✏️ Atualizei: " if ex else "✅ Cadastrei: ") + f"{E(alvo['nome'])} · {M.faixa(alvo['pecasMin'] + alvo['maoMin'], alvo['pecasMax'] + alvo['maoMax'])} · {M.dur(alvo['duracao'])}")
        for h in res["horarios"]:
            for d in h["dias"]:
                t["horario"][d] = None if h.get("fechado") else [h["abre"], h["fecha"]]
            out.append("🕗 " + ", ".join(M.DIAS_CURTO[d] for d in h["dias"]) + ": " + ("fechado" if h.get("fechado") else f"{h['abre']} às {h['fecha']}"))
        if not out:
            return self.tg.send(cid, "Não encontrei preço, duração nem horário nessa mensagem. Exemplos:\n<code>Alinhamento R$ 150 1h</code>\n<code>Seg a sex 8h às 18h</code>\n\nComandos: /ajuda · Testar como cliente: /cliente")
        return self.tg.send(cid, "Entendi!\n" + "\n".join(out) + "\n\nOs próximos orçamentos já usam esses dados. Ver tudo: /catalogo")

    # ---------------------------------------------------------------- cliente
    def iniciar_conversa(self, cid, u):
        slug = u.get("tenant") or next(iter(self.db.d["tenants"]))
        u["tenant"] = slug
        t = self.db.tenant(slug)
        sd = M.DADOS["segmentos"][t["segmento"]]
        u["conv"] = {"tenant": slug, "etapa": "problema", "campo": None, "dados": {}, "intent": None, "confianca": 0, "ticket": None}
        quem = "com o seu carro" if t["segmento"] == "oficina" else "que você precisa"
        ex = " · ".join(f"“{e}”" for e in sd["exemplos"][:3])
        return self.tg.send(cid, f"Olá! 👋 Aqui é o atendimento automático da <b>{E(t['nome'])}</b>.\nMe conte o que está acontecendo {quem}, do seu jeito.\n\nExemplos: {ex}\n\n<i>Assistente automático (modo de teste). A qualquer momento escreva “atendente” para falar com uma pessoa.</i>")

    def texto_cliente(self, cid, u, txt, valor=None):
        if not u.get("conv"):
            if not u.get("tenant"):
                return self.escolher_negocio(cid, "Olá! 👋 Com qual negócio você quer falar?")
            self.iniciar_conversa(cid, u)
            if not txt:
                return
        conv = u["conv"]
        t = self.db.tenant(conv["tenant"])
        sd = M.DADOS["segmentos"][t["segmento"]]
        tk = self.db.ticket(conv["ticket"]) if conv.get("ticket") else None
        if tk:
            tk.setdefault("chat", []).append({"de": "cliente", "texto": txt, "ts": M.agora_ms()})
        else:
            conv.setdefault("chat", []).append({"de": "cliente", "texto": txt, "ts": M.agora_ms()})
        conv["ultima"] = M.agora_ms()
        n = M.norm(txt)

        def out(texto, teclado=None):
            alvo = self.db.ticket(conv["ticket"]) if conv.get("ticket") else None
            (alvo.setdefault("chat", []) if alvo else conv.setdefault("chat", [])).append({"de": "bot", "texto": re.sub(r"<[^>]+>", "", texto), "ts": M.agora_ms()})
            self.tg.send(cid, texto, teclado)

        if valor == "atendente" or (not valor and re.search(r"atendente|humano|falar com (alguem|uma pessoa)|pessoa de verdade", n)):
            return self.chamar_humano(cid, u, conv, t, txt, out)
        ext = M.extrair(sd, txt)
        etapa = conv["etapa"]
        if etapa == "problema":
            it, conf = None, 0
            if valor and valor.startswith("serv:"):
                c = next((x for x in t["catalogo"] if x["id"] == valor[5:]), None)
                if c:
                    it, conf = M.intent_de_item(c), 0.95
            else:
                it, conf = M.detectar(sd, t["catalogo"], txt)
                if not it:
                    rid = self.ia.classificar(txt, t["catalogo"])
                    if rid:
                        it, conf = M.intent_de_item(next(c for c in t["catalogo"] if c["id"] == rid)), 0.8
                        it["explicacao"] = "Entendi (com ajuda da IA): " + it["rotulo"] + "."
            if not it:
                bts = [(c["nome"][:40], f"serv:{c['id']}") for c in t["catalogo"][:6]] + [("🙋 Falar com atendente", "atendente")]
                return out("Ainda não tenho certeza do que é. Qual destas opções é mais parecida?", linhas(bts))
            for k, v in ext.items():
                conv["dados"].setdefault(k, v)
            conv["intent"] = it; conv["confianca"] = conf
            tk = self.criar_ticket(cid, u, conv, t, txt)
            achados = [x for x in (ext.get("veiculo") and "veículo " + ext["veiculo"], ext.get("placa") and "placa " + ext["placa"]) if x]
            out(E(it["explicacao"]) + (" Já anotei: " + ", ".join(achados) + "." if achados else ""))
            return self.perguntar(conv, t, out)
        if etapa == "pergunta":
            campo, prefixo = conv["campo"], ""
            d = conv["dados"]
            if campo == "cliente":
                nome = ext.get("cliente") or re.sub(r"^(meu nome (é|e)|me chamo|sou (o|a)|é|e)\s+", "", re.sub(r"^(oi|olá|ola)[,!. ]*", "", txt, flags=re.I), flags=re.I).strip()
                nome = re.sub(r"[^A-Za-zÀ-ú '\-]", "", " ".join(M.cap(p) for p in nome.split()[:3])).strip()
                if len(nome) < 2:
                    return out("Não peguei seu nome. Pode escrever de novo?")
                d["cliente"] = nome; prefixo = f"Prazer, {E(M.primeiro_nome(nome))}!"
            elif campo == "veiculo":
                d["veiculo"] = ext.get("veiculo") or M.cap(txt)[:40]
                if ext.get("placa") and d.get("placa") is None:
                    d["placa"] = ext["placa"]
                prefixo = f"Anotado: {E(d['veiculo'])}."
            elif campo == "placa":
                if valor == "pular" or re.search(r"pular|nao sei|nao tenho|depois|sem placa", n):
                    d["placa"] = ""
                elif ext.get("placa"):
                    d["placa"] = ext["placa"]
                else:
                    return out("Não reconheci a placa. Use o formato ABC1D23 ou ABC-1234, ou toque em Pular.", [[("Pular", "pular")]])
            elif campo == "bairro":
                d["bairro"] = "Retirada na loja" if valor == "retirar" or re.search(r"retir", n) else M.cap(txt)[:40]
            elif campo == "urgencia":
                d["urgencia"] = valor[4:] if valor and valor.startswith("urg:") else (M.urgencia_de_resposta(txt) or "media")
            for k, v in ext.items():
                if k != "cliente":
                    d.setdefault(k, v)
            self.sync(conv, self.db.ticket(conv["ticket"]))
            return self.perguntar(conv, t, out, prefixo)
        if etapa == "orcado":
            if valor == "aprovar" or re.match(r"^(sim|aprovo|aprovar|aprovado|ok|pode fazer|pode|fechado|bora|quero)", n):
                return self.aprovar(cid, conv, t, out)
            return out("Quer seguir com o orçamento? É só tocar em um dos botões.", [[("✅ Aprovar orçamento", "aprovar")], [("🙋 Falar com atendente", "atendente")]])
        if etapa == "agendar":
            tk = self.db.ticket(conv["ticket"])
            if valor and valor.startswith("slot:"):
                ts = int(valor[5:]); tk["agendamento"] = ts
                for e in tk.get("eventos", []):
                    if e["regra"] == "lembrete" and e["estado"] == "aguardando_horario":
                        e["estado"] = "agendado"; e["ts"] = max(ts - 2 * 3600000, M.agora_ms() + 10 * 60000)
                conv["etapa"] = "fim"
                out(f"📅 Agendado para <b>{M.data_hora(ts)}</b>. Vou te mandar um lembrete antes. Protocolo: <b>{tk['id']}</b>.\nQualquer dúvida, é só escrever aqui.")
                return self.avisar_donos(t, f"📅 <b>{tk['id']}</b> agendado para {M.data_hora(ts)}.\n\n" + self.resumo_ticket(tk, t), self.botoes_ticket(tk))
            slots = M.proximos_horarios(M.agora_ms(), t["horario"], 3)
            return out("Pra confirmar, toque em um dos horários:", linhas([("📅 " + M.data_hora(s), f"slot:{s}") for s in slots]))
        # fim / humano: encaminha para a equipe
        tk = self.db.ticket(conv["ticket"]) if conv.get("ticket") else None
        if tk:
            self.avisar_donos(t, f"💬 <b>{E(tk.get('cliente') or 'Cliente')}</b> ({tk['id']}) escreveu:\n“{E(txt)}”", [[("💬 Responder", f"rp:{tk['id']}"), ("📄 Ver pedido", f"vp:{tk['id']}")]])
            return out(f"Recebido! Passei sua mensagem para a equipe da {E(t['nome'])} (pedido {tk['id']}). Para um assunto novo, use /nova.")
        return self.iniciar_conversa(cid, u)

    def criar_ticket(self, cid, u, conv, t, problema):
        it = conv["intent"]; agora = M.agora_ms()
        tk = {"id": self.novo_id(t), "tenant": t["id"], "seg": t["segmento"], "canal": "telegram", "chat_id": cid,
              "cliente": conv["dados"].get("cliente") or (u.get("nome") or "Cliente").strip(), "telegram": u.get("username"),
              "veiculo": conv["dados"].get("veiculo", ""), "placa": conv["dados"].get("placa") or "", "bairro": conv["dados"].get("bairro", ""),
              "problema": problema, "intent": it["id"] if it else None,
              "servicos": list(it["servicos"]) if it else [], "opcionais": list(it.get("opcionais", [])) if it else [],
              "prioridade": conv["dados"].get("urgencia") or (it["prioridade"] if it else "media"), "status": "Novo", "criado": agora,
              "humano": False, "tempoRespostaSeg": max(1, round((agora - conv.get("ultima", agora)) / 1000)),
              "chat": list(conv.get("chat", [])), "eventos": [], "historico": [{"status": "Novo", "ts": agora}],
              "itens": [], "total": {"min": 0, "max": 0}, "alertas": {}}
        o = M.orcamento(M.DADOS["segmentos"][t["segmento"]], t["catalogo"], tk["servicos"], tk["veiculo"])
        tk["itens"], tk["total"] = o["itens"], o["total"]
        tk["prazo"] = M.calc_prazo(t, tk["prioridade"], agora, o["duracao"])
        self.db.d["tickets"].insert(0, tk)
        conv["ticket"] = tk["id"]; conv["chat"] = []
        return tk

    def sync(self, conv, tk):
        if not tk:
            return
        for k in ("cliente", "veiculo", "placa", "bairro"):
            if conv["dados"].get(k) not in (None, ""):
                tk[k] = conv["dados"][k]
        if conv["dados"].get("urgencia"):
            tk["prioridade"] = conv["dados"]["urgencia"]

    def perguntar(self, conv, t, out, prefixo=""):
        sd = M.DADOS["segmentos"][t["segmento"]]
        p = next((q for q in sd["perguntas"] if conv["dados"].get(q["campo"]) is None), None)
        if not p:
            return self.orcar(conv, t, out, prefixo)
        conv["etapa"] = "pergunta"; conv["campo"] = p["campo"]
        kb = None
        if p["campo"] == "urgencia":
            kb = [[("🚨 Hoje, é urgente", "urg:alta")], [("📅 Nesta semana", "urg:media")], [("🙂 Sem pressa", "urg:baixa")]]
        elif p["campo"] == "placa":
            kb = [[("Pular", "pular")]]
        elif p["campo"] == "bairro":
            kb = [[("🏬 Vou retirar na loja", "retirar")]]
        return out((prefixo + " " if prefixo else "") + E(p["texto"]), kb)

    def orcar(self, conv, t, out, prefixo=""):
        tk = self.db.ticket(conv["ticket"]); self.sync(conv, tk)
        sd = M.DADOS["segmentos"][t["segmento"]]
        if t["segmento"] == "loja" and conv["dados"].get("bairro") is not None:
            if conv["dados"]["bairro"] == "Retirada na loja":
                tk["servicos"] = [s for s in tk["servicos"] if s != "entrega"]
            elif "entrega" not in tk["servicos"] and any(c["id"] == "entrega" for c in t["catalogo"]):
                tk["servicos"].append("entrega")
            tk["opcionais"] = [s for s in tk["opcionais"] if s not in tk["servicos"] and s != "entrega"]
        o = M.orcamento(sd, t["catalogo"], tk["servicos"], tk["veiculo"])
        tk["itens"], tk["total"], tk["ajuste"] = o["itens"], o["total"], o["ajuste"]
        tk["prazo"] = M.calc_prazo(t, tk["prioridade"], M.agora_ms(), o["duracao"])
        M.mudar_status(tk, t, "Orçado", pular_chat=("orcamento",))
        rot = sd["rotulos"]
        ls = [f"🧾 <b>Orçamento {tk['id']}</b> · automático"]
        for i in tk["itens"]:
            ls.append(f"• <b>{E(i['nome'])}</b>\n   {rot['pecas']}: {M.faixa_t(i['pecasMin'], i['pecasMax'])} · {rot['mao']}: {M.faixa_t(i['maoMin'], i['maoMax'])}")
        ls.append(f"\n💰 <b>Total estimado: {M.faixa(tk['total']['min'], tk['total']['max'])}</b>")
        ls.append(f"⏱️ Duração estimada: {M.dur(o['duracao'])}")
        ls.append(f"📅 Prazo combinado: {M.data_hora(tk['prazo'])} (prioridade {M.PRIORIDADES[tk['prioridade']].lower()})")
        if o["ajuste"]:
            ls.append(f"ℹ️ {E(o['ajuste'])}")
        opc = [c for c in t["catalogo"] if c["id"] in tk.get("opcionais", [])]
        if opc:
            ls.append("🔎 Pode ser necessário, só com sua autorização: " + "; ".join(f"{E(c['nome'])} ({M.faixa(c['pecasMin'] + c['maoMin'], c['pecasMax'] + c['maoMax'])})" for c in opc))
        ls.append(f"<i>Valores estimados, confirmados {'após avaliação do carro' if t['segmento'] == 'oficina' else 'na separação do pedido'}. Válido por 7 dias.</i>")
        if prefixo:
            out(prefixo + " Montei seu orçamento:")
        out("\n".join(ls), [[("✅ Aprovar orçamento", "aprovar")], [("🙋 Falar com atendente", "atendente")]])
        conv["etapa"] = "orcado"
        self.avisar_donos(t, "🆕 <b>Orçamento enviado automaticamente</b>\n\n" + self.resumo_ticket(tk, t), self.botoes_ticket(tk))

    def aprovar(self, cid, conv, t, out):
        tk = self.db.ticket(conv["ticket"])
        for ev in M.mudar_status(tk, t, "Aprovado", posvenda_atraso_min=POSVENDA_MIN):
            self.tg.send(cid, "🤖 " + E(ev["texto"]))
        for e in tk["eventos"]:
            if e["regra"] == "lembrete" and e["estado"] == "agendado":
                e["estado"] = "aguardando_horario"
        slots = M.proximos_horarios(M.agora_ms(), t["horario"], 3)
        conv["etapa"] = "agendar"
        out("Escolha o melhor horário para trazer o carro:" if t["segmento"] == "oficina" else "Escolha quando quer receber ou retirar:",
            linhas([("📅 " + M.data_hora(s), f"slot:{s}") for s in slots]) + [[("🙋 Falar com atendente", "atendente")]])
        self.avisar_donos(t, "✅ <b>Orçamento aprovado pelo cliente!</b>\n\n" + self.resumo_ticket(tk, t), self.botoes_ticket(tk))

    def chamar_humano(self, cid, u, conv, t, txt, out):
        tk = self.db.ticket(conv["ticket"]) if conv.get("ticket") else None
        if not tk:
            conv["intent"] = None
            tk = self.criar_ticket(cid, u, conv, t, txt)
        tk["humano"] = True; tk["humanoEm"] = M.agora_ms(); self.sync(conv, tk)
        sla = t["sla"].get(tk["prioridade"]) or t["sla"]["media"]
        conv["etapa"] = "humano"
        if t.get("donos"):
            out(f"Combinado! Chamei a equipe da {E(t['nome'])}. Pela nossa regra, a resposta chega em até {sla['respostaMin']} min (em horário de funcionamento). Protocolo: <b>{tk['id']}</b>.")
        else:
            out(f"Registrei seu pedido de atendimento (protocolo <b>{tk['id']}</b>). Este negócio de teste ainda não tem um atendente conectado, então a resposta pode demorar.")
        self.avisar_donos(t, "🙋 <b>Cliente pediu atendente</b> · responda pelo botão abaixo\n\n" + self.resumo_ticket(tk, t),
                          [[("💬 Responder cliente", f"rp:{tk['id']}")]] + self.botoes_ticket(tk)[:1])

    # ---------------------------------------------------------------- botões
    def on_callback(self, cq):
        cid = cq["message"]["chat"]["id"]
        dado = cq.get("data") or ""
        self.tg.call("answerCallbackQuery", _t=10, callback_query_id=cq["id"])
        u = self.db.user(cid, cq.get("from"))
        rotulo = dado
        try:
            for linha in cq["message"].get("reply_markup", {}).get("inline_keyboard", []):
                for b in linha:
                    if b.get("callback_data") == dado:
                        rotulo = b["text"]
        except Exception:
            pass
        # dono
        if dado.startswith(("av:", "rp:", "vp:")):
            tk = self.db.ticket(dado[3:])
            if not tk or tk["tenant"] not in u.get("dono_de", []):
                return self.tg.send(cid, "Esse pedido não é de um negócio seu.")
            t = self.db.tenant(tk["tenant"])
            if dado.startswith("vp:"):
                return self.tg.send(cid, self.resumo_ticket(tk, t), self.botoes_ticket(tk))
            if dado.startswith("rp:"):
                u["respondendo"] = tk["id"]; u["modo"] = "dono"
                return self.tg.send(cid, f"✍️ Escreva agora a mensagem para <b>{E(tk.get('cliente') or 'o cliente')}</b> ({tk['id']}). A próxima mensagem que você mandar vai direto para ele.")
            prox = M.proximo_status(tk)
            if not prox:
                return self.tg.send(cid, f"{tk['id']} já foi entregue.")
            esperado = cq["message"].get("text", "")
            if f"Avançar para {prox}" not in json.dumps(cq["message"].get("reply_markup", {}), ensure_ascii=False) and esperado:
                pass  # botão antigo: avança mesmo assim a partir do status atual
            saem = M.mudar_status(tk, t, prox, posvenda_atraso_min=POSVENDA_MIN)
            for ev in saem:
                if tk.get("chat_id"):
                    self.tg.send(tk["chat_id"], "🤖 " + E(ev["texto"]))
            if prox == "Aprovado":
                for e in tk["eventos"]:
                    if e["regra"] == "lembrete" and e["estado"] == "agendado":
                        e["estado"] = "aguardando_horario"
            extra = " · pós-venda com avaliação sai em %d min" % POSVENDA_MIN if prox == "Entregue" else ""
            return self.tg.send(cid, f"✔️ {tk['id']} → <b>{prox}</b>. {len(saem)} mensagem(ns) automática(s) enviada(s) ao cliente{extra}.\n\n" + self.resumo_ticket(tk, t), self.botoes_ticket(tk))
        if dado.startswith("claim:"):
            t = self.db.tenant(dado[6:])
            if not t:
                return
            if t["donos"] and cid not in t["donos"]:
                return self.tg.send(cid, "Esse negócio já tem dono. Peça o código de atendente para ele e envie /dono CÓDIGO.")
            return self.virar_dono(cid, u, t)
        if dado == "novo":
            u["aguardando"] = "novo_nome"
            return self.tg.send(cid, "Qual é o nome do seu negócio?")
        if dado.startswith("seg:"):
            _, seg, modo = dado.split(":")
            nome = u.get("novo_nome") or "Meu negócio"
            slug = slugify(nome)
            while self.db.tenant(slug):
                slug = slugify(nome)[:22] + "-" + secrets.token_hex(2)
            t = novo_tenant(slug, nome, seg, modo == "ex")
            self.db.d["tenants"][slug] = t
            return self.virar_dono(cid, u, t)
        if dado.startswith("t:"):
            if self.db.tenant(dado[2:]):
                u["tenant"] = dado[2:]
                if u["modo"] == "dono":
                    u["modo"] = "cliente"
                return self.iniciar_conversa(cid, u)
            return
        if dado.startswith("nps:"):
            tid, nota = dado[4:].split(":")
            tk = self.db.ticket(tid)
            if tk and tk.get("chat_id") == cid:
                tk["nps5"] = int(nota)
                tk.setdefault("chat", []).append({"de": "cliente", "texto": f"Avaliação: {nota}/5", "ts": M.agora_ms()})
                t = self.db.tenant(tk["tenant"])
                self.tg.send(cid, "Obrigado pela avaliação! 💙" + (" Se quiser, conte o que podemos melhorar: é só escrever aqui." if int(nota) <= 3 else ""))
                self.avisar_donos(t, f"⭐ {E(tk.get('cliente') or 'Cliente')} avaliou o pedido {tk['id']} com <b>{nota}/5</b>.")
            return
        if dado == "nova":
            return self.iniciar_conversa(cid, u)
        # botões do fluxo do cliente
        if u["modo"] == "dono" and u.get("dono_de") and not u.get("conv"):
            return self.tg.send(cid, "Você está no modo dono. Para testar como cliente: /cliente")
        return self.texto_cliente(cid, u, rotulo, dado)

    # ---------------------------------------------------------------- vigia de SLA e agendamentos
    def vigiar(self):
        with self.db.lock:
            agora = M.agora_ms(); mudou = False
            for tk in self.db.d["tickets"]:
                t = self.db.tenant(tk["tenant"])
                if not t:
                    continue
                s = M.sla_estado(tk, agora)
                al = tk.setdefault("alertas", {})
                if s["ativo"] and tk["status"] != "Novo":
                    if s["cls"] == "atencao" and not al.get("atencao"):
                        al["atencao"] = agora; mudou = True
                        self.avisar_donos(t, f"🟡 <b>SLA em atenção</b>: {tk['id']} ({E(tk['status'])}) · {s['texto']}.", self.botoes_ticket(tk))
                    if s["cls"] == "erro" and not al.get("erro"):
                        al["erro"] = agora; mudou = True
                        self.avisar_donos(t, f"🔴 <b>SLA estourado</b>: {tk['id']} ({E(tk['status'])}) · {s['texto']}.", self.botoes_ticket(tk))
                for e in tk.get("eventos", []):
                    if e["estado"] == "agendado" and e["ts"] <= agora and tk.get("chat_id"):
                        e["estado"] = "enviado"; e["ts"] = agora; mudou = True
                        tk.setdefault("chat", []).append({"de": "auto", "regra": e["regra"], "texto": e["texto"], "ts": agora})
                        kb = [[(("⭐" * n), f"nps:{tk['id']}:{n}") for n in (1, 2, 3)], [(("⭐" * n), f"nps:{tk['id']}:{n}") for n in (4, 5)]] if e["regra"] == "posvenda" else None
                        texto = e["texto"]
                        if e["regra"] == "posvenda":
                            texto = re.sub(r"De 0 a 10[^?]*\?", "Que nota você dá de 1 a 5?", texto)
                        self.tg.send(tk["chat_id"], "🤖 " + E(texto), kb)
            if mudou:
                self.db.save()


# ============================================================ KPIs / exportação
def kpis(t, tickets):
    passou = lambda x, st: any(h["status"] == st for h in x.get("historico", []))  # noqa: E731
    orc = [x for x in tickets if passou(x, "Orçado")]
    apr = [x for x in tickets if passou(x, "Aprovado")]
    concl = [x for x in tickets if x.get("prontoEm")]
    no_prazo = [x for x in concl if x["prontoEm"] <= x["prazo"]]
    estour = [x for x in tickets if not x.get("prontoEm") and x["prazo"] < M.agora_ms()]
    abertos = [x for x in tickets if x["status"] in ("Orçado", "Aprovado", "Em serviço", "Pronto")]
    entreg = [x for x in tickets if x["status"] == "Entregue"]
    notas = [x["nps5"] for x in tickets if x.get("nps5")]
    resp = sum(x.get("tempoRespostaSeg", 0) for x in tickets) / len(tickets) if tickets else 0
    den = len(concl) + len(estour)
    risco = [x for x in tickets if M.sla_estado(x)["ativo"] and M.sla_estado(x)["cls"] != "ok"]
    return {"negocio": t["nome"], "atendimentos": len(tickets), "automaticos": len([x for x in tickets if not x.get("humano")]),
            "taxa_aprovacao": f"{round(len(apr) / len(orc) * 100)}%" if orc else "—",
            "tempo_resposta": (f"{round(resp)} s" if resp < 60 else f"{resp / 60:.1f} min".replace(".", ",")) if tickets else "—",
            "sla_cumprido": f"{round(len(no_prazo) / den * 100)}%" if den else "—", "em_risco": len(risco),
            "previsto": sum(M.valor_medio(x) for x in abertos), "realizado": sum(x.get("valorFinal") or M.valor_medio(x) for x in entreg),
            "avaliacao": f"{sum(notas) / len(notas):.1f}/5".replace(".", ",") if notas else "—"}


def ticket_publico(x):
    """Formato igual ao da demonstração web, sem chat_id."""
    y = {k: v for k, v in x.items() if k not in ("chat_id", "alertas", "tenant")}
    y["exemplo"] = False
    y["telefone"] = ""
    if x.get("nps5"):
        y["nps"] = x["nps5"] * 2  # nota 1–5 convertida para a escala 0–10 do dashboard
    y["eventos"] = [e for e in x.get("eventos", []) if e["estado"] in ("enviado", "agendado")]
    return y


def tunnel_url():
    try:
        u = open(TUNNEL_FILE).read().strip()
        return u if u.startswith("https://") else None
    except Exception:
        return None


# ============================================================ API HTTP (somente leitura)
def criar_api(bot: Bot, ia: IA):
    class H(BaseHTTPRequestHandler):
        def log_message(self, *a):
            pass

        def _cors(self):
            o = self.headers.get("Origin")
            if o in CORS_OK:
                self.send_header("Access-Control-Allow-Origin", o)
                self.send_header("Vary", "Origin")
                self.send_header("Access-Control-Allow-Headers", "X-Atende-Chave")
                self.send_header("Access-Control-Allow-Methods", "GET, OPTIONS")

        def _json(self, code, obj):
            b = json.dumps(obj, ensure_ascii=False).encode()
            self.send_response(code)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Cache-Control", "no-store")
            self._cors()
            self.end_headers()
            self.wfile.write(b)

        def do_OPTIONS(self):
            self.send_response(204); self._cors(); self.end_headers()

        def do_GET(self):
            url = urllib.parse.urlparse(self.path)
            q = {k: v[0] for k, v in urllib.parse.parse_qs(url.query).items()}
            if url.path in ("/", "/api/saude"):
                with bot.db.lock:
                    return self._json(200, {"ok": True, "servico": "Atende AI · bot de teste", "bot": "@" + BOT_USER, "ia": ia.ok,
                                            "negocios": len(bot.db.d["tenants"]), "agora": M.agora_ms()})
            if not url.path.startswith("/api/"):
                return self._json(404, {"erro": "não encontrado"})
            with bot.db.lock:
                t = bot.db.tenant(q.get("negocio", ""))
                chave = self.headers.get("X-Atende-Chave") or q.get("chave", "")
                if not t or not secrets.compare_digest(chave, t["chave_api"]):
                    return self._json(401, {"erro": "negócio ou chave inválidos"})
                tks = [x for x in bot.db.d["tickets"] if x["tenant"] == t["id"]]
                neg = {"id": t["id"], "nome": t["nome"], "segmento": t["segmento"], "horario": t["horario"], "link": bot.link(t["id"])}
                if url.path == "/api/pedidos":
                    return self._json(200, {"negocio": neg, "pedidos": [ticket_publico(x) for x in tks]})
                if url.path == "/api/kpis":
                    return self._json(200, kpis(t, tks))
                if url.path == "/api/catalogo":
                    return self._json(200, {"negocio": neg, "catalogo": t["catalogo"]})
                if url.path == "/api/export":
                    return self._json(200, {"negocio": neg, "catalogo": t["catalogo"], "automacoes": t["automacoes"], "sla": t["sla"],
                                            "pedidos": [ticket_publico(x) for x in tks], "kpis": kpis(t, tks), "geradoEm": M.agora_ms()})
            return self._json(404, {"erro": "rota desconhecida"})

    srv = ThreadingHTTPServer(("127.0.0.1", API_PORT), H)
    threading.Thread(target=srv.serve_forever, daemon=True, name="api").start()
    return srv


# ============================================================ principal
TG: Telegram | None = None


def configurar(tg: Telegram):
    tg.call("setMyCommands", commands=[{"command": c, "description": d} for c, d in CMD_CLIENTE])
    tg.call("setMyDescription", description="Atendimento automático de oficinas e lojas (modo de teste). Conte o problema do seu jeito, receba o orçamento com os preços do negócio e aprove com um toque. Donos: envie /dono para cadastrar serviços e acompanhar pedidos.")
    tg.call("setMyShortDescription", short_description="Orçamento automático para oficinas e lojas · Atende AI (teste) · byGui")


def main():
    global TG
    token = re.sub(r"\s+", "", os.environ.get("TELEGRAM_BOT_TOKEN") or "")
    if not token:
        print("Defina TELEGRAM_BOT_TOKEN.", file=sys.stderr); sys.exit(2)
    TG = Telegram(token)
    me = TG.call("getMe", _t=15)
    if not me:
        log("getMe falhou; tentando de novo em 15 s"); time.sleep(15); sys.exit(1)
    log("Bot conectado: @" + me["username"])
    globals()["BOT_USER"] = me["username"]
    TG.call("deleteWebhook", drop_pending_updates=False)
    configurar(TG)
    db = DB(DB_PATH)
    ia = IA(); ia.testar()
    bot = Bot(TG, db, ia)
    criar_api(bot, ia)
    log("API em http://127.0.0.1:%d" % API_PORT)
    open(os.path.join(DATA, "bot.pid"), "w").write(str(os.getpid()))

    def laco_vigia():
        while True:
            try:
                bot.vigiar()
            except Exception:
                log("vigia:", traceback.format_exc())
            time.sleep(30)
    threading.Thread(target=laco_vigia, daemon=True, name="vigia").start()

    while True:
        ups = TG.call("getUpdates", _t=70, timeout=50, offset=(db.d["offset"] + 1) if db.d.get("offset") else None,
                      allowed_updates=["message", "callback_query"])
        if ups is None:
            time.sleep(3); continue
        for up in ups:
            db.d["offset"] = up["update_id"]
            bot.processar(up)
        open(os.path.join(DATA, "heartbeat"), "w").write(str(M.agora_ms()))


if __name__ == "__main__":
    main()
