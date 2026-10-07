"""Teste ponta a ponta do bot com updates simulados (sem rede). Rode: python3 bot/test_bot.py"""
import json
import re
import os
import sys
import tempfile
import urllib.request

os.environ["ATENDE_DATA"] = tempfile.mkdtemp(prefix="atende-test-")
os.environ["ATENDE_API_PORT"] = "8799"
os.environ["ATENDE_POSVENDA_MIN"] = "0"
os.environ["ATENDE_SEM_REDE"] = "1"  # sem consulta ao ViaCEP nos testes
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
    bot.processar({"update_id": uid[0], "message": {"message_id": uid[0], "chat": {"id": chat, "type": "private"}, "from": {"first_name": "Teste%d" % chat}, "text": texto}})


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
ok("Termo de uso do piloto" in textos(DONO)[-1] and t["donos"] == [], "termo do piloto aparece antes de assumir (nada liberado ainda)")
msg(DONO, "/painel")
ok("donos de negócio" in textos(DONO)[-1], "sem aceite, comandos de dono continuam bloqueados")
tocar(DONO, "Aceito")
ok(t["termos"] and t["termos"][0]["chat"] == DONO and t["termos"][0]["aceitoEm"] > 0, "aceite do termo registrado com data/hora")
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

# ===================== Loja virtual (ecommerce)
DONO2, CLI2, CLI3 = 333, 444, 555
ok(db.tenant("loja-exemplo-online") and db.tenant("loja-exemplo-online")["segmento"] == "ecommerce", "loja de exemplo online semeada")
msg(DONO2, "/dono"); tocar(DONO2, "Criar meu negócio"); msg(DONO2, "Loja do Mano")
tocar(DONO2, "Loja virtual (catálogo vazio)")
ok(not any(x["nome"] == "Loja do Mano" for x in db.d["tenants"].values()), "loja só é criada depois do aceite")
tocar(DONO2, "Aceito")
t2 = next(x for x in db.d["tenants"].values() if x["nome"] == "Loja do Mano")
ok(t2["segmento"] == "ecommerce" and t2["catalogo"] == [] and t2.get("politicas"), "dono criou loja virtual vazia com políticas padrão")
msg(DONO2, "Fone bluetooth R$ 89 estoque 12 entrega 3 dias")
fone = next((c for c in t2["catalogo"] if c["nome"] == "Fone bluetooth"), None)
ok(fone and fone["preco"] == 89 and fone["estoque"] == 12 and fone["envioDias"] == 3, "produto cadastrado pelo chat (preço, estoque, envio)")
msg(DONO2, "Frete grátis acima de R$ 150. Pix com 10% de desconto, cartão em até 3x. Chave pix: mano@exemplo.com")
pg = t2["politicas"]["pagamento"]
ok(t2["politicas"]["frete"]["gratisAcima"] == 150 and pg["pixDescontoPct"] == 10 and pg["parcelas"] == 3 and pg["pixChave"] == "mano@exemplo.com", "políticas de frete/pagamento/Pix pelo chat")
msg(DONO2, "/politicas")
ok("Frete grátis acima de R$ 150,00" in textos(DONO2)[-1], "/politicas mostra o que foi cadastrado")
msg(DONO2, "/link")
ok(t2["id"] in textos(DONO2)[-1], "/link com deep link da loja")

