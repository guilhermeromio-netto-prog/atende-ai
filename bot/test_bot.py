"""Teste ponta a ponta do bot com updates simulados (sem rede). Rode: python3 bot/test_bot.py"""
import json
import os
import sys
import tempfile
import urllib.request

os.environ["ATENDE_DATA"] = tempfile.mkdtemp(prefix="atende-test-")
os.environ["ATENDE_API_PORT"] = "8799"
os.environ["ATENDE_POSVENDA_MIN"] = "0"
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import atende_bot as B  # noqa: E402
import motor as M  # noqa: E402


class FakeTG(B.Telegram):
    def __init__(self):
        super().__init__("TESTE")
        self.saida = []

    def call(self, method, _t=40, **p):
        self.saida.append((method, p))
        return {"message_id": len(self.saida)}


tg = FakeTG(); B.TG = tg
db = B.DB(os.path.join(os.environ["ATENDE_DATA"], "db.json"))
ia = B.IA(); ia.ok = False
bot = B.Bot(tg, db, ia)
uid = [0]
DONO, CLI = 111, 222


def msg(chat, texto):
    uid[0] += 1
    bot.processar({"update_id": uid[0], "message": {"chat": {"id": chat, "type": "private"}, "from": {"first_name": "Teste%d" % chat}, "text": texto}})


def ultimo_teclado(chat):
    for m, p in reversed(tg.saida):
        if m == "sendMessage" and p.get("chat_id") == chat and p.get("reply_markup"):
            return p["reply_markup"]["inline_keyboard"]
    return []


def tocar(chat, contem):
    kb = ultimo_teclado(chat)
    b = next(b for linha in kb for b in linha if contem in b["text"] or contem == b["callback_data"])
    uid[0] += 1
    bot.processar({"update_id": uid[0], "callback_query": {"id": "c%d" % uid[0], "data": b["callback_data"], "from": {"first_name": "x"},
                                                          "message": {"chat": {"id": chat}, "reply_markup": {"inline_keyboard": kb}}}})


def textos(chat):
    return [p["text"] for m, p in tg.saida if m == "sendMessage" and p.get("chat_id") == chat]


ok = lambda c, m: print(("✅ " if c else "❌ ") + m) or (c or sys.exit(1))  # noqa: E731

# dono assume a oficina de exemplo e cadastra serviço
msg(DONO, "/dono"); tocar(DONO, "Assumir: Oficina")
t = db.tenant("oficina-pista-livre")
ok(t["donos"] == [DONO], "dono assumiu o negócio")
msg(DONO, "Polimento técnico R$ 350 a 480 3h")
ok(any(c["nome"] == "Polimento técnico" and c["duracao"] == 180 for c in t["catalogo"]), "cadastro pelo chat adicionou serviço")
msg(DONO, "Seg a sex 8h às 19h")
ok(t["horario"][1] == ["08:00", "19:00"], "horário atualizado pelo chat")

# cliente pelo deep link
msg(CLI, "/start oficina-pista-livre")
msg(CLI, "Meu Onix 2019 tá fazendo barulho ao frear")
msg(CLI, "Ana Souza")
msg(CLI, "ABC1D23")
tocar(CLI, "Nesta semana")
tk = db.d["tickets"][0]
ok(tk["status"] == "Orçado" and tk["total"] == {"min": 250, "max": 460}, "orçamento itemizado gerado (%s)" % tk["total"])
ok(tk["cliente"] == "Ana Souza" and tk["veiculo"] == "Onix 2019" and tk["placa"] == "ABC1D23", "dados do cliente coletados")
ok(any("Orçamento automático enviado" in x or "Orçamento enviado" in x for x in textos(DONO)), "dono notificado do orçamento")
tocar(CLI, "Aprovar")
ok(tk["status"] == "Aprovado", "cliente aprovou")
ok(any("Combinado" in x for x in textos(CLI)), "confirmação automática enviada ao cliente")
tocar(CLI, "📅")
ok(tk.get("agendamento") and any(e["regra"] == "lembrete" and e["estado"] == "agendado" for e in tk["eventos"]), "agendado e lembrete programado")

# dono avança status pelos botões
for alvo in ("Em serviço", "Pronto", "Entregue"):
    tocar(DONO, "Avançar para " + alvo)
    ok(tk["status"] == alvo, "dono avançou para " + alvo)
ok(any("está pronto" in x for x in textos(CLI)), "cliente recebeu 'carro pronto'")
bot.vigiar()
ok(any("1 a 5" in x for x in textos(CLI)), "pós-venda com nota 1–5 enviado pelo vigia")
tocar(CLI, "⭐⭐⭐⭐⭐")
ok(tk.get("nps5") == 5, "avaliação registrada")

# atendente humano + resposta do dono
msg(CLI, "/nova"); msg(CLI, "quero falar com atendente")
tk2 = db.d["tickets"][0]
ok(tk2["humano"], "pedido de atendente criou ticket")
tocar(DONO, "Responder cliente"); msg(DONO, "Oi! Já te ligo.")
ok(any("Já te ligo" in x for x in textos(CLI)), "resposta do dono chegou ao cliente")

# fallback sem intenção
msg(CLI, "/nova"); msg(CLI, "xyzzy blá")
ok(len(ultimo_teclado(CLI)) >= 3, "fallback oferece opções do catálogo")

# vigia de SLA
tk["prontoEm"] = None; tk["status"] = "Em serviço"; tk["prazo"] = M.agora_ms() - 60000; tk["alertas"] = {}
bot.vigiar()
ok(any("SLA estourado" in x for x in textos(DONO)), "vigia alertou SLA estourado")

# loja com retirada
msg(CLI, "/start casa-forte"); msg(CLI, "Quero pintar meu quarto"); msg(CLI, "Bia"); tocar(CLI, "retirar"); tocar(CLI, "Hoje")
tl = db.d["tickets"][0]
ok(tl["total"] == {"min": 380, "max": 560} and tl["bairro"] == "Retirada na loja", "loja: retirada sem frete")

# API
srv = B.criar_api(bot, ia)
base = "http://127.0.0.1:8799"
r = json.load(urllib.request.urlopen(base + "/api/saude"))
ok(r["ok"], "API /api/saude")
try:
    urllib.request.urlopen(base + "/api/pedidos?negocio=oficina-pista-livre&chave=errada"); ok(False, "chave errada deveria falhar")
except urllib.error.HTTPError as e:
    ok(e.code == 401, "API recusa chave errada")
req = urllib.request.Request(base + "/api/export?negocio=oficina-pista-livre", headers={"X-Atende-Chave": t["chave_api"], "Origin": "https://guilhermeromio-netto-prog.github.io"})
with urllib.request.urlopen(req) as resp:
    d = json.load(resp)
    ok(resp.headers.get("Access-Control-Allow-Origin") == "https://guilhermeromio-netto-prog.github.io", "CORS liberado para o GitHub Pages")
ok(len(d["pedidos"]) == 2 and all("chat_id" not in p for p in d["pedidos"]), "export sem chat_id, com %d pedidos" % len(d["pedidos"]))
ok(d["kpis"]["atendimentos"] == 2, "KPIs calculados")
if os.environ.get("ATENDE_DUMP"):
    json.dump(d, open(os.environ["ATENDE_DUMP"], "w"), ensure_ascii=False)
srv.shutdown()
print("\nTodos os testes passaram.")
