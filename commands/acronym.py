from telegram import Update, ParseMode, constants, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CallbackContext
from telegram.utils.helpers import escape_markdown

from commands.base import Command
import data
import re
from commands.decorators import command
from config.logger import log_command
from utils import try_msg, reverse_acronym, \
    generate_acronym


@command(member_exclusive=True)
def desiglar(update: Update, context: CallbackContext, cmd: Command) -> None:
    """
    Turns an acronym into its corresponding phrase
    """
    log_command(update)

    msg, reply = cmd.get_arg_and_reply()
    arg = msg if msg else reply

    message = data.Acronyms.get(arg.lower())

    if message is None:
        message = reverse_acronym(arg.lower())
        message += "\n<i>Para hacer una sigla real:</i> /siglar"

    try_msg(context.bot,
            chat_id=update.message.chat_id,
            parse_mode="HTML",
            text=message)

def confirm_siglar(update: Update, context: CallbackContext) -> None:
    """
    Result of confirm button to over-write an acronym
    """
    query = update.callback_query
    query.answer()

    if query.data == "siglar:no":
        response = "La sigla anterior se mantuvo"
    else:
        arg = re.search(r"(.*) reemplazaría a .*, ¿deseas siglar igual\?", query.message.text).group(1)
        acronym = generate_acronym(arg)
        data.Acronyms.set(acronym, arg)
        response = acronym

    query.edit_message_text(text=response, parse_mode="HTML")

@command(member_exclusive=True)
def siglar(update: Update, context: CallbackContext, cmd: Command) -> None:
    """
    Saves a phrase as an acronym
    """
    log_command(update)
    msg, reply = cmd.get_arg_and_reply()
    arg = msg if msg else reply

    acronym = generate_acronym(arg)
    old_acronym = data.Acronyms.get(acronym)

    message = acronym
    if old_acronym is not None and old_acronym != arg:
        keyboard = [
                        [
                            InlineKeyboardButton("Si 👍", callback_data="siglar:si"),
                            InlineKeyboardButton("¡No! 😱", callback_data="siglar:no")
                        ]
                   ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        update.message.reply_text(
                "<i>"+arg+"</i> reemplazaría a <i>"+old_acronym+"</i>, ¿deseas siglar igual?",
                reply_markup=reply_markup,
                parse_mode="HTML")
        return
    elif old_acronym == arg:
        message = "eypuv (ya se sigló una vez)"
    else:
        data.Acronyms.set(acronym, arg)

    try_msg(context.bot,
            chat_id=update.message.chat_id,
            parse_mode="HTML",
            text=message)


@command(member_exclusive=True)
def glosario(update: Update, context: CallbackContext, cmd: Command) -> None:
    """Sends a list of acronyms and meanings to the private chat
    of the user that called the command."""

    log_command(update)
    msg, reply = cmd.get_arg_and_reply()
    arg = msg if msg else reply

    if arg:
        if len(arg) > 1:
            try_msg(context.bot,
                    chat_id=update.message.chat_id,
                    parse_mode="HTML",
                    text="Este comando sólo puede invocarse "
                         "con 1 (un) caracter o ninguno.")
            return
        acronyms = data.Acronyms.list_by_letter(arg.lower())
        if not acronyms:
            try_msg(context.bot,
                    chat_id=update.message.chat_id,
                    parse_mode="HTML",
                    text=f"No encontré siglas que empiecen con {arg} :^(")
            return
    else:
        acronyms = data.Acronyms.list_all()

    acronyms.sort(key=lambda x: x[0])

    if update.message.from_user.id != update.message.chat_id:
        try_msg(context.bot,
                chat_id=update.message.chat_id,
                parse_mode="HTML",
                text="Enviaré la lista de siglas a tu chat privado ;^)")

    separator = "\n➖➖➖➖➖➖➖"
    msg = separator

    for idx, acro in enumerate(acronyms):
        definition = f"\n{acro[0]}\n{acro[1]}"

        if len(msg + definition + separator) > constants.MAX_MESSAGE_LENGTH:
            try_msg(context.bot,
                    chat_id=update.message.from_user.id,
                    parse_mode=ParseMode.MARKDOWN_V2,
                    text=escape_markdown(msg, version=2),
                    disable_web_page_preview=True)
            msg = separator

        msg += definition + separator

        if idx == len(acronyms) - 1:
            try_msg(context.bot,
                    chat_id=update.message.from_user.id,
                    parse_mode=ParseMode.MARKDOWN_V2,
                    text=escape_markdown(msg, version=2),
                    disable_web_page_preview=True)