msg(CLI2, "/start " + t2["id"])
msg(CLI2, "vcs tem fone blutooth?")
ok(any(b["callback_data"] == "add:" + fone["id"] for l in ultimo_teclado(CLI2) for b in l), "busca tolerante a erro achou o produto")
tocar(CLI2, "add:" + fone["id"]); tocar(CLI2, "➕ 1")
conv = db.user(CLI2)["conv"]
ok(conv["carrinho"] == {fone["id"]: 2}, "carrinho com quantidade 2")
tocar(CLI2, "Fechar pedido"); msg(CLI2, "Carlos Lima"); msg(CLI2, "01310-100"); msg(CLI2, "Av Paulista 1000 ap 12"); tocar(CLI2, "pg:pix")
resumo = textos(CLI2)[-1]
ok("Total: R$ 160,20" in resumo and "grátis" in resumo and "−R$ 17,80" in resumo, "resumo itemizado: frete grátis + desconto Pix (R$ 160,20)")
tocar(CLI2, "Confirmar pedido")
pe = db.d["tickets"][0]
ok(pe["id"].startswith("EC-") and pe["status"] == "Aguardando pagamento" and pe["totalFinal"] == 160.2, "pedido criado aguardando pagamento")
ok(any("mano@exemplo.com" in x for x in textos(CLI2)), "cliente recebeu a chave Pix do lojista")
ok(any("Novo pedido aguardando pagamento" in x for x in textos(DONO2)), "lojista notificado do pedido")
tocar(CLI2, "Já paguei")
ok(any("informou que pagou" in x for x in textos(DONO2)), "‘Já paguei’ avisou o lojista")
tocar(DONO2, "Confirmar pagamento")
ok(pe["status"] == "Pago" and fone["estoque"] == 10, "lojista confirmou pagamento e estoque baixou (12→10)")
ok(any("Pagamento confirmado" in x or "confirmado" in x.lower() for x in textos(CLI2)[-2:]), "cliente recebeu confirmação de pagamento")
tocar(DONO2, "Avançar para Separando")
ok(pe["status"] == "Separando", "pedido em separação")
tocar(DONO2, "Informar rastreio"); msg(DONO2, "BR123456789BR")
ok(pe["status"] == "Enviado" and pe["rastreio"] == "BR123456789BR" and pe.get("prontoEm"), "rastreio informado e pedido enviado")
ok(any("BR123456789BR" in x for x in textos(CLI2)), "cliente recebeu o código de rastreio")
msg(CLI2, "cade meu pedido " + pe["id"].lower())
ok("BR123456789BR" in textos(CLI2)[-1] and "Enviado" in textos(CLI2)[-1], "cliente consultou rastreio pelo número")
msg(CLI2, "quanto é o frete pro cep 30140-071?")
ok("Sudeste" in textos(CLI2)[-1] and "R$ 21,90" in textos(CLI2)[-1], "frete por CEP (região Sudeste)")
msg(CLI2, "quero trocar, veio com defeito"); tocar(CLI2, "tr:" + pe["id"]); tocar(CLI2, "Defeito")
tr = db.d["tickets"][0]
ok(tr["tipo"] == "troca" and tr["pedidoRef"] == pe["id"] and tr["motivo"] == "Defeito", "troca aberta com motivo e pedido")
ok(any("troca/devolução" in x for x in textos(DONO2)), "lojista notificado da troca")
tocar(DONO2, "Avançar para Em análise")
ok(tr["status"] == "Em análise", "troca em análise")
msg(CLI2, "quero 1 fone bluetooth")
ok(conv["carrinho"] == {fone["id"]: 1}, "pedido direto pelo texto adiciona ao carrinho")
conv["carrinhoEm"] -= 11 * 60000
bot.vigiar(); n1 = len(textos(CLI2)); bot.vigiar()
ok("carrinho" in textos(CLI2)[-1] and t2["metricas"]["abandonados"] == 1 and len(textos(CLI2)) == n1, "lembrete de carrinho abandonado (uma vez)")
k = B.kpis(t2, [x for x in db.d["tickets"] if x["tenant"] == t2["id"]])
ok(k["pedidos"] == 1 and k["pagos"] == 1 and k["faturamento"] == 160.2 and k["trocas"] == 1 and k["conversao"] == "50%", "KPIs da loja virtual (%s, conv %s)" % (k["faturamento"], k["conversao"]))
msg(DONO2, "/painel")
ok("Conversão carrinho" in textos(DONO2)[-1], "/painel por segmento")

msg(CLI3, "/start loja-exemplo-online")
ok("não faça" in textos(CLI3)[-1].lower() or "nenhum pagamento" in textos(CLI3)[-1], "loja de exemplo avisa: sem pagamento real")
msg(CLI3, "tem smartwach?")
ok(any("smartwatch" in b["callback_data"] for l in ultimo_teclado(CLI3) for b in l), "busca com erro de digitação (smartwach)")
msg(CLI3, "garafa termica")
ok("esgotado" in textos(CLI3)[-1], "produto sem estoque aparece como esgotado")
msg(CLI3, "atendente")
ok(db.d["tickets"][0]["tipo"] == "atendimento" and db.d["tickets"][0]["humano"], "loja virtual: pedir atendente abre ticket")

