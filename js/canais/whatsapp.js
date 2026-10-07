/* Adaptador WhatsApp (em breve). Mesmo motor, outra aparência e outros limites:
   WhatsApp Cloud API aceita até 3 "reply buttons" por mensagem interativa. */
(function (AT) {
  'use strict';
  const U = AT.U;
  AT.Canais.registrar({
    id: 'whatsapp', nome: 'WhatsApp', icone: '🟢', disponivel: false, lido: '✓✓', mostrarRemetente: false,
    classe: 'cv--whatsapp',
    limiteBotoes: 3,
    moldura(opts) { return AT.Chat.molduraBase('cv--whatsapp', Object.assign({}, opts, { status: opts.status || 'conta comercial' })); },
    teclado(botoes, ativo) {
      return '<div class="cv__teclado" role="group" aria-label="Botões da mensagem">' + botoes.slice(0, 3).map((b) =>
        '<button type="button" class="tecla" data-valor="' + U.esc(b.valor) + '"' + (ativo ? '' : ' disabled') + '>' + U.esc(b.rotulo) + '</button>').join('') + '</div>';
    }
  });
})(window.AT);
