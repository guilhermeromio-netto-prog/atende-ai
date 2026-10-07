/* Atende AI — Manual do lojista (#/manual). Fonte: docs/MANUAL-DO-LOJISTA.md. Pronto para imprimir ou salvar em PDF. */
(function (AT) {
  'use strict';
  const ARQ = 'MANUAL-DO-LOJISTA.md';
  async function render(main) {
    main.innerHTML = `
      <div class="manual-barra no-print">
        <div class="olho">Para lojistas e oficinas · piloto</div>
        <div class="manual-barra__acoes">
          <button type="button" class="btn btn--pri" id="man-print">🖨️ Imprimir ou salvar em PDF</button>
          <a class="btn btn--tg" href="https://t.me/Applojas10_bot?start=pro-lojavirtual">⭐ Começar pelo link Pro</a>
          <a class="btn" href="${AT.Doc.REPO + ARQ}">Ver no GitHub</a>
        </div>
      </div>
      <div class="manual-grade">
        <nav class="manual-toc no-print" aria-label="Seções do manual" id="man-toc"></nav>
        <article class="manual card" id="man-doc" aria-live="polite"><p class="muted">Carregando o manual…</p></article>
      </div>`;
    main.querySelector('#man-print').addEventListener('click', () => window.print());
    try {
      const r = AT.Doc.md(await AT.Doc.carregar(ARQ));
      const doc = main.querySelector('#man-doc'); if (!doc) return;
      doc.innerHTML = r.html;
      main.querySelector('#man-toc').innerHTML = '<p class="h3">Neste manual</p><ol>' + r.toc.map((x) => '<li><a href="#/manual" data-alvo="' + x.id + '">' + AT.Doc.inline(x.t.replace(/^\d+\.\s*/, '')) + '</a></li>').join('') + '</ol>';
      main.querySelectorAll('[data-alvo]').forEach((a) => a.addEventListener('click', (e) => {
        e.preventDefault(); const el = document.getElementById(a.dataset.alvo); if (el) el.scrollIntoView({ block: 'start', behavior: AT.U.reduzMov() ? 'auto' : 'smooth' });
      }));
    } catch (e) {
      const doc = main.querySelector('#man-doc');
      if (doc) doc.innerHTML = '<p>Não consegui carregar o manual aqui (' + AT.U.esc(e.message) + '). Leia direto no GitHub: <a href="' + AT.Doc.REPO + ARQ + '">MANUAL-DO-LOJISTA.md</a>.</p>';
    }
  }
  AT.V = AT.V || {};
  AT.V.manual = { titulo: 'Manual do lojista', render };
})(window.AT);