# migração segura de um banco antigo
antigo = {"versao": 1, "offset": 5, "seq": 3002, "usuarios": {"9": {"modo": "dono"}}, "tickets": [{"id": "OF-3001"}],
          "tenants": {"oficina-pista-livre": {"id": "oficina-pista-livre", "segmento": "oficina", "nome": "X", "donos": [9], "catalogo": [1, 2]}}}
pm = os.path.join(os.environ["ATENDE_DATA"], "antigo.json"); json.dump(antigo, open(pm, "w"))
dm = B.DB(pm).d
ok(dm["tenants"]["oficina-pista-livre"]["catalogo"] == [1, 2] and dm["tenants"]["oficina-pista-livre"]["donos"] == [9] and dm["tickets"] == [{"id": "OF-3001"}]
   and "loja-exemplo-online" in dm["tenants"] and dm["seq"] == 3002, "migração preserva dados e acrescenta a loja de exemplo")

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
req = urllib.request.Request(base + "/api/export?negocio=" + t2["id"], headers={"X-Atende-Chave": t2["chave_api"]})
d2 = json.load(urllib.request.urlopen(req))
ok(d2["politicas"]["pagamento"]["pixChave"] == "mano@exemplo.com" and d2["kpis"]["pedidos"] == 1 and d2["metricas"]["abandonados"] == 1, "API export da loja virtual com políticas e métricas")
if os.environ.get("ATENDE_DUMP"):
    json.dump(d2, open(os.environ["ATENDE_DUMP"].replace(".json", "-ecom.json"), "w"), ensure_ascii=False)
if os.environ.get("ATENDE_DUMP"):
    json.dump(d, open(os.environ["ATENDE_DUMP"], "w"), ensure_ascii=False)

# ===================== Plataforma: termo, privacidade, admin, piloto, exclusão
def cb(chat, data):
    uid[0] += 1
    bot.processar({"update_id": uid[0], "callback_query": {"id": "c%d" % uid[0], "data": data, "from": {"first_name": "x"},
                                                          "message": {"chat": {"id": chat}, "reply_markup": {"inline_keyboard": []}}}})


DONO4, ADMIN, ATAQ, CLI5 = 666, 777, 888, 999
msg(DONO4, "/dono"); tocar(DONO4, "Criar meu negócio"); msg(DONO4, "Loja Recusada"); tocar(DONO4, "Loja (catálogo vazio)"); tocar(DONO4, "Não aceito")
ok(not any(x["nome"] == "Loja Recusada" for x in db.d["tenants"].values()) and not db.user(DONO4)["dono_de"], "sem aceite (Não aceito) nada é criado")
t["termos"] = []  # dono antigo, de antes do termo
msg(DONO, "/painel")
ok("Termo de uso do piloto" in textos(DONO)[-1], "dono existente sem aceite vê o termo no próximo comando")
tocar(DONO, "Aceito")
ok("painel" in textos(DONO)[-1] and t["termos"], "depois do aceite o dono existente segue para o painel")
msg(CLI5, "/start casa-forte")
ok("/excluir_dados" in textos(CLI5)[-1] and "Atende AI" in textos(CLI5)[-1], "1ª mensagem ao cliente traz a nota de privacidade")
msg(CLI5, "/nova")
ok("/excluir_dados" not in textos(CLI5)[-1], "nota de privacidade só na 1ª conversa com o negócio")

# admin
for cmd in ("/plataforma", "/lojas", "/loja casa-forte", "/piloto casa-forte", "/admin_conectar", "/excluir_loja casa-forte"):
    msg(CLI5, cmd)
    ok("Acesso negado" in textos(CLI5)[-1], "não admin recebe 'Acesso negado' em " + cmd.split()[0])
cb(CLI5, "adm:del:casa-forte")
ok(db.tenant("casa-forte") and "Acesso negado" in textos(CLI5)[-1], "botão de excluir loja recusado para não admin")
msg(CLI5, "/admin ERRADO")
ok("código inválido" in textos(CLI5)[-1] and CLI5 not in db.d["plataforma"]["admins"], "/admin com código errado é negado")
for _ in range(5):
    msg(ATAQ, "/admin ADM000000000000")
