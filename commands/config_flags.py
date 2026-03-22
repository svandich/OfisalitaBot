import shlex
from typing import Callable, Any, Optional
from dataclasses import dataclass

from telegram import Update
from telegram.ext import CallbackContext, JobQueue

import data
from commands.base import Command
from commands.decorators import command
from utils import try_msg


@dataclass
class ConfigDef:
    """
    Defines a persistent configuration flag
    """

    default: Any
    description: str

    parser: Callable[[str], Any]
    """Function that validates and converts user input"""

    applier: Optional[Callable[..., None]] = None
    """Function that makes config changes apply/refresh at runtime"""


# Global registry of available configuration flags
config_registry: dict[str, ConfigDef] = {}


def register_config(key: str, config_def: ConfigDef) -> None:
    """Register a new configuration flag."""
    key = key.strip().lower()
    config_registry[key] = config_def


def apply_config_key(*, key: str, chat_id: int, job_queue: JobQueue) -> None:
    """
    Applies a persisted config flag to runtime behavior.
    Unknown keys are ignored by design.
    """
    normalized = str(key).strip().lower()
    config_def = config_registry.get(normalized)

    if config_def is not None and config_def.applier is not None:
        config_def.applier(chat_id=chat_id, job_queue=job_queue)


def apply_all_config_keys(*, chat_id: int, job_queue: JobQueue) -> None:
    """
    Applies all known config flags for the given chat.
    Intended to run at startup so features self-heal after restarts.
    """
    for key in config_registry.keys():
        apply_config_key(key=key, chat_id=chat_id, job_queue=job_queue)


def init_configs(job_queue: JobQueue) -> None:
    """
    Fetches all active chats from the database and applies their configurations.
    Intended to run once at bot startup.
    """
    for chat_id in data.ConfigFlags.get_all_chat_ids():
        apply_all_config_keys(chat_id=chat_id, job_queue=job_queue)


def list_configs(chat_id: int) -> str:
    """List all configuration flags for the given chat."""
    lines: list[str] = []
    for key, conf in sorted(config_registry.items()):
        display_val = data.ConfigFlags.get(
            chat_id, key, default=str(conf.default)
        )

        lines.append(
            f"• <b>{key}</b>: <code>{display_val}</code>\n<i>{conf.description}</i>"
        )

    if not lines:
        return "🤷‍♂️"

    return "<b>Configuración:</b>\n\n" + "\n\n".join(lines)


@command(member_exclusive=True)
def set_config(update: Update, context: CallbackContext, cmd: Command) -> None:
    """
    Generic persistent configuration command.

    - No arguments -> lists current configuration flags (plus defaults)
    - <key> <value> -> sets the value of the given key
    """
    raw_arg = (cmd.arg or "").strip()

    # List mode: no arguments -> list all configuration flags
    if not raw_arg:
        text = list_configs(update.message.chat_id)
        try_msg(
            context.bot,
            chat_id=update.message.chat_id,
            parse_mode="HTML",
            text=text,
        )
        return

    # Set mode: expects exactly two tokens: <key> <value>
    try:
        parts = shlex.split(raw_arg)
    except ValueError as e:
        try_msg(
            context.bot,
            chat_id=update.message.chat_id,
            parse_mode="HTML",
            text=f"Error leyendo argumentos: {str(e)}",
        )
        return

    if len(parts) != 2:
        try_msg(
            context.bot,
            chat_id=update.message.chat_id,
            parse_mode="HTML",
            text="Uso: /set <key> <value>",
        )
        return

    key = parts[0].strip().lower()
    if key not in config_registry:
        try_msg(
            context.bot,
            chat_id=update.message.chat_id,
            parse_mode="HTML",
            text=f"No cacho que es <code>{key}</code> :')",
        )
        return

    config_def = config_registry[key]
    raw_value = parts[1].strip()

    try:
        parsed_value = config_def.parser(raw_value)
        if parsed_value is None:
            raise ValueError
    except (ValueError, TypeError):
        try_msg(
            context.bot,
            chat_id=update.message.chat_id,
            parse_mode="HTML",
            text=f"El valor ingresado no es válido para <code>{key}</code>.",
        )
        return

    chat_id = update.message.chat_id

    # Fetch, compare, and save dynamically based on data type
    if isinstance(config_def.default, bool):
        prev_val = data.ConfigFlags.get_bool(
            chat_id, key, default=config_def.default
        )
        data.ConfigFlags.set_bool(chat_id, key, parsed_value)
        prev_display = "true" if prev_val else "false"
        new_display = "true" if parsed_value else "false"
    else:
        prev_val = data.ConfigFlags.get(
            chat_id, key, default=str(config_def.default)
        )
        data.ConfigFlags.set(chat_id, key, str(parsed_value))
        prev_display = str(prev_val)
        new_display = str(parsed_value)

    changed = prev_val != parsed_value

    # Apply the change at runtime
    apply_config_key(key=key, chat_id=chat_id, job_queue=context.job_queue)

    if changed:
        text = (
            "Listo!\n"
            f"<b>{key}</b>: <code>{prev_display}</code> → <code>{new_display}</code>"
        )
    else:
        text = f"<code>{key}</code> ya tenía el valor <code>{new_display}</code> :3"

    try_msg(
        context.bot,
        chat_id=update.message.chat_id,
        parse_mode="HTML",
        text=text,
    )
