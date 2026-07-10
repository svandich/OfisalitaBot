from telegram import Update
from telegram.ext import CallbackContext

from commands.decorators import command
from commands.base import Command
from config.logger import log_command
from utils import try_msg


@command(member_exclusive=True)
def slashear(update: Update, context: CallbackContext, cmd: Command) -> None:
    """
    Converts a phrase into a slash-ized version
    """
    log_command(update)
    arg = cmd.get_arg_or_reply()

    words = arg.split()
    response = "/" + words[0].lower()
    for word in words[1:]:
        response += word.capitalize()
    try_msg(
        context.bot,
        chat_id=update.message.chat_id,
        parse_mode="HTML",
        text=response,
    )


@command(member_exclusive=True)
def repetir(update: Update, context: CallbackContext, cmd: Command) -> None:
    """
    Repeats the text of a given message
    """
    log_command(update)
    arg = cmd.get_arg_or_reply()

    try_msg(
        context.bot,
        chat_id=update.message.chat_id,
        parse_mode="HTML",
        text=arg,
    )