msg(ATAQ, "/admin " + bot.admin_cfg["codigo"])
ok(ATAQ not in db.d["plataforma"]["admins"] and "Muitas tentativas" in textos(ATAQ)[-1], "5 tentativas erradas bloqueiam até o código certo")
ok(os.path.exists(os.path.join(os.environ["ATENDE_DATA"], "admin.json")) and bot.admin_cfg["codigo"].startswith("ADM"), "código admin gerado na 1ª execução em data/admin.json")
antes_n = len(tg.saida)
msg(ADMIN, "/admin " + bot.admin_cfg["codigo"].lower())
ok(ADMIN in db.d["plataforma"]["admins"] and "administrador da plataforma" in textos(ADMIN)[-1], "/admin com código certo vira super-admin")
ok(any(m == "deleteMessage" for m, p in tg.saida[antes_n:]), "mensagem com o código é apagada do chat")
msg(ADMIN, "/plataforma")
ok("Plataforma Atende AI" in textos(ADMIN)[-1] and "Faturamento intermediado" in textos(ADMIN)[-1], "/plataforma mostra KPIs globais")
msg(ADMIN, "/lojas")
ok(all(x in textos(ADMIN)[-1] for x in ("oficina-pista-livre", t2["id"], "loja-exemplo-online")), "/lojas lista todas as lojas")
msg(ADMIN, "/loja " + t2["id"])
ok("Saúde do piloto" in textos(ADMIN)[-1] and "Recentes" in textos(ADMIN)[-1], "/loja mostra KPIs, saúde do piloto e pedidos recentes")
msg(ADMIN, "/piloto " + t2["id"])
ok(t2["piloto"] is True and t2["pilotoInfo"]["inicio"] and "/antes" in textos(DONO2)[-1], "/piloto marca a loja e convida o dono a preencher o antes")
msg(DONO2, "/antes resposta 2h vendas R$ 8.000 pedidos 40")
ok(t2["pilotoInfo"]["antes"] == {**t2["pilotoInfo"]["antes"], "respostaMin": 120, "vendasMes": 8000, "pedidosMes": 40}, "dono preenche o antes (resposta, vendas, pedidos)")
msg(ADMIN, "/admin_conectar")
ok("Acesso negado" not in textos(ADMIN)[-1], "/admin_conectar responde ao admin")

# API admin
for nome_h, h in (("sem chave", {}), ("chave errada", {"X-Atende-Admin": "errada"}), ("chave de loja", {"X-Atende-Admin": t["chave_api"]})):
    try:
        urllib.request.urlopen(urllib.request.Request(base + "/api/admin/plataforma", headers=h)); ok(False, "API admin deveria recusar")
    except urllib.error.HTTPError as e:
        ok(e.code == 401, "API admin recusa " + nome_h)
req = urllib.request.Request(base + "/api/admin/export", headers={"X-Atende-Admin": bot.admin_cfg["chave_api"], "Origin": "https://guilhermeromio-netto-prog.github.io"})
with urllib.request.urlopen(req) as resp:
    ad = json.load(resp)
    ok("X-Atende-Admin" in (resp.headers.get("Access-Control-Allow-Headers") or "") or resp.headers.get("Access-Control-Allow-Origin"), "CORS na API admin")
ok(ad["plataforma"]["lojas"] == len(db.d["tenants"]) and any(x["id"] == t2["id"] and x["piloto"] and x["saude"]["antes"]["vendasMes"] == 8000 for x in ad["lojas"]), "API admin exporta lojas, piloto e antes/depois")
ok("Ana Souza" not in json.dumps(ad, ensure_ascii=False) and "chat" not in ad["lojas"][0]["recentes"][0], "API admin sem dados pessoais dos clientes")

# exclusão pelo cliente
msg(CLI, "/excluir_dados"); tocar(CLI, "Apagar meus dados"); tocar(CLI, "Sim, apagar")
dump = json.dumps(db.d, ensure_ascii=False)
ok("Ana Souza" not in dump and "ABC1D23" not in dump and str(CLI) not in db.d["usuarios"], "cliente apagou nome, placa e cadastro")
ok(tk["cliente"].startswith("Cliente (dados removidos)") and tk["chat"] == [] and tk["chat_id"] is None and tk["anonimizadoEm"] and tk["total"] == {"min": 250, "max": 460},
   "pedidos do cliente anonimizados (status e valor mantidos)")
ok(any("LGPD" in x for x in textos(DONO)), "dono avisado da exclusão")

