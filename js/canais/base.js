/* Atende AI — núcleo de conversa independente de canal.
   O motor (js/motor.js + js/conversa.js) produz mensagens neutras:
   { de: 'cliente'|'dono'|'bot'|'auto'|'atendente'|'sistema', texto, html?, teclado?: [{rotulo, valor}], ts }
   Cada adaptador em js/canais/ decide só a aparência e os limites do canal (ex.: nº de botões). */
(function (AT) {
  'use strict';
  const U = AT.U;
  const Canais = { lista: {}, padrao: 'telegram' };
  Canais.registrar = (a) => { Canais.lista[a.id] = a; };
  Canais.get = (id) => Canais.lista[id] || Canais.lista[Canais.padrao];
  Canais.atual = () => Canais.get((AT.S && AT.S.st && AT.S.st.canal) || Canais.padrao);
  AT.Canais = Canais;

  const Chat = {};
  Chat.bolha = function (m, ladoDireito, ativo, canal) {
    canal = canal || Canais.atual();
    if (m.de === 'sistema') return '<div class="bolha bolha--sis">' + U.esc(m.texto) + '</div>';
    const direita = ladoDireito.includes(m.de);
    const corpo = m.html ? m.html : U.esc(m.texto).split(/\n+/).map((l) => '<p>' + l + '</p>').join('');
    let rot = '';
    if (m.de === 'bot') rot = '<span class="bolha__ia">IA simulada</span>';
    if (m.de === 'auto') rot = '<span class="bolha__auto">Automação</span>';
    if (m.de === 'atendente') rot = '<span>Atendente</span>';
    const de = !direita && canal.mostrarRemetente && m.de === 'atendente' ? '<span class="bolha__de">Atendente humano</span>' : '';
    const teclado = m.teclado && m.teclado.length ? canal.teclado(m.teclado, ativo) : '';
    return '<div class="msg ' + (direita ? 'msg--out' : 'msg--in') + '"><div class="bolha">' + de + corpo +
      '<div class="bolha__meta">' + rot + '<span>' + U.hora(m.ts) + '</span>' + (direita ? '<span aria-hidden="true">' + canal.lido + '</span>' : '') + '</div></div>' + teclado + '</div>';
  };
  Chat.render = function (log, msgs, ladoDireito, canal) {
    const ultimo = msgs.length - 1;
    log.innerHTML = msgs.map((m, i) => Chat.bolha(m, ladoDireito, i === ultimo, canal)).join('');
    log.scrollTop = log.scrollHeight;
  };
  Chat.moldura = function (opts) { return (opts.canal || Canais.atual()).moldura(opts); };
  Chat.digitando = function (log, on) {
    const ex = log.querySelector('.digitando');
    if (on && !ex) { log.insertAdjacentHTML('beforeend', '<div class="digitando" aria-label="digitando"><i></i><i></i><i></i></div>'); log.scrollTop = log.scrollHeight; }
    if (!on && ex) ex.remove();
  };
  Chat.atraso = () => (U.reduzMov() ? 150 : 650 + Math.random() * 350);
  /** teclado de respostas (reply keyboard), abaixo da caixa de texto */
  Chat.opcoes = function (box, lista, onEscolha) {
    box.innerHTML = (lista || []).map((o, i) => '<button type="button" class="opcao" data-i="' + i + '">' + U.esc(o) + '</button>').join('');
    box.querySelectorAll('.opcao').forEach((b) => b.addEventListener('click', () => onEscolha(lista[+b.dataset.i])));
  };
  /** botões presos à mensagem (inline keyboard) */
  Chat.ligarTeclado = function (log, cb) {
    log.addEventListener('click', (e) => {
      const b = e.target.closest('.tecla'); if (!b || b.disabled) return;
      cb(b.dataset.valor, b.textContent);
    });
  };
  /** cabeçalho/corpo padrão; adaptadores usam e trocam só a classe de tema */
  Chat.molduraBase = function (classe, opts) {
    return '<div class="cv ' + classe + '" id="' + opts.id + '">' +
      '<div class="cv__topo"><div class="cv__avatar" aria-hidden="true">' + U.esc(opts.avatar) + '</div><div><div class="cv__nome">' + U.esc(opts.nome) + '</div><div class="cv__status">' + U.esc(opts.status) + '</div></div><span class="cv__demo">Demonstração —<br>IA simulada</span></div>' +
      '<div class="cv__log" role="log" aria-live="polite" aria-label="Conversa"></div>' +
      '<div class="cv__opcoes" aria-label="Sugestões de resposta"></div>' +
      '<form class="cv__form" autocomplete="off"><label class="sr" for="' + opts.id + '-in">' + U.esc(opts.label) + '</label><input id="' + opts.id + '-in" type="text" placeholder="' + U.esc(opts.placeholder) + '" maxlength="400"><button class="cv__enviar" type="submit" aria-label="Enviar">➤</button></form></div>';
  };
  Chat.botUser = function (nome) {
    const base = U.norm(nome).replace(/[^a-z0-9 ]/g, '').split(' ').filter(Boolean).map(U.cap).join('').slice(0, 24);
    return '@' + (base || 'Atende') + 'Bot';
  };
  AT.Chat = Chat;
})(window.AT);
