import logging
import httpx
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes

TOKEN   = "8664412130:AAFwHd4Vr5CpbksNSnT04M3d6i5Z-9WdIlc"
TG_LINK = "https://t.me/PoizonAdvisor"
MARKUP  = 1.15

logging.basicConfig(level=logging.INFO)

# ── Доставка ─────────────────────────────────────────────────────────────────
WEIGHT = {"sneakers": 1.2, "clothes": 1.0}

DELIVERY_OPTIONS = {
    "GROUP1": [  # РФ, АМ, БЕЛ, ГРУ, АЗ
        ("air",      "✈️ Авиа",           225, "3-5 дн"),
        ("express",  "📦 СДЭК Экспресс",  173, "10-12 дн"),
        ("standard", "📦 СДЭК Стандарт",   77, "25 дн"),
    ],
    "KZ": [("auto", "🚗 Авто", 100, "4-8 дн")],
    "UZ": [("air",  "✈️ Авиа", 100, "3-6 дн")],
    "TJ": [("air",  "✈️ Авиа", 100, "3-6 дн")],
}

COUNTRY_GROUP = {
    "RU": "GROUP1", "AM": "GROUP1", "BY": "GROUP1", "GE": "GROUP1", "AZ": "GROUP1",
    "KZ": "KZ", "UZ": "UZ", "TJ": "TJ",
}

COUNTRY_FLAGS = {
    "RU": "🇷🇺 Россия",    "AM": "🇦🇲 Армения",     "BY": "🇧🇾 Беларусь",
    "GE": "🇬🇪 Грузия",    "AZ": "🇦🇿 Азербайджан", "KZ": "🇰🇿 Казахстан",
    "UZ": "🇺🇿 Узбекистан","TJ": "🇹🇯 Таджикистан",
}

CURRENCY = {
    "RU": ("RUB", "₽"),   "AM": ("AMD", "֏"),  "BY": ("BYN", "Br"),
    "GE": ("GEL", "₾"),   "AZ": ("AZN", "₼"),  "KZ": ("KZT", "₸"),
    "UZ": ("UZS", "сум"), "TJ": ("TJS", "с."),
}

COUNTRIES = [
    ("RUB", lambda d: round(d["RUB"] + 1.2, 2), 13.2),
    ("KZT", lambda d: round(d["KZT"] + 8, 1),  555.0),
    ("BYN", lambda d: round(d["BYN"], 3),       0.041),
    ("UZS", lambda d: round(d["UZS"], 0),       1645.0),
    ("TJS", lambda d: round(d["TJS"] + 0.2, 2), 1.08),
    ("AMD", lambda d: round(d["AMD"], 1),       490.0),
    ("GEL", lambda d: round(d["GEL"], 3),       0.37),
    ("AZN", lambda d: round(d["AZN"], 3),       0.19),
]

FLAGS = {
    "RUB": "🇷🇺", "KZT": "🇰🇿", "BYN": "🇧🇾", "UZS": "🇺🇿",
    "TJS": "🇹🇯", "AMD": "🇦🇲", "GEL": "🇬🇪", "AZN": "🇦🇿",
}
SYMBOLS = {
    "RUB": "₽", "KZT": "₸", "BYN": "Br", "UZS": "сум",
    "TJS": "с.", "AMD": "֏", "GEL": "₾", "AZN": "₼",
}

WELCOME = (
    "👋 Привет! Я калькулятор цен <b>POIZON SNG</b> 🇨🇳\n\n"
    "Напиши цену товара в юанях — я мгновенно переведу в валюту твоей страны и рассчитаю доставку.\n\n"
    "Пример: просто напиши <b>350</b>"
)

# ── Курсы ────────────────────────────────────────────────────────────────────
async def get_rates() -> dict:
    try:
        async with httpx.AsyncClient() as c:
            r = await c.get("https://open.er-api.com/v6/latest/CNY", timeout=6)
            d = r.json()["rates"]
            return {key: fn(d) for key, fn, _ in COUNTRIES}
    except Exception:
        return {key: fb for key, fn, fb in COUNTRIES}

# ── Форматирование суммы ──────────────────────────────────────────────────────
def fmt(val: float) -> str:
    if val >= 100:
        return f"{int(val):,}".replace(",", " ")
    return f"{val:.2f}".rstrip("0").rstrip(".")

# ── Расчёт стоимости товара ───────────────────────────────────────────────────
def calc_text(cny: float, rates: dict) -> str:
    m = MARKUP
    lines = []
    for key, fn, _ in COUNTRIES:
        val = cny * rates[key] * m
        lines.append(f"{FLAGS[key]}  {fmt(val)} {SYMBOLS[key]}")
    return (
        f"🧮 <b>{int(cny)} ¥</b>\n"
        f"─────────────────\n"
        + "\n".join(lines) +
        f"\n─────────────────"
    )

# ── Клавиатура после расчёта ─────────────────────────────────────────────────
def price_kb(cny: float) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📦 + Доставка", callback_data=f"d_start:{cny}")],
        [InlineKeyboardButton("📩 Заказать", url=TG_LINK)],
    ])

# ── Отправить расчёт цены ────────────────────────────────────────────────────
async def send_price(update: Update, cny: float):
    rates = await get_rates()
    text  = calc_text(cny, rates)
    await update.message.reply_text(text, parse_mode="HTML", reply_markup=price_kb(cny))