# exclusão da loja pelo dono → admin
msg(DONO2, "/excluir_dados"); tocar(DONO2, "Pedir exclusão da loja")
ok(t2.get("exclusao") and any("Pedido de exclusão de loja" in x for x in textos(ADMIN)), "pedido de exclusão da loja notifica o admin")
tocar(ADMIN, "Excluir agora")
ok(not db.tenant(t2["id"]) and not any(x["tenant"] == t2["id"] for x in db.d["tickets"]) and not db.user(DONO2)["dono_de"], "admin excluiu a loja e os pedidos")
ok("foram excluídos" in textos(DONO2)[-1], "dono avisado da exclusão da loja")

# ===================== Secretário do dono (critérios de aceite da spec)
import secretario as SEC  # noqa: E402
from datetime import datetime, timedelta  # noqa: E402
agora_dt = datetime.now(M.TZ)
padrao = "hoje às 18h" if agora_dt.hour < 18 else "amanhã às 18h"
n0 = len(textos(DONO))
msg(DONO, "Agendar reunião com João, pagar conta de luz, lembrar de comprar leite")
novas = textos(DONO)[n0:]
tf = sorted(db.d["tarefas"], key=lambda x: x["id"])[-3:]
ag, ct, lb = (next(x for x in tf if x["tipo"] == tp) for tp in ("agenda.criar", "financeiro.pagar", "lembrete.criar"))
ok(novas[0].startswith("📝 <b>Encontrei 3 pedidos:</b>"), "lista numerada 'Encontrei 3 pedidos' antes de executar")
ok("1. Reunião com João — falta dia e hora." in novas[0] and "2. Conta de luz — falta vencimento." in novas[0] and ("3. Comprar leite — posso lembrar " + padrao) in novas[0], "lista diz o que falta em cada item (copy da spec)")
ok(len(novas) == 4 and all(("#" + x["id"]) in "".join(novas[1:]) for x in tf), "três pedidos geram três cartões, cada um com prova (#AG/#CT/#LB)")
ok(sum(1 for x in novas if "numa mensagem só" in x) == 1, "o que falta é perguntado numa mensagem só")
ok(ag["status"] == "aguardando_dado" and not ag["slots"].get("data") and "inicio" not in ag["slots"], "reunião NÃO é gravada sem data e hora")
ok(ct["status"] == "aguardando_dado" and not ct.get("pagoEm"), "conta sem vencimento aguarda dado, sem pagar")
ok(lb["status"] == "executada" and padrao in novas[3] and "horário padrão" in novas[3] and datetime.fromtimestamp(lb["slots"]["quando"] / 1000, M.TZ).hour == 18,
   "lembrete sem hora usa 18:00 local e declara na confirmação")
