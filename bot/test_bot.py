"""Teste ponta a ponta do bot com updates simulados (sem rede). Rode: python3 bot/test_bot.py"""
import json
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
srv.shutdown()
print("\nTodos os testes passaram.")
