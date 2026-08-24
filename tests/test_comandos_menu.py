"""El menú de comandos publicado en Telegram cubre todos los CommandHandler."""

from unittest.mock import AsyncMock, MagicMock

from telegram.ext import CommandHandler

from app.bot import handlers


def test_menu_cubre_todos_los_comandos():
    application = handlers.build_application()
    registrados = set()
    for grupo in application.handlers.values():
        for h in grupo:
            if isinstance(h, CommandHandler):
                registrados |= set(h.commands)
    en_menu = {c.command for c in handlers.COMANDOS_BOT}
    assert en_menu == registrados


async def test_registrar_comandos_publica_el_menu():
    application = MagicMock()
    application.bot.set_my_commands = AsyncMock()
    await handlers.registrar_comandos(application)
    application.bot.set_my_commands.assert_awaited_once_with(handlers.COMANDOS_BOT)
