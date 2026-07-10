from datetime import datetime, time as time_type

from telegram import Message, Update, Bot, TelegramError, constants as tg_constants
from telegram.ext import CallbackContext

from config.logger import logger


def _try_send(
    bot: Bot, attempts: int, function: callable, error_message: str, **params
):
    """
    Make multiple attempts to send a message.
    """
    chat_id = params["chat_id"]
    attempt = 1
    while attempt <= attempts:
        try:
            ret = function(**params)
        except TelegramError as e:
            logger.error(
                (
                    f"[Attempt {attempt}/{attempts}] {error_message} {chat_id} "
                    f"raised following error: {type(e).__name__}: {e}"
                )
            )
        else:
            break
        attempt += 1

    if attempt > attempts:
        logger.error(
            (
                f"Max attempts reached for chat {str(chat_id)}."
                "Aborting message and raising exception."
            )
        )

    return ret


def try_msg(bot: Bot, attempts: int = 2, **params) -> None:
    """
    Make multiple attempts to send a text message.
    """
    error_message = "Messaging chat"
    _try_send(bot, attempts, bot.send_message, error_message, **params)


def try_edit(bot: Bot, attempts: int = 2, **params) -> None:
    """
    Make multiple attempts to edit a message.
    """
    error_message = f"Editing message {params['message_id']} in chat"
    _try_send(bot, attempts, bot.edit_message_text, error_message, **params)


def try_sticker(bot: Bot, attempts: int = 2, **params) -> None:
    """
    Make multiple attempts to send a sticker.
    """
    error_message = "Stickering chat"
    _try_send(bot, attempts, bot.send_sticker, error_message, **params)


def try_delete(bot: Bot, attempts: int = 2, **params) -> None:
    """
    Make multiple attempts to delete a message.
    """
    error_message = f"Deleting message {params['message_id']} in chat"
    _try_send(bot, attempts, bot.delete_message, error_message, **params)


def send_long_message(bot: Bot, **params) -> None:
    """
    Recursively breaks long texts into multiple messages,
    prioritizing newlines for slicing.
    """
    text = params.pop("text", "")

    params_copy = params.copy()
    maxl = params.pop("max_length", tg_constants.MAX_MESSAGE_LENGTH)
    slice_str = params.pop("slice_str", "\n")
    if len(text) > maxl:
        slice_index = text.rfind(slice_str, 0, maxl)
        if slice_index <= 0:
            slice_index = maxl
        sliced_text = text[:slice_index]
        rest_text = text[slice_index + 1 :]
        try_msg(bot, text=sliced_text, **params)
        send_long_message(bot, text=rest_text, **params_copy)
    else:
        try_msg(bot, text=text, **params)


def get_arg(update: Update) -> str:
    """
    Returns the argument of a command.

    DEPRECATED: Use Command.arg instead.
    """
    try:
        arg = update.message.text[(update.message.text.index(" ") + 1) :]
    except ValueError:
        arg = ""
    return arg


def get_arg_reply(update: Update) -> str:
    """
    Returns the argument of a command or the text of a reply.
    (Preference towards replies)

    DEPRECATED: Use Command.get_reply_or_arg() instead.
    """
    if update.message.reply_to_message is None:
        return get_arg(update)
    try:
        arg = update.message.reply_to_message.text
    except AttributeError:
        arg = ""
    return arg


def get_text_or_caption(msg: Message) -> str:
    """
    Returns the text of the message argument, or the caption if no text is available.
    This handles messages that have media and captions,
    which apparently don't have a valid text field.
    """
    return msg.text if msg.text else msg.caption


def guard_reply_to_message(update: Update) -> bool:
    """
    Guard statement:
    Verifies if a message is a reply.
    To be used in conjunction with a return.
    False if the code should keep running.
    True if the code should stop running.
    """
    return not update.message.reply_to_message


def guard_reply_to_bot_message(update: Update, context: CallbackContext) -> bool:
    """
    Guard statement:
    Verifies if a reply is replying to a message from the actual bot.
    To be used in conjunction with a return.
    False if the code should keep running.
    True if the code should stop running.
    """
    return context.bot.id != update.message.reply_to_message.from_user.id


def guard_hashtag(content: str, match: str) -> bool:
    """
    Guard statement:
    Verifies if a reply is replying to a message from the actual bot.
    To be used in conjunction with a return.
    False if the code should keep running.
    True if the code should stop running.
    """
    return not content.startswith(match)


def guard_editable_bot_message(
    update: Update, context: CallbackContext, match: str
) -> bool:
    """
    Guard statement:
    Verifies if a reply is replying to a message from the actual bot that
    begins with a specific hashtag.
    To be used in conjunction with a return.
    False if the code should keep running.
    True if the code should stop running.
    """
    if guard_reply_to_message(update):
        return True

    if guard_reply_to_bot_message(update, context):
        return True

    if guard_hashtag(update.message.reply_to_message.text, match):
        return True

    return False


def strip_quotes(string: str) -> str:
    """
    Removes a single pair of matching quotation marks from the beginning and
    end of the string if they exist.

    Examples:
        "Hello" -> Hello    # Removed

        'This is a "test"' -> This is a "test"  # Removed

        Baloian said "Hello" -> Baloian said "Hello"    # Not removed
    """
    if (
        string.startswith('"')
        and string.endswith('"')
        or string.startswith("'")
        and string.endswith("'")
    ):
        return string[1:-1]
    return string


def parse_str(string: str) -> bool | int | float | str:
    """
    Parses a string into a boolean, integer, float or string.
    """
    if string.lower() == "true":
        return True
    if string.lower() == "false":
        return False
    try:
        return int(string)
    except ValueError:
        pass
    try:
        return float(string)
    except ValueError:
        pass
    return string

def parse_bool(raw: str) -> bool | None:
    """
    Parses a string into a boolean if possible (considering intent)
    """
    normalized = str(raw).strip().lower()
    if normalized in ("true", "t", "yes", "y", "on", "1"):
        return True
    if normalized in ("false", "f", "no", "n", "off", "0"):
        return False
    return None

def parse_time(raw: str) -> time_type | None:
    """
    Parses a string into a time of the day if possible (considering intent)
    Supports:
      - "H" -> H:00
      - "HH:MM" -> HH:MM
      - "HH:MM:SS" -> HH:MM:SS
    """
    for fmt in ("%H:%M:%S", "%H:%M", "%H"):
        try:
            return datetime.strptime(raw, fmt).time()
        except ValueError:
            continue
    return None