ok(all(re.fullmatch(r"([01]\d|2[0-3]):[0-5]\d", x["slots"]["hora"]) for x in db.d["tarefas"] if x["slots"].get("hora")) and not re.search(r"\b\d{1,2}:\d{3}", "".join(novas)), "sem horários inválidos")
n1 = len(textos(DONO))
msg(DONO, "João amanhã 15h, luz vence dia 12, leite hoje à noite")
novas = textos(DONO)[n1:]
amanha = (agora_dt + timedelta(days=1)).date().isoformat()
ok(ag["status"] == "executada" and ag["slots"]["data"] == amanha and ag["slots"]["hora"] == "15:00", "resposta numa frase completa a reunião (amanhã 15h) e grava")
ok(any("tarefa concluída:</b> reunião com joão agendada para amanhã às 15h" in x.lower() and "#" + ag["id"] in x for x in novas), "cartão de sucesso repete o título e cita a prova")
ok(ct["status"] == "aguardando_ok" and ct["slots"]["vencimento"].endswith("-12") and not ct.get("pagoEm"), "conta de luz registrada em aguardando_ok (nunca paga sozinha)")
ok(any("espera a sua confirmação" in x and "Não pago nada sem o seu ok" in x for x in novas), "cartão da conta pede o ok explícito")
ok(datetime.fromtimestamp(lb["slots"]["quando"] / 1000, M.TZ).hour == 20, "lembrete atualizado para 'hoje à noite' (20h)")
bot.vigiar()
ok(ct["status"] == "aguardando_ok" and not ct.get("pagoEm"), "vigia não marca conta como paga")
# lembrete dispara no horário
lb["disparo"] = M.agora_ms() - 1000; n2 = len(textos(DONO)); bot.vigiar()
ok(any("⏰ <b>Lembrete:</b> Comprar leite" in x and lb["id"] in x for x in textos(DONO)[n2:]) and lb["disparado"], "lembrete dispara no Telegram na hora")
n3 = len(textos(DONO)); bot.vigiar()
ok(len(textos(DONO)) == n3, "lembrete dispara uma vez só")
tocar(DONO, "+1h")
ok(not lb["disparado"] and lb["disparo"] > M.agora_ms() + 3500000, "botão +1h reagenda o lembrete")
# pagamento só com botão
msg(DONO, "/contas")
ok("aguardando seu ok" in textos(DONO)[-1] and ct["id"] in textos(DONO)[-1], "/contas lista a conta aguardando ok")
tocar(DONO, "Paguei " + ct["id"])
ok(ct["status"] == "executada" and ct.get("pagoEm") and ct["pagoPor"] == DONO, "conta só vira paga pelo botão explícito do dono")
msg(DONO, "/agenda")
ok("Reunião com João" in textos(DONO)[-1] and "amanhã às 15h" in textos(DONO)[-1], "/agenda lista a reunião")
msg(DONO, "/lembretes")
ok("Comprar leite" in textos(DONO)[-1], "/lembretes lista o lembrete")
# completo de primeira: executa sem perguntar; sem pessoa: pergunta com quem
n4 = len(textos(DONO))
msg(DONO, "Marcar visita com Dona Maria amanhã às 10h")
ok("numa mensagem só" not in textos(DONO)[n4] and db.d["tarefas"][-1]["status"] == "executada", "pedido completo é executado sem perguntas")
msg(DONO, "agendar reunião amanhã 10h")
ok(db.d["tarefas"][-1]["status"] == "aguardando_dado" and db.d["tarefas"][-1]["falta"] == ["pessoa"] and "com quem" in textos(DONO)[-2], "não inventa pessoa: pergunta com quem")
tocar(DONO, "Cancelar")
ok(db.d["tarefas"][-1]["status"] == "cancelada", "tarefa pode ser cancelada")
# intenções do negócio
msg(DONO, "ligar pro cliente Ana amanhã 9h, repor pastilha de freio 10 unidades")
lg, rp = db.d["tarefas"][-2], db.d["tarefas"][-1]
ok(lg["tipo"] == "cliente.ligar" and lg["slots"]["pessoa"] == "Ana" and rp["tipo"] == "estoque.repor" and rp["slots"]["quantidade"] == 10, "intenções do negócio: ligar pro cliente e repor estoque")
# cadastro de catálogo continua funcionando
msg(DONO, "Visita técnica R$ 100 1h")
ok(any(c["nome"] == "Visita técnica" for c in t["catalogo"]), "cadastro de catálogo não é confundido com pedido ao secretário")
# cliente não aciona o secretário
nt = len(db.d["tarefas"]); msg(CLI5, "lembrar de comprar leite")
ok(len(db.d["tarefas"]) == nt, "mensagem de cliente não cria tarefa do secretário")
# áudio
uid[0] += 1; bot.processar({"update_id": uid[0], "message": {"message_id": uid[0], "chat": {"id": DONO, "type": "private"}, "from": {"first_name": "x"}, "voice": {"file_id": "abc", "duration": 4}}})
ok("Pode mandar em texto" in textos(DONO)[-1] and len(db.d["tarefas"]) == nt, "áudio: pede texto com educação, sem fingir transcrição")
# API
try:
    urllib.request.urlopen(base + "/api/secretario?negocio=oficina-pista-livre&chave=errada"); ok(False, "deveria recusar")
except urllib.error.HTTPError as e:
    ok(e.code == 401, "API /api/secretario exige a chave da loja")
sd = json.load(urllib.request.urlopen(urllib.request.Request(base + "/api/secretario?negocio=oficina-pista-livre", headers={"X-Atende-Chave": t["chave_api"]})))
ok(sd["por_status"]["executada"] >= 3 and sd["por_status"]["cancelada"] == 1 and all("chat" not in x for x in sd["tarefas"]), "API /api/secretario lista tarefas por status (sem chat_id)")

