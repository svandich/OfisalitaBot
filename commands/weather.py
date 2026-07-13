import requests
from telegram import Update
from random import choice
from datetime import time
from time import sleep
import pytz

from telegram.ext import CallbackContext

from commands.base import Command
from commands.decorators import command
from config.logger import log_command
from commands.config_flags import register_config, ConfigDef
from utils import try_msg, parse_bool, parse_time
import data

CLIMA_FLAG_KEY = "clima"
CLIMA_HORA_FLAG_KEY = "clima_hora"
CLIMA_JOB_NAME = "clima"
SANTIAGO_TZ = pytz.timezone("America/Santiago")


def intro() -> str:
    """
    Generates a random "good morning" message
    """
    gm = [
        "BUENOS DÍAS OFIPAPITAS!!!",
        "Buenos días 🌞",
        "CÓMO ESTÁ EL GRUPO MÁS BUENO PAL web-EO?!",
        "HOLA",
        "bdo",
        "buenos días grupazo!!!",
        "monitos días,,,",
        "ola buebos días",
        "ooct",
        "beunos días",
        "cómo está el grupo más bueno pal lunes",
        "buenos dias amiguites",
        "ola buenos dias",
        "/buenosDiasOfipapitas",
        "buenos dias c:",
        "Buenos dias mi gente",
        "Buenos dias bbs",
        "/buenosDiasAmoTuSonrisa",
        "/buenosdias@ofipapinhos",
        "yoyoyo what's up GAMERS?👾?🎮?",
        "Bom dia",
        "La vida es más dulce si le sonries... Buenos días",
        "Comienza tu día declarando DIOS TIENE COSAS BUENAS PARA MI!!!",
        "bdoct",
        "saludos a todxs los valientes que ya se levantaron",
        "wakey, wakey, ofisalita",
        "good morning ofisaleet-a",
        "wake up samurai",
        "QUETEN"
    ]
    presentation = [
        "les traigo el clima",
        "acá tengo el clima del día",
        "veamos como estará el climilla hoy",
        "le tenimos el clima pa la uach",
        "y ahora... _el clima_:",
        "lo vi en un sueño, el clima de hoy",
        "el clima según yo:",
        "hoy día...",
        "comparemos los climas de ayer y hoy!!!1!",
        "al que le sirva el clima:",
        "clima pal que lee:",
        "al que madruga el clima le ayuda",
        "cachen el clima",
    ]
    return choice(gm) + "\n" + choice(presentation) + "\n"


def weather_emoji(mnTemp: str, mxTemp: str, prec: int) -> str:
    """
    Calculates an appropriate emoji for the given weather conditions
    """
    mn = int(mnTemp)
    mx = int(mxTemp)
    avg = (mn + mx) / 2

    # 1. Precipitation takes priority (Scale: 0 - 100)
    if prec >= 80:
        return "⛈️"  # High probability of heavy rain / storm
    elif prec >= 40:
        return "🌧️"  # Solid chance of rain
    elif prec >= 20:
        return "🌦️"  # Mixed / Drizzle / Low chance

    # 2. Extreme Heat (Looking at the peak of the day)
    if mx >= 32:
        return "🔥"  # Scorching hot
    elif mx >= 28:
        return "🥵"  # Very hot

    # 3. Extreme Cold (Looking at freezing mornings or very cold peaks)
    if mx <= 12:
        return "🥶"  # Freezing all day
    elif mn <= 3 and mx <= 18:
        return "🧊"  # Frosty morning, but warms up a bit

    # 4. Standard / Mild Weather (Using average as a fallback)
    if avg < 14:
        return "🧣"  # Chilly, need a scarf/jacket
    elif avg < 18:
        return "🌤️"  # Cool and crisp
    elif avg < 24:
        return "😎"  # Perfect pleasant weather
    else:
        return "☀️"  # Warm and sunny (24 to 27 max)


def prec_msg(yest: int, today: int) -> str:
    """
    Generates a precipitation forecast string based on max probability
    """
    # 1. Dry yesterday / Dry today
    if yest < 15 and today < 15:
        return ""

    # 2. Wet yesterday / Dry today
    elif today < 15:
        ayer_si = [
            "parece que ya pasó la lluvia",
            "risk of rain: none",
            "abrigate que va a hacer frío wuaja",
        ]
        return choice(ayer_si)

    # 3. Dry yesterday / Wet today
    elif yest < 15:
        hoy_si = [
            "saquen los paraguas que hoy llueve",
            "se viene lluvia, cuidadito",
            "WARNING: RISK OF RAIN",
        ]
        return choice(hoy_si)

    # 4. Wet yesterday / Wet today
    precipitation_difference = today - yest

    if precipitation_difference <= -40:
        mucho_menos = [
            "no va a llover tanto como ayer",
            "ayer llovió harto, no será tanto hoy",
        ]
        return choice(mucho_menos)
    elif precipitation_difference <= -20:
        menos = [
            "hoy hay menos prob de lluvia que ayer, pero no sé si me confiaría",
            "al ojo llueve menos",
        ]
        return choice(menos)
    elif -20 < precipitation_difference < 20:
        igual = [
            "debería llover lo mismo hoy que ayer",
            "la lluvia se mantendrá como ayer",
        ]
        return choice(igual)
    elif precipitation_difference >= 40:
        harto = [
            "hoy llueve mucho más que ayer, prepararse",
            "se viene harto mas fuerte la lluvia",
        ]
        return choice(harto)
    else:  # >= 20 but < 40
        mas = [
            "hoy llueve más que ayer",
            "empeora la lluvia hoy",
        ]
        return choice(mas)


