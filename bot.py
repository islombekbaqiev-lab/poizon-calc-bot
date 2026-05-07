import asyncio
import logging
import httpx
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

TOKEN   = "8664412130:AAFwHd4Vr5CpbksNSnT04M3d6i5Z-9WdIlc"
TG_LINK = "https://t.me/PoizonAdvisor"

logging.basicConfig(level=logging.INFO)

MARKUP = 1.15  # наценка 15%

WELCOME = (
    "👋 Привет! Я калькулятор цен <b>POIZON SNG</b> 🇨🇳\n\n"
    "Напиши цену товара в юанях — я мгновенно покажу стоимость в рублях, тенге и BYN.\n\n"
    "Пример: просто напиши <b>350</b>"
)


COUNTRIES = [
    ("RUB", "🇷🇺", "₽",   lambda d: round(d["RUB"] + 1.2, 2), 13.2),
    ("KZT", "🇰🇿", "₸",   lambda d: round(d["KZT"] + 8, 1),  555.0),
    ("BYN", "🇧🇾", "Br",  lambda d: round(d["BYN"], 3),       0.041),
    ("UZS", "🇺🇿", "сум", lambda d: round(d["UZS"], 0),       1645.0),
    ("TJS", "🇹🇯", "с.",  lambda d: round(d["TJS"] + 0.2, 2), 1.08),
    ("AMD", "🇦🇲", "֏",   lambda d: round(d["AMD"], 1),       490.0),
    ("GEL", "🇬🇪", "₾",   lambda d: round(d["GEL"], 3),       0.37),
    ("AZN", "🇦🇿", "₼",   lambda d: round(d["AZN"], 3),       0.19),
]


async def get_rates() -> dict:
    try:
        async with httpx.AsyncClient() as c:
            r = await c.get("https://open.er-api.com/v6/latest/CNY", timeout=6)
            d = r.json()["rates"]
            return {key: fn(d) for key, flag, sym, fn, _ in COUNTRIES}
    except Exception:
        return {key: fallback for key, flag, sym, fn, fallback in COUNTRIES}


async def calc_reply(update: Update, cny: float):
    rates = await get_rates()
    m = MARKUP

    lines = []
    for key, flag, sym, _, _ in COUNTRIES:
        val = cny * rates[key] * m
        if val >= 100:
            formatted = f"{int(val):,}"
        else:
            formatted = f"{val:.2f}".rstrip("0").rstrip(".")
        lines.append(f"{flag}  {formatted} {sym}")

    text = (
        f"🧮 <b>{int(cny)} ¥</b>\n"
        f"─────────────────\n"
        + "\n".join(lines) +
        f"\n─────────────────\n"
        f"Хочешь заказать? 👇"
    )

    kb = InlineKeyboardMarkup([[
        InlineKeyboardButton("📩 Написать @PoizonAdvisor", url=TG_LINK)
    ]])
    await update.message.reply_text(text, parse_mode="HTML", reply_markup=kb)


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    kb = InlineKeyboardMarkup([[
        InlineKeyboardButton("📩 Заказать", url=TG_LINK)
    ]])
    await update.message.reply_text(WELCOME, parse_mode="HTML", reply_markup=kb)


async def cmd_calc(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.args:
        try:
            cny = float(context.args[0].replace(",", "."))
            await calc_reply(update, cny)
            return
        except Exception:
            pass
    await update.message.reply_text(
        "Напиши цену в юанях:\n/calc 350\n\nИли просто: <b>350</b>",
        parse_mode="HTML"
    )


async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    raw = (update.message.text or "").strip().replace(",", ".").replace("¥", "").replace(" ", "")
    try:
        cny = float(raw)
        if 1 <= cny <= 1_000_000:
            await calc_reply(update, cny)
            return
    except ValueError:
        pass
    await update.message.reply_text(WELCOME, parse_mode="HTML")


app = Application.builder().token(TOKEN).build()
app.add_handler(CommandHandler("start", cmd_start))
app.add_handler(CommandHandler("calc",  cmd_calc))
app.add_handler(MessageHandler(filters.TEXT & filters.ChatType.PRIVATE, handle_text))

print("Калькулятор запущен...")
app.run_polling()
