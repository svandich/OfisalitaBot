from telegram import Update
from telegram.ext import CallbackContext

from commands.base import Command
from commands.decorators import command
from config.logger import log_command
from utils import get_arg, try_msg, guard_editable_bot_message, try_edit

COUNTER_HASHTAG = "#CONTADOR"


@command(member_exclusive=True)
def contador(update: Update, context: CallbackContext, cmd: Command) -> None:
    """
    Starts an editable counter
    """
    log_command(update)
    arg = cmd.get_arg_or_reply().replace("\n", " ")
    message = f"{COUNTER_HASHTAG} {arg}:\n0"

    try_msg(context.bot,
            chat_id=update.message.chat_id,
            parse_mode="HTML",
            text=message)


@command(member_exclusive=True)
def sumar(update: Update, context: CallbackContext, cmd: Command, sign: int = 1) -> None:
    """
    Adds a number to a counter (default 1)
    """
    if guard_editable_bot_message(update, context, COUNTER_HASHTAG):
        return

    content = update.message.reply_to_message.text
    lines = content.split("\n")

    previous_number = int(lines[-1])

    addition = int(cmd.arg) if cmd.arg else 1

    addition *= sign

    lines[-1] = previous_number + addition

    new_message = "\n".join([str(item) for item in lines])

    try_edit(
        context.bot,
        chat_id=update.message.chat_id,
        parse_mode="HTML",
        message_id=update.message.reply_to_message.message_id,
        text=new_message
    )


@command(member_exclusive=True)
def restar(update: Update, context: CallbackContext) -> None:
    """
    Subtracts a number to a counter (default 1)
    """
    sumar(update, context, -1)