def forecast(
    max_retries: int = 3, retry_sleep_s: float = 2.0
) -> tuple[str, str, str]:
    """
    Calculates today's and yesterday's forecasts
    """
    url = "https://api.open-meteo.com/v1/forecast"
    params = dict(
        latitude="-39.7947",
        longitude="-73.2459",
        hourly="temperature_2m,precipitation_probability",
        timezone="auto",
        past_days="1",
        forecast_days="1",
    )

    last_err: Exception | None = None
    for attempt in range(1, max_retries + 1):
        try:
            response = requests.get(url=url, params=params, timeout=10)
            data = response.json()
            temp = data["hourly"]["temperature_2m"]
            prec = data["hourly"]["precipitation_probability"]

            i = 7  # hora de inicio ventana de interés
            f = 22  # hora de fin ventana de interés

            mnYest = str(round(min(temp[i:f])))
            mxYest = str(round(max(temp[i:f])))
            precYest = max(prec[i:f])
            emojiYest = weather_emoji(mnYest, mxYest, precYest)
            tempYest = (
                "Ayer: " + emojiYest + " " + mnYest + "/" + mxYest + "°C"
            )

            mnToday = str(round(min(temp[i + 24 : f + 24])))
            mxToday = str(round(max(temp[i + 24 : f + 24])))
            precToday = max(prec[i + 24 : f + 24])
            emojiToday = weather_emoji(mnToday, mxToday, precToday)
            tempToday = (
                "Hoy: " + emojiToday + " " + mnToday + "/" + mxToday + "°C"
            )

            return tempYest, tempToday, prec_msg(precYest, precToday)
        except Exception as e:
            last_err = e
            if attempt < max_retries:
                sleep(retry_sleep_s)

    raise RuntimeError(
        f"No se pudo obtener el clima (intentos={max_retries})."
    ) from last_err


def weather(context: CallbackContext) -> None:
    """
    Tells the weather forecast for the day
    """
    try:
        tempYest, tempToday, prec = forecast()
        message = intro() + tempYest + "\n" + tempToday + "\n" + prec
    except Exception as e:
        message = (
            f"{intro()}\nIntenté consiguir los datos del clima, pero no lo logré 😭."
            "\nIntenta con /clima más tarde..."
        )
    try_msg(
        context.bot,
        chat_id=context.job.context,
        parse_mode="markdown",
        text=message,
    )


@command(member_exclusive=True)
def reply_clima(update: Update, context: CallbackContext) -> None:
    """
    Replies with the weather forecast for the day
    """
    log_command(update)

    try:
        _, tempToday, prec = forecast()
        message = tempToday + "\n" + prec

        try_msg(
            context.bot,
            chat_id=update.message.chat_id,
            parse_mode="markdown",
            text=message,
            reply_to_message_id=update.message.message_id,
        )
    except Exception:
        try_msg(
            context.bot,
            chat_id=update.message.chat_id,
            parse_mode="markdown",
            text="Algo falló cuando intenté conseguir los datos del clima :C. Revisa los logs porfis?",
            reply_to_message_id=update.message.message_id,
        )


def sync_weather_jobs(job_queue, chat_id: int) -> None:
    """
    Ensures the daily weather job matches the persisted DB flag.
    """
    enabled = data.ConfigFlags.get_bool(chat_id, CLIMA_FLAG_KEY, default=False)
    job_name = f"{CLIMA_JOB_NAME}:{chat_id}"
    jobs = job_queue.get_jobs_by_name(job_name)

    # Read scheduled time per chat (stored as "HH:MM" / "HH:MM:SS").
    hora_raw = data.ConfigFlags.get(
        chat_id, CLIMA_HORA_FLAG_KEY, default=str("7:00:00")
    )
    hora = parse_time(hora_raw) if hora_raw is not None else None
    if hora is None:
        hora = time(hour=7, minute=0)

    # Convert to timezone-aware time for apscheduler.
    scheduled_time = hora.replace(tzinfo=SANTIAGO_TZ)

    if enabled:
        # Always refresh schedule so changes in `clima_hora` apply immediately.
        for job in jobs:
            job.schedule_removal()
        job_queue.run_daily(
            weather,
            time=scheduled_time,
            context=chat_id,
            name=job_name,
        )
    elif jobs:
        for job in jobs:
            job.schedule_removal()


# -- Configuration --

# Flag for sending the daily weather report
register_config(
    CLIMA_FLAG_KEY,
    ConfigDef(
        default=False,
        description="Enviar el reporte diario del clima.",
        parser=parse_bool,
        applier=sync_weather_jobs,
    ),
)

# Flag for the time at which the weather report is sent
register_config(
    CLIMA_HORA_FLAG_KEY,
    ConfigDef(
        default="7:00:00",
        description="Horario de envío del reporte del clima [24h]",
        parser=parse_time,
        applier=sync_weather_jobs,
    ),
)
