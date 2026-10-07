/* Atende AI — roteador hash e casca da aplicação */
(function (AT) {
  'use strict';
  const U = AT.U;
  const ROTAS = { '': 'inicio', 'como-usar': 'comoUsar', onboarding: 'onboarding', atendimento: 'atendimento', pedidos: 'pedidos', dashboard: 'dashboard', config: 'config', admin: 'admin', privacidade: 'privacidade' };
  const main = document.getElementById('conteudo');
  let atual = null;

  function marcarSeg() {
    document.querySelectorAll('[data-seg]').forEach((b) => b.setAttribute('aria-pressed', String(b.dataset.seg === AT.S.seg())));
  }
  function rota() {
    const partes = (location.hash.replace(/^#\/?/, '') || '').split('/');
    const nome = ROTAS[partes[0]] ? partes[0] : '';
    const v = AT.V[ROTAS[nome]];
    document.getElementById('gaveta-raiz').innerHTML = '';
    document.querySelectorAll('.nav a').forEach((a) => { if (a.dataset.rota === nome) a.setAttribute('aria-current', 'page'); else a.removeAttribute('aria-current'); });
    document.title = v.titulo + ' · Atende AI (demonstração)';
    const mudou = atual !== nome; atual = nome;
    v.render(main, partes[1]);
    marcarSeg();
    ligarSeg(main);
    if (mudou) { window.scrollTo(0, 0); if (nome) main.focus({ preventScroll: true }); }
  }
  function trocarSeg(seg) {
    if (seg === AT.S.seg()) return;
    AT.S.st.segmento = seg; AT.S.salvar();
    U.toast('Segmento: ' + AT.S.segDef(seg).rotulo + ' · ' + AT.S.negocio().nome);
    if (/^#\/pedidos\//.test(location.hash)) history.replaceState(null, '', '#/pedidos');
    rota();
  }
  function ligarSeg(raiz) {
    raiz.querySelectorAll('[data-seg]').forEach((b) => { if (!b._lig) { b._lig = true; b.addEventListener('click', () => trocarSeg(b.dataset.seg)); } });
  }
  async function iniciar() {
    try { await AT.S.carregar(); }
    catch (e) {
      main.innerHTML = '<div class="card" role="alert"><h1>Não foi possível carregar a demonstração</h1><p>O arquivo <code>dados.json</code> não abriu. Se você abriu o <code>index.html</code> direto do disco, rode um servidor local (ex.: <code>python3 -m http.server</code>) ou use o link do GitHub Pages.</p></div>';
      return;
    }
    if (AT.S.conexao()) await AT.S.atualizarVivo();
    ligarSeg(document);
    window.addEventListener('hashchange', rota);
    rota();
    if (AT.S.vivoErro) U.toast('Modo conectado: ' + AT.S.vivoErro + '. Mostrando dados de exemplo.');
    setInterval(async () => {
      if (AT.S.conexao()) await AT.S.atualizarVivo();
      const lembrou = AT.ConversaEcom.vigiar();
      const v = AT.V[ROTAS[atual]]; if (v && v._tick) v._tick(lembrou);
    }, 30000);
  }
  iniciar();
})(window.AT);
