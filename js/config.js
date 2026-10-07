/* Atende AI — configurações: automações, SLA, canais e dados */
(function (AT) {
  'use strict';
  const U = AT.U, M = AT.M;
  const S = () => AT.S;

  function exemploVars() {
    const t = S().ticketsSeg().find((x) => x.itens && x.itens.length) || null;
    if (t) return M.vars(t);
    return { cliente: 'Carla', servico: 'troca de óleo', prazo: 'hoje às 17:00', valor: 'R$ 180', negocio: S().negocio().nome, veiculo: 'Onix 2019', placa: 'ABC1D23' };
  }

  function render(main) {
    const seg = S().seg(); const regras = S().st.automacoes[seg]; const sla = S().st.sla[seg]; const P = S().dados.prioridades;
    const vars = exemploVars();
    main.innerHTML = `
      <div class="cab"><div><div class="olho">Passo 5 · Regras do negócio</div><h1>Configurações</h1>
      <p>Edite as mensagens automáticas, o SLA por prioridade e os dados da demonstração. Vale para o segmento <strong>${seg === 'oficina' ? 'Oficina' : 'Loja'}</strong>.</p></div></div>
      <div class="grade">
        <section class="card" aria-labelledby="h-auto">
          <h2 id="h-auto">Automações (cadeia de mensagens)</h2>
          <p class="pequeno muted">Variáveis disponíveis: <code>{cliente}</code> <code>{servico}</code> <code>{prazo}</code> <code>{valor}</code> <code>{negocio}</code> <code>{veiculo}</code> <code>{placa}</code>. A prévia usa um pedido real da lista.</p>
          <div id="cf-regras">${regras.map((r, i) => `
            <div class="regra" data-i="${i}">
              <input type="checkbox" class="toggle" id="cf-on-${i}" ${r.ativo ? 'checked' : ''} aria-describedby="cf-q-${i}">
              <div>
                <label for="cf-on-${i}"><strong>${U.esc(r.nome)}</strong></label>
                <div class="pequeno muted" id="cf-q-${i}">Dispara no status <strong>${U.esc(r.gatilho)}</strong> · ${U.esc(r.quando)}</div>
                <label class="sr" for="cf-t-${i}">Texto da mensagem: ${U.esc(r.nome)}</label>
                <textarea id="cf-t-${i}" style="margin-top:8px">${U.esc(r.template)}</textarea>
                <div class="pre" aria-live="polite"><strong>Prévia:</strong> <span>${U.esc(U.template(r.template, vars))}</span></div>
              </div>
            </div>`).join('')}</div>
        </section>
        <section class="card" aria-labelledby="h-sla">
          <h2 id="h-sla">SLA por prioridade</h2>
          <p class="pequeno muted">Resposta: tempo máximo até a 1ª resposta humana quando o cliente pede atendente. Conclusão: horas úteis (dentro do horário de funcionamento) até o pedido ficar pronto. Vale para novos pedidos.</p>
          <div class="tabela-wrap"><table><thead><tr><th>Prioridade</th><th>Resposta (min)</th><th>Conclusão (horas úteis)</th></tr></thead><tbody>
            ${Object.keys(P).map((k) => `<tr><th scope="row" style="text-transform:none;font-size:.95rem">${P[k]}</th>
              <td><input class="inp num" type="number" min="1" data-p="${k}" data-k="respostaMin" value="${sla[k].respostaMin}" aria-label="Resposta em minutos, prioridade ${P[k]}" style="width:110px"></td>
              <td><input class="inp num" type="number" min="1" data-p="${k}" data-k="conclusaoHoras" value="${sla[k].conclusaoHoras}" aria-label="Conclusão em horas úteis, prioridade ${P[k]}" style="width:110px"></td></tr>`).join('')}
          </tbody></table></div>
        </section>
        <section class="card" aria-labelledby="h-canais">
          <h2 id="h-canais">Canais</h2>
          <div class="tabela-wrap"><table><thead><tr><th>Canal</th><th>Situação</th><th>Como funcionará na fase 2</th></tr></thead><tbody>
            <tr><td>✈️ Telegram</td><td><span class="chip chip--ok">Canal principal · simulado aqui</span></td><td>Telegram Bot API via webhook num servidor pequeno. Gratuito e sem aprovação prévia. O token do bot fica só no servidor, nunca no navegador.</td></tr>
            <tr><td>🟢 WhatsApp</td><td><span class="chip chip--atencao">Em breve</span></td><td>Segundo adaptador do mesmo motor, via WhatsApp Cloud API (Meta), com conta comercial verificada e modelos de mensagem aprovados.</td></tr>
          </tbody></table></div>
        </section>
        <section class="card" aria-labelledby="h-cx">
          <h2 id="h-cx">Modo conectado (bot de teste no Telegram)</h2>
          <p class="pequeno muted">Liga Pedidos e Dashboard aos dados reais do bot <a href="https://t.me/Applojas10_bot">@Applojas10_bot</a>. O jeito mais fácil: no Telegram, como dono, envie <code>/conectar</code> e abra o link que o bot mandar. A chave só lê os pedidos do seu negócio. Sem conexão, o app usa os dados de exemplo.</p>
          <div id="cx-status" style="margin-bottom:10px">${S().vivo ? '<span class="chip chip--ok">Conectado: ' + U.esc(S().vivo.negocio.nome) + ' · ' + S().vivo.pedidos.length + ' pedido(s)</span>' : S().conexao() ? '<span class="chip chip--atencao">Sem resposta da API' + (S().vivoErro ? ': ' + U.esc(S().vivoErro) : '') + '</span>' : '<span class="chip">Desconectado · usando dados de exemplo</span>'}</div>
          <form id="cx-form" class="filtros" style="margin:0">
            <label class="campo" style="flex:2;min-width:240px">Endereço da API<input class="inp" id="cx-api" type="url" placeholder="https://….trycloudflare.com" value="${U.esc((S().conexao() || {}).api || '')}" required></label>
            <label class="campo">Negócio (id)<input class="inp" id="cx-neg" placeholder="oficina-pista-livre" value="${U.esc((S().conexao() || {}).negocio || '')}" required></label>
            <label class="campo">Chave de leitura<input class="inp" id="cx-chave" type="password" autocomplete="off" value="${U.esc((S().conexao() || {}).chave || '')}" required></label>
            <button class="btn btn--pri" type="submit">Conectar</button>
            ${S().conexao() ? '<button class="btn" type="button" id="cx-sair">Desconectar</button>' : ''}
          </form>
        </section>
        <section class="card" aria-labelledby="h-dados">
          <h2 id="h-dados">Dados da demonstração</h2>
          <p class="pequeno muted">Tudo fica salvo só neste navegador (localStorage). Os ${S().dados.ticketsExemplo.length} pedidos iniciais são dados de exemplo fictícios.</p>
          <div class="linha">
            <button type="button" class="btn" id="cf-exp">⬇️ Exportar JSON</button>
            <label class="btn" for="cf-imp" tabindex="0" id="cf-imp-rot">⬆️ Importar JSON</label><input type="file" id="cf-imp" accept="application/json,.json" class="sr">
            <button type="button" class="btn btn--perigo" id="cf-reset">↺ Restaurar dados de exemplo</button>
          </div>
        </section>
      </div>`;
    main.querySelectorAll('.regra').forEach((el) => {
      const r = regras[+el.dataset.i]; const ta = el.querySelector('textarea'); const pre = el.querySelector('.pre span');
      el.querySelector('.toggle').addEventListener('change', (e) => { r.ativo = e.target.checked; S().salvar(); U.toast(r.nome + (r.ativo ? ' ligada' : ' desligada')); });
      ta.addEventListener('input', () => { pre.textContent = U.template(ta.value, vars); });
      ta.addEventListener('change', () => { r.template = ta.value.trim() || r.template; S().salvar(); U.toast('Mensagem salva'); });
    });
    main.querySelectorAll('[data-p]').forEach((i) => i.addEventListener('change', () => {
      sla[i.dataset.p][i.dataset.k] = Math.max(1, +i.value || 1); S().salvar(); U.toast('SLA atualizado');
    }));
    main.querySelector('#cx-form').addEventListener('submit', async (e) => {
      e.preventDefault();
      const cx = { api: main.querySelector('#cx-api').value.trim().replace(/\/+$/, ''), negocio: main.querySelector('#cx-neg').value.trim(), chave: main.querySelector('#cx-chave').value.trim() };
      const ok = await S().conectar(cx);
      U.toast(ok ? 'Conectado ao bot: ' + S().vivo.negocio.nome : 'Não conectou: ' + S().vivoErro);
      render(main);
    });
    const sair = main.querySelector('#cx-sair');
    if (sair) sair.addEventListener('click', () => { S().desconectar(); U.toast('Desconectado. Voltando aos dados de exemplo.'); render(main); });
    main.querySelector('#cf-exp').addEventListener('click', () => { U.baixar('atende-ai-dados.json', JSON.stringify(S().st, null, 1), 'application/json'); U.toast('JSON exportado'); });
    const rot = main.querySelector('#cf-imp-rot');
    rot.addEventListener('keydown', (e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); main.querySelector('#cf-imp').click(); } });
    main.querySelector('#cf-imp').addEventListener('change', (e) => {
      const file = e.target.files[0]; if (!file) return;
      const fr = new FileReader();
      fr.onload = () => {
        try {
          const d = JSON.parse(fr.result);
          if (!d || !Array.isArray(d.tickets) || !d.catalogos || !d.negocios) throw new Error('formato');
          d.versao = S().dados.versao; S().st = d; S().salvar(); U.toast('Dados importados'); render(main);
        } catch (err) { U.toast('Arquivo inválido: use um JSON exportado pelo Atende AI.'); }
      };
      fr.readAsText(file);
    });
    main.querySelector('#cf-reset').addEventListener('click', () => {
      if (!confirm('Restaurar os dados de exemplo? Pedidos, catálogo e regras criados nesta demonstração serão apagados deste navegador.')) return;
      S().resetar(); U.toast('Dados de exemplo restaurados'); render(main);
    });
  }
  AT.V = AT.V || {};
  AT.V.config = { titulo: 'Configurações', render };
})(window.AT);
