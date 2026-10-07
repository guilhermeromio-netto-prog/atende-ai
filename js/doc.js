/* Atende AI — renderizador mínimo de Markdown para os documentos do repositório (manual, playbook).
   Fonte única: os .md em docs/ são lidos pelo site; sem dependências externas. */
(function (AT) {
  'use strict';
  const REPO = 'https://github.com/guilhermeromio-netto-prog/atende-ai/blob/main/docs/';
  const esc = (s) => String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
  const slug = (s) => s.toLowerCase().normalize('NFD').replace(/[\u0300-\u036f]/g, '').replace(/<[^>]+>/g, '').replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '');

  function inline(s) {
    const cod = [];
    let h = esc(s).replace(/`([^`]+)`/g, (_, c) => { cod.push('<code>' + c + '</code>'); return '\u0000' + (cod.length - 1) + '\u0000'; });
    const links = [];
    h = h.replace(/\[([^\]]+)\]\(([^)\s]+)\)/g, (_, t, u) => {
      const href = /^(https?:|#|mailto:)/.test(u) ? u : REPO + u.replace(/^\.\//, '');
      links.push('<a href="' + href + '">' + t + '</a>'); return '\u0001' + (links.length - 1) + '\u0001';
    });
    h = h.replace(/(^|[\s(])(https?:\/\/[^\s<)]+?)([.,;:]?)(?=\s|\)|$)/g, (_, a, u, p) => a + '<a href="' + u + '">' + u + '</a>' + p);
    h = h.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>').replace(/(^|[\s(])\*([^*\s][^*]*)\*/g, '$1<em>$2</em>');
    return h.replace(/\u0001(\d+)\u0001/g, (_, i) => links[i]).replace(/\u0000(\d+)\u0000/g, (_, i) => cod[i]);
  }

  // nivel: soma ao nível dos títulos (1 = "#" vira <h2>), útil para embutir um documento numa página.
  function md(texto, nivel) {
    nivel = nivel || 0;
    const L = texto.replace(/\r/g, '').split('\n'); const out = []; const toc = [];
    let i = 0;
    const tit = (n, t) => { const h = Math.min(6, n + nivel); const id = slug(t); if (n === 2) toc.push({ id, t: t.replace(/\*\*/g, '') }); return '<h' + h + ' id="' + id + '">' + inline(t) + '</h' + h + '>'; };
    while (i < L.length) {
      const l = L[i];
      if (!l.trim()) { i++; continue; }
      let m;
      if (l.startsWith('```')) { const b = []; i++; while (i < L.length && !L[i].startsWith('```')) b.push(L[i++]); i++; out.push('<pre class="doc-pre">' + esc(b.join('\n')) + '</pre>'); continue; }
      if ((m = l.match(/^(#{1,4})\s+(.*)$/))) { out.push(tit(m[1].length, m[2])); i++; continue; }
      if (/^---+\s*$/.test(l)) { out.push('<hr>'); i++; continue; }
      if (l.startsWith('>')) { const b = []; while (i < L.length && L[i].startsWith('>')) b.push(L[i++].replace(/^>\s?/, '')); out.push('<blockquote>' + b.map(inline).join('<br>') + '</blockquote>'); continue; }
      if (l.startsWith('|')) {
        const rows = []; while (i < L.length && L[i].startsWith('|')) rows.push(L[i++]);
        const cel = (r) => r.replace(/^\||\|\s*$/g, '').split('|').map((c) => c.trim());
        const corpo = rows.slice(rows[1] && /^\|[\s:|-]+\|?\s*$/.test(rows[1]) ? 2 : 1);
        out.push('<div class="tabela-wrap"><table class="tabela doc-tab"><thead><tr>' + cel(rows[0]).map((c) => '<th scope="col">' + inline(c) + '</th>').join('') + '</tr></thead><tbody>' +
          corpo.map((r) => '<tr>' + cel(r).map((c) => '<td>' + inline(c) + '</td>').join('') + '</tr>').join('') + '</tbody></table></div>');
        continue;
      }
      if (/^\s*[-*]\s+/.test(l) || /^\s*\d+\.\s+/.test(l)) {
        const ord = /^\s*\d+\./.test(l); const it = [];
        while (i < L.length && (ord ? /^\s*\d+\.\s+/ : /^\s*[-*]\s+/).test(L[i])) {
          let t = L[i++].replace(ord ? /^\s*\d+\.\s+/ : /^\s*[-*]\s+/, '');
          const caixa = t.match(/^\[( |x)\]\s+/i);
          if (caixa) t = t.slice(caixa[0].length);
          it.push('<li' + (caixa ? ' class="doc-check"' : '') + '>' + (caixa ? (caixa[1] === ' ' ? '☐ ' : '☑ ') : '') + inline(t) + '</li>');
        }
        out.push(ord ? '<ol>' + it.join('') + '</ol>' : '<ul>' + it.join('') + '</ul>');
        continue;
      }
      const p = []; while (i < L.length && L[i].trim() && !/^(#{1,4}\s|>|\||```|---|\s*[-*]\s+|\s*\d+\.\s+)/.test(L[i])) p.push(L[i++]);
      if (!p.length) { p.push(L[i++]); }
      out.push('<p>' + p.map(inline).join('<br>') + '</p>');
    }
    return { html: out.join('\n'), toc };
  }

  async function carregar(arquivo) {
    const r = await fetch('docs/' + arquivo, { cache: 'no-cache' });
    if (!r.ok) throw new Error('HTTP ' + r.status);
    return r.text();
  }

  AT.Doc = { md, carregar, inline, REPO };
})(window.AT);
