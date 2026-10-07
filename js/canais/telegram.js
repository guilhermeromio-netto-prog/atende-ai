/* Adaptador Telegram (canal principal).
   Fase 2: Telegram Bot API via webhook num servidor pequeno. O token do bot NUNCA fica no navegador.
   Mapeamento: Chat.teclado → reply_markup.inline_keyboard (callback_data = valor); Chat.opcoes → reply_markup.keyboard. */
(function (AT) {
  'use strict';
  const U = AT.U;
  AT.Canais.registrar({
    id: 'telegram', nome: 'Telegram', icone: '✈️', disponivel: true, lido: '✓✓', mostrarRemetente: true,
    classe: 'cv--telegram',
    limiteBotoes: 8,
    moldura(opts) { return AT.Chat.molduraBase('cv--telegram', Object.assign({}, opts, { status: opts.status || 'bot' })); },
    teclado(botoes, ativo) {
      return '<div class="cv__teclado" role="group" aria-label="Botões da mensagem">' + botoes.slice(0, 8).map((b) =>
        '<button type="button" class="tecla" data-valor="' + U.esc(b.valor) + '"' + (ativo ? '' : ' disabled') + '>' + U.esc(b.rotulo) + '</button>').join('') + '</div>';
    }
  });
})(window.AT);