# ── Handlers ─────────────────────────────────────────────────────────────────
async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    kb = InlineKeyboardMarkup([[InlineKeyboardButton("📩 Заказать", url=TG_LINK)]])
    await update.message.reply_text(WELCOME, parse_mode="HTML", reply_markup=kb)

async def cmd_calc(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.args:
        try:
            await send_price(update, float(context.args[0].replace(",", ".")))
            return
        except Exception:
            pass
    await update.message.reply_text("Напиши цену в юанях, например: <b>350</b>", parse_mode="HTML")

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    raw = (update.message.text or "").strip().replace(",", ".").replace("¥", "").replace(" ", "")
    try:
        cny = float(raw)
        if 1 <= cny <= 1_000_000:
            await send_price(update, cny)
            return
    except ValueError:
        pass
    await update.message.reply_text(WELCOME, parse_mode="HTML")

# ── Callback: шаги доставки ───────────────────────────────────────────────────
async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q    = update.callback_query
    data = q.data
    await q.answer()

    # Шаг 1 — выбор типа товара
    if data.startswith("d_start:"):
        cny = data.split(":")[1]
        kb  = InlineKeyboardMarkup([
            [InlineKeyboardButton("👟 Кроссовки (1.2 кг)", callback_data=f"d_item:sneakers:{cny}")],
            [InlineKeyboardButton("👕 Одежда (1 кг)",      callback_data=f"d_item:clothes:{cny}")],
        ])
        await q.edit_message_reply_markup(reply_markup=kb)

    # Шаг 2 — выбор страны
    elif data.startswith("d_item:"):
        _, item, cny = data.split(":")
        rows = []
        row  = []
        for code, label in COUNTRY_FLAGS.items():
            row.append(InlineKeyboardButton(label, callback_data=f"d_country:{item}:{cny}:{code}"))
            if len(row) == 2:
                rows.append(row); row = []
        if row:
            rows.append(row)
        await q.edit_message_reply_markup(reply_markup=InlineKeyboardMarkup(rows))

    # Шаг 3 — выбор способа (если GROUP1) или сразу результат
    elif data.startswith("d_country:"):
        _, item, cny, country = data.split(":")
        group   = COUNTRY_GROUP[country]
        options = DELIVERY_OPTIONS[group]
        weight  = WEIGHT[item]

        if len(options) == 1:
            # Только один вариант — сразу считаем
            _, label, rate_cny, days = options[0]
            await show_delivery_result(q, float(cny), country, weight, rate_cny, label, days)
        else:
            rows = []
            for code, label, rate_cny, days in options:
                rows.append([InlineKeyboardButton(
                    f"{label} — {days}",
                    callback_data=f"d_type:{item}:{cny}:{country}:{code}"
                )])
            await q.edit_message_reply_markup(reply_markup=InlineKeyboardMarkup(rows))

    # Шаг 4 — итог с доставкой
    elif data.startswith("d_type:"):
        _, item, cny, country, dtype = data.split(":")
        group   = COUNTRY_GROUP[country]
        options = DELIVERY_OPTIONS[group]
        weight  = WEIGHT[item]
        option  = next((o for o in options if o[0] == dtype), None)
        if option:
            _, label, rate_cny, days = option
            await show_delivery_result(q, float(cny), country, weight, rate_cny, label, days)


async def show_delivery_result(q, cny: float, country: str, weight: float, rate_cny: int, label: str, days: str):
    rates    = await get_rates()
    cur_key, symbol = CURRENCY[country]
    rate     = rates[cur_key]

    # Стоимость товара
    item_price = cny * rate * MARKUP

    # Стоимость доставки (в юанях → в валюту страны, минималка 1 кг)
    actual_weight = max(weight, 1.0)
    delivery_cny  = rate_cny * actual_weight
    delivery_local = delivery_cny * rate

    total = item_price + delivery_local

    flag  = [v for k, v in COUNTRY_FLAGS.items() if k == country][0].split()[0]
    text  = (
        f"🧮 <b>Итого для {COUNTRY_FLAGS[country]}</b>\n"
        f"─────────────────\n"
        f"🏷  Товар:     {fmt(item_price)} {symbol}\n"
        f"📦 Доставка:  {fmt(delivery_local)} {symbol}\n"
        f"   ({label} · {days} · {actual_weight} кг)\n"
        f"─────────────────\n"
        f"💰 <b>Итого: {fmt(total)} {symbol}</b>\n\n"
        f"Хочешь заказать? 👇"
    )
    kb = InlineKeyboardMarkup([[InlineKeyboardButton("📩 Написать @PoizonAdvisor", url=TG_LINK)]])
    await q.edit_message_text(text, parse_mode="HTML", reply_markup=kb)


# ── Запуск ────────────────────────────────────────────────────────────────────
app = Application.builder().token(TOKEN).build()
app.add_handler(CommandHandler("start", cmd_start))
app.add_handler(CommandHandler("calc",  cmd_calc))
app.add_handler(CallbackQueryHandler(handle_callback))
app.add_handler(MessageHandler(filters.TEXT & filters.ChatType.PRIVATE, handle_text))

print("Калькулятор запущен...")
app.run_polling()
