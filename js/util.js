/* Atende AI — utilitários */
window.AT = window.AT || {};
(function (AT) {
  'use strict';
  const brl = new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL', maximumFractionDigits: 0 });
  const U = {};
  U.norm = (s) => String(s || '').toLowerCase().normalize('NFD').replace(/[\u0300-\u036f]/g, '').replace(/\s+/g, ' ').trim();
  U.esc = (s) => String(s == null ? '' : s).replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
  U.brl = (v) => brl.format(Math.round(v || 0));
  U.faixa = (min, max) => (Math.round(min) === Math.round(max) ? U.brl(min) : U.brl(min) + ' a ' + U.brl(max));
  U.faixaT = (min, max) => (!min && !max ? '—' : U.faixa(min, max));
  U.dur = (m) => {
    m = Math.round(m || 0);
    if (m < 60) return m + ' min';
    const h = Math.floor(m / 60), r = m % 60;
    return r ? h + 'h' + String(r).padStart(2, '0') : h + 'h';
  };
  U.cap = (s) => { s = String(s || '').trim(); return s.charAt(0).toUpperCase() + s.slice(1); };
  U.primeiroNome = (s) => String(s || '').trim().split(/\s+/)[0] || 'cliente';
  const dias = ['dom', 'seg', 'ter', 'qua', 'qui', 'sex', 'sáb'];
  U.diasCurto = dias;
  U.diasLongo = ['Domingo', 'Segunda', 'Terça', 'Quarta', 'Quinta', 'Sexta', 'Sábado'];
  U.hora = (ts) => new Date(ts).toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' });
  U.dataHora = (ts) => {
    const d = new Date(ts), hoje = new Date();
    const amanha = new Date(); amanha.setDate(hoje.getDate() + 1);
    const ontem = new Date(); ontem.setDate(hoje.getDate() - 1);
    const mesmo = (a, b) => a.toDateString() === b.toDateString();
    let dia;
    if (mesmo(d, hoje)) dia = 'hoje';
    else if (mesmo(d, amanha)) dia = 'amanhã';
    else if (mesmo(d, ontem)) dia = 'ontem';
    else dia = dias[d.getDay()] + ', ' + d.toLocaleDateString('pt-BR', { day: '2-digit', month: '2-digit' });
    return dia + ' às ' + U.hora(ts);
  };
  U.dataCurta = (ts) => new Date(ts).toLocaleDateString('pt-BR', { day: '2-digit', month: '2-digit' });
  U.restante = (ms) => {
    const neg = ms < 0; ms = Math.abs(ms);
    const min = Math.round(ms / 60000);
    const d = Math.floor(min / 1440), h = Math.floor((min % 1440) / 60), m = min % 60;
    let s = d ? d + 'd ' + h + 'h' : h ? h + 'h ' + String(m).padStart(2, '0') + 'min' : m + 'min';
    return neg ? 'estourado há ' + s : 'faltam ' + s;
  };
  U.tempoResp = (seg) => (seg < 60 ? Math.round(seg) + ' s' : seg < 3600 ? (seg / 60).toFixed(1).replace('.', ',') + ' min' : (seg / 3600).toFixed(1).replace('.', ',') + ' h');
  U.toMin = (hhmm) => { const [h, m] = String(hhmm).split(':').map(Number); return h * 60 + (m || 0); };
  U.fromMin = (m) => String(Math.floor(m / 60)).padStart(2, '0') + ':' + String(m % 60).padStart(2, '0');

  /** Soma minutos úteis respeitando o horário de funcionamento [dom..sáb] = ["08:00","18:00"] | null */
  U.somaUteis = (ts, minutos, horario) => {
    if (!horario || !horario.some(Boolean)) return ts + minutos * 60000;
    let d = new Date(ts); let resta = minutos; let guarda = 0;
    const proximoDia = () => { d.setDate(d.getDate() + 1); d.setHours(0, 0, 0, 0); };
    while (resta > 0 && guarda++ < 800) {
      const h = horario[d.getDay()];
      if (!h) { proximoDia(); continue; }
      const ab = U.toMin(h[0]), fe = U.toMin(h[1]);
      const agora = d.getHours() * 60 + d.getMinutes();
      if (agora < ab) { d.setHours(Math.floor(ab / 60), ab % 60, 0, 0); continue; }
      if (agora >= fe) { proximoDia(); continue; }
      const usa = Math.min(fe - agora, resta);
      d = new Date(d.getTime() + usa * 60000); resta -= usa;
    }
    return d.getTime();
  };
  /** Próximos horários livres de agendamento (início de bloco, de hora em hora) */
  U.proximosHorarios = (ts, horario, n) => {
    const out = []; let d = new Date(ts + 60 * 60000); d.setMinutes(0, 0, 0); let guarda = 0;
    while (out.length < n && guarda++ < 24 * 14) {
      const h = horario[d.getDay()];
      const m = d.getHours() * 60;
      if (h && m >= U.toMin(h[0]) && m + 60 <= U.toMin(h[1])) {
        out.push(d.getTime());
        d = new Date(d.getTime() + 3 * 3600000); // espaça as opções
      } else d = new Date(d.getTime() + 3600000);
    }
    return out;
  };
  U.template = (txt, vars) => String(txt || '').replace(/\{(\w+)\}/g, (m, k) => (vars[k] != null ? vars[k] : m));
  U.debounce = (fn, ms) => { let t; return (...a) => { clearTimeout(t); t = setTimeout(() => fn(...a), ms); }; };
  U.toast = (msg) => {
    const el = document.getElementById('toast'); if (!el) return;
    el.textContent = msg; el.classList.add('on');
    clearTimeout(U._tt); U._tt = setTimeout(() => el.classList.remove('on'), 2600);
  };
  U.baixar = (nome, conteudo, tipo) => {
    const blob = new Blob([conteudo], { type: tipo });
    const a = document.createElement('a'); a.href = URL.createObjectURL(blob); a.download = nome;
    document.body.appendChild(a); a.click(); setTimeout(() => { URL.revokeObjectURL(a.href); a.remove(); }, 500);
  };
  U.reduzMov = () => window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  U.faixaVivo = function () {
    const S = AT.S; if (!S) return '';
    if (S.vivoAtivo()) return '<div class="vivo" role="status"><strong>🟢 Modo conectado</strong> · dados ao vivo do bot de teste <a href="' + U.esc(S.vivo.negocio.link) + '">' + U.esc(S.vivo.negocio.link.replace('https://', '')) + '</a> · ' + U.esc(S.vivo.negocio.nome) + ' · atualizado às ' + U.hora(S.vivo.geradoEm) + ' (a cada 30 s) · <a href="#/config">gerenciar</a></div>';
    if (S.conexao() && S.vivoErro) return '<div class="vivo vivo--erro" role="status"><strong>⚠️ Modo conectado indisponível</strong> (' + U.esc(S.vivoErro) + '). O servidor de teste pode estar desligado. Mostrando dados de exemplo. <a href="#/config">Ver conexão</a></div>';
    if (S.vivo && !S.vivoAtivo()) return '<div class="vivo" role="status">🟢 Bot conectado ao segmento ' + (S.vivo.negocio.segmento === 'oficina' ? 'Oficina' : 'Loja') + '. Troque o segmento no topo para ver os dados ao vivo.</div>';
    return '';
  };
  AT.U = U;
})(window.AT);