# ============================================================ versão Pro (plug and play)
print("\n— versão Pro —")
PROD, PCLI = 1201, 1202
msg(PROD, "/start pro-lojavirtual")
ok("Passo 1/4" in textos(PROD)[-1] and "menos de 3 minutos" in textos(PROD)[-1], "Pro: o link abre o assistente no passo 1 (nome)")
msg(PROD, "Loja do Mano Pro")
ok("Passo 2/4" in textos(PROD)[-2] and "Termo de uso do piloto" in textos(PROD)[-1], "Pro: passo 2 mostra o termo do piloto")
ok(not any(x["nome"] == "Loja do Mano Pro" for x in db.d["tenants"].values()), "Pro: nada é criado antes do aceite")
tocar(PROD, "Aceito")
tm = next(x for x in db.d["tenants"].values() if x["nome"] == "Loja do Mano Pro")
ok(tm["plano"] == "pro" and tm["segmento"] == "ecommerce" and PROD in tm["donos"] and tm["termos"] and all(a["ativo"] for a in tm["automacoes"]) and not tm["catalogo"],
   "Pro: aceite cria a loja virtual Pro, vazia, com automações ligadas")
ok(tm["recursos"]["resumo_diario"] == "19:00" and tm["recursos"]["carrinho_abandonado"] and tm["recursos"]["posvenda"] and tm["recursos"]["alerta_sla"] and len(tm["modelos"]) >= 5,
   "Pro: recursos (carrinho, pós-venda, SLA, resumo 19h) e modelos de mensagem prontos")
ok("Passo 3/4" in textos(PROD)[-1], "Pro: segue direto para frete")
tocar(PROD, "Grátis acima de R$ 199"); tocar(PROD, "Pix 10% off")
msg(PROD, "Chave pix: mano.pro@email.com")
pol = tm["politicas"]
ok(pol["frete"]["tipo"] == "fixo" and pol["frete"]["gratisAcima"] == 199 and pol["pagamento"]["pixDescontoPct"] == 10 and pol["pagamento"]["parcelas"] == 6 and pol["pagamento"]["pixChave"] == "mano.pro@email.com",
   "Pro: presets de frete/pagamento e chave Pix aplicados")
ok("Passo 4/4" in textos(PROD)[-1], "Pro: passo 4 pede a lista de produtos")
msg(PROD, "Fone bluetooth; 89,90; 12; 3\nGarrafa térmica R$ 59 estoque 20 entrega 2 dias\nCabo USB-C,29.90,50,1\nxyz sem preço")
nomes = {c["nome"]: c for c in tm["catalogo"]}
ok(len(tm["catalogo"]) == 3 and nomes["Fone bluetooth"]["preco"] == 89.9 and nomes["Fone bluetooth"]["estoque"] == 12 and nomes["Cabo USB-C"]["envioDias"] == 1 and nomes["Garrafa térmica"]["estoque"] == 20,
   "Pro: importa lista em ‘;’, CSV e texto livre (3 produtos)")
