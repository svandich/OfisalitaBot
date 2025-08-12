from telegram import Update
from telegram.ext import CallbackContext

from commands.decorators import command
from commands.base import Command
from config.logger import log_command
from utils import try_msg, guard_editable_bot_message, try_edit

LIST_HASHTAG = "#LISTA"


@command(member_exclusive=True)
def lista(update: Update, context: CallbackContext, cmd: Command) -> None:
    """
    Starts an editable list
    """
    log_command(update)
    arg = cmd.get_arg_or_reply()
    message = f"{LIST_HASHTAG} {arg}:"

    try_msg(context.bot,
            chat_id=update.message.chat_id,
            parse_mode="HTML",
            text=message)


@command(member_exclusive=True)
def agregar(update: Update, context: CallbackContext, cmd: Command) -> None:
    """
    Adds an item to a list
    """
    if guard_editable_bot_message(update, context, LIST_HASHTAG):
        return

    content = update.message.reply_to_message.text
    lines = content.split("\n")
    lines_count = len(lines)

    addition = cmd.arg.replace("\n", " ")

    new_message = content + f"\n{lines_count}- " + addition

    try_edit(
        context.bot,
        chat_id=update.message.chat_id,
        parse_mode="HTML",
        message_id=update.message.reply_to_message.message_id,
        text=new_message
    )


@command(member_exclusive=True)
def quitar(update: Update, context: CallbackContext, cmd: Command) -> None:
    """
    Removes an item from a list
    """
    if guard_editable_bot_message(update, context, LIST_HASHTAG):
        return

    content = update.message.reply_to_message.text

    number = int(cmd.arg)
    number_dash = str(number) + "-"

    lines = content.split("\n")
    new_lines = []

    found_target = False
    for line in lines:
        if found_target:
            split_line = line.split("- ")
            number = str(int(split_line[0]) - 1)
            split_line[0] = number
            new_lines.append('- '.join(split_line))
        else:
            if line.startswith(number_dash):
                found_target = True
            else:
                new_lines.append(line)

    new_message = '\n'.join(new_lines)

    try_edit(
        context.bot,
        chat_id=update.message.chat_id,
        parse_mode="HTML",
        message_id=update.message.reply_to_message.message_id,
        text=new_message
    )


@command(member_exclusive=True)
def editar(update: Update, context: CallbackContext, cmd: Command) -> None:
    """
    Edits an item from a list
    """
    log_command(update)
    if guard_editable_bot_message(update, context, LIST_HASHTAG):
        return

    content = update.message.reply_to_message.text
    args = cmd.arg

    try:
        number = int(args[:args.find(" ")])
    except ValueError:
        return

    new_content = args[args.find(" ") + 1:]
    lines = content.split("\n")

    if number == 0:
        lines[0] = f"{LIST_HASHTAG} {new_content}:"
    elif number in range(1, len(lines) + 1):
        lines[number] = f"{number}- {new_content}"
    else:
        return

    new_message = '\n'.join(lines)

    if new_message == content:
        return

    try_edit(
        context.bot,
        chat_id=update.message.chat_id,
        parse_mode="HTML",
        message_id=update.message.reply_to_message.message_id,
        text=new_message
    )


@command(member_exclusive=True)
def deslistar(update: Update, context: CallbackContext) -> None:
    """
    Cierra una lista
    """
    if guard_editable_bot_message(update, context, LIST_HASHTAG):
        return

    content = update.message.reply_to_message.text
    new_message = content[1:]

    try_edit(
        context.bot,
        chat_id=update.message.chat_id,
        parse_mode="HTML",
        message_id=update.message.reply_to_message.message_id,
        text=new_message
    )