ok("Não entendi" in textos(PROD)[-1] and "xyz sem preço" in textos(PROD)[-1], "Pro: avisa a linha que não entendeu")
tocar(PROD, "Concluir")
fim = textos(PROD)[-2]
bv = textos(PROD)[-1]
ok("Seja bem-vindo" in bv and "#/manual" in bv and "Piloto fundador" in bv and "/missao" in bv and "Primeiros 3 passos" in bv, "Pro: ao concluir chega o ‘Seja bem-vindo’ com manual, piloto fundador e 3 passos")
ok("está no ar" in fim and tm["proDuracaoSeg"] < 180 and bot.link(tm["id"]) in fim and "resumo diário às 19h" in fim, "Pro: loja pronta em menos de 3 min, com link e automações")
ok(not db.user(PROD).get("pro") and db.user(PROD)["modo"] == "dono", "Pro: assistente encerrado, dono no modo dono")
msg(PROD, "/manual")
ok("Seja bem-vindo" in textos(PROD)[-1] and "/cliente" in textos(PROD)[-1], "/manual reenvia as boas-vindas do dono")
msg(PROD, "/missao")
ok("Missão" in textos(PROD)[-1] and "versão 1" in textos(PROD)[-1] and "Humano no controle" in textos(PROD)[-1], "/missao mostra missão, visão e valores (versão 1)")
msg(PCLI, "/manual")
ok("Seja bem-vindo" in textos(PCLI)[-1] and "pro-lojavirtual" in textos(PCLI)[-1], "/manual para quem ainda não tem loja aponta o link Pro")
msg(PROD, "/plano")
ok("Plano Pro" in textos(PROD)[-1] and "Resumo diário às 19h" in textos(PROD)[-1] and "Secretário" in textos(PROD)[-1], "/plano lista os recursos do Pro")
msg(PROD, "/modelos")
ok(bot.link(tm["id"]) in textos(PROD)[-1] and "mano.pro@email.com" in textos(PROD)[-1], "/modelos traz textos prontos com link e chave Pix")
msg(DONO, "/plano")
ok("Plano Básico" in textos(DONO)[-1], "loja comum continua no plano Básico")
# cliente compra na loja Pro
msg(PCLI, "/start " + tm["id"]); msg(PCLI, "quero um fone")
ok("Adicionei 1x Fone bluetooth" in textos(PCLI)[-1], "Pro: cliente acha produto importado (busca)"); tocar(PCLI, "Fechar pedido")
msg(PCLI, "Ana Souza"); msg(PCLI, "01310-100"); msg(PCLI, "Rua A 10"); tocar(PCLI, "pg:pix"); tocar(PCLI, "Confirmar pedido")
pp = next(x for x in db.d["tickets"] if x["tenant"] == tm["id"])
ok(pp["tenant"] == tm["id"] and pp["status"] == "Aguardando pagamento" and any("mano.pro@email.com" in x for x in textos(PCLI)), "Pro: cliente fecha pedido e recebe a chave Pix")
tocar(PROD, "Confirmar pagamento")
ok(pp["status"] == "Pago", "Pro: dono confirma o pagamento pelo botão")
# resumo diário às 19h
from datetime import datetime as _dt
hoje = _dt.now(M.TZ)
h18 = int(hoje.replace(hour=18, minute=0, second=0, microsecond=0).timestamp() * 1000)
h19 = int(hoje.replace(hour=19, minute=5, second=0, microsecond=0).timestamp() * 1000)
tm["resumoEnviadoEm"] = None
for x in db.d["tenants"].values():
    if x["id"] != tm["id"]:
        x["resumoEnviadoEm"] = hoje.strftime("%Y-%m-%d")
n = len(textos(PROD)); nd = len(textos(DONO))
bot.pro_vigiar(h18)
ok(len(textos(PROD)) == n, "resumo diário não sai antes das 19h")
bot.pro_vigiar(h19)
rs = textos(PROD)[-1]
ok(len(textos(PROD)) == n + 1 and "Resumo do dia" in rs and "pagos hoje: <b>1</b>" in rs and "R$ 100,81" in rs and "Para separar/enviar: <b>1</b>" in rs, "resumo diário às 19h com pedidos, pagos e faturamento do dia")
bot.pro_vigiar(h19 + 600000)
ok(len(textos(PROD)) == n + 1 and len(textos(DONO)) == nd, "resumo sai uma vez por dia e só para lojas Pro")
msg(PROD, "/resumo")
ok("Resumo do dia" in textos(PROD)[-1], "/resumo sob demanda")
# admin liga/desliga Pro
msg(ATAQ, "/pro casa-forte")
ok("Acesso negado" in textos(ATAQ)[-1] and db.d["tenants"]["casa-forte"]["plano"] != "pro", "/pro negado para quem não é admin")
msg(ADMIN, "/pro casa-forte")
ok(db.d["tenants"]["casa-forte"]["plano"] == "pro", "admin liga o Pro com /pro slug")
msg(ADMIN, "/pro casa-forte off")
ok(db.d["tenants"]["casa-forte"]["plano"] == "basico", "admin volta para Básico com /pro slug off")
pn = json.load(urllib.request.urlopen(urllib.request.Request(base + "/api/pedidos?negocio=" + tm["id"], headers={"X-Atende-Chave": tm["chave_api"]})))
ok(pn["negocio"]["plano"] == "pro" and pn["negocio"]["recursos"]["resumo_diario"] == "19:00", "API do negócio informa o plano Pro (selo no dashboard)")
la = json.load(urllib.request.urlopen(urllib.request.Request(base + "/api/admin/lojas", headers={"X-Atende-Admin": bot.admin_cfg["chave_api"]})))
ok(any(x["id"] == tm["id"] and x["plano"] == "pro" for x in la["lojas"]), "API admin mostra o plano de cada loja")
srv.shutdown()
print("\nTodos os testes passaram.")
