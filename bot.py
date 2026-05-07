import logging
import httpx
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    CallbackQueryHandler, filters, ContextTypes, PicklePersistence,
)

TOKEN   = "8664412130:AAFwHd4Vr5CpbksNSnT04M3d6i5Z-9WdIlc"
TG_LINK = "https://t.me/PoizonAdvisor"

logging.basicConfig(level=logging.INFO)

# ── Страны ────────────────────────────────────────────────────────────────────
COUNTRIES = {
    "RU": {"flag": "🇷🇺", "name": "Россия",       "cur": "RUB", "sym": "₽"},
    "KZ": {"flag": "🇰🇿", "name": "Казахстан",    "cur": "KZT", "sym": "₸"},
    "BY": {"flag": "🇧🇾", "name": "Беларусь",     "cur": "BYN", "sym": "Br"},
    "UZ": {"flag": "🇺🇿", "name": "Узбекистан",   "cur": "UZS", "sym": "сум"},
    "TJ": {"flag": "🇹🇯", "name": "Таджикистан",  "cur": "TJS", "sym": "с."},
    "AM": {"flag": "🇦🇲", "name": "Армения",      "cur": "AMD", "sym": "֏"},
    "GE": {"flag": "🇬🇪", "name": "Грузия",       "cur": "GEL", "sym": "₾"},
    "AZ": {"flag": "🇦🇿", "name": "Азербайджан",  "cur": "AZN", "sym": "₼"},
}

# ── Доставка ──────────────────────────────────────────────────────────────────
DELIVERY = {
    "RU": [
        ("air",      "✈️ Авиа",          225, "3-5 дн"),
        ("express",  "📦 СДЭК Экспресс", 173, "10-12 дн"),
        ("standard", "📦 СДЭК Стандарт",  77, "25 дн"),
    ],
    "AM": [
        ("air",      "✈️ Авиа",          225, "3-5 дн + СДЭК"),
        ("express",  "📦 СДЭК Экспресс", 173, "10-12 дн"),
        ("standard", "📦 СДЭК Стандарт",  77, "25 дн"),
    ],
    "BY": [
        ("air",      "✈️ Авиа",          225, "3-5 дн + СДЭК"),
        ("express",  "📦 СДЭК Экспресс", 173, "10-12 дн"),
        ("standard", "📦 СДЭК Стандарт",  77, "25 дн"),
    ],
    "GE": [
        ("air",      "✈️ Авиа",          225, "3-5 дн + СДЭК"),
        ("express",  "📦 СДЭК Экспресс", 173, "10-12 дн"),
        ("standard", "📦 СДЭК Стандарт",  77, "25 дн"),
    ],
    "AZ": [
        ("air",      "✈️ Авиа",          225, "3-5 дн + СДЭК"),
        ("express",  "📦 СДЭК Экспресс", 173, "10-12 дн"),
        ("standard", "📦 СДЭК Стандарт",  77, "25 дн"),
    ],
    "KZ": [("auto", "🚗 Авто", 100, "4-8 дн")],
    "UZ": [("air",  "✈️ Авиа", 100, "3-6 дн")],
    "TJ": [("air",  "✈️ Авиа", 100, "3-6 дн")],
}

WEIGHT = {"sneakers": 1.2, "clothes": 1.0}

# ── Курсы ────────────────────────────────────────────────────────────────────
_rates_cache: dict = {}

async def get_rates() -> dict:
    global _rates_cache
    try:
        async with httpx.AsyncClient() as c:
            r = await c.get("https://open.er-api.com/v6/latest/CNY", timeout=6)
            d = r.json()["rates"]
            _rates_cache = {
                "RUB": round(d["RUB"] + 1.2, 2),
                "KZT": round(d["KZT"] + 8, 1),
                "BYN": round(d["BYN"], 3),
                "UZS": round(d["UZS"], 0),
                "TJS": round(d["TJS"] + 0.2, 2),
                "AMD": round(d["AMD"], 1),
                "GEL": round(d["GEL"], 3),
                "AZN": round(d["AZN"], 3),
            }
            return _rates_cache
    except Exception:
        return _rates_cache or {
            "RUB": 13.2, "KZT": 555.0, "BYN": 0.041, "UZS": 1645.0,
            "TJS": 1.08, "AMD": 490.0, "GEL": 0.37, "AZN": 0.19,
        }

# ── Хелперы ──────────────────────────────────────────────────────────────────
def fmt(val: float) -> str:
    if val >= 100:
        return f"{int(val):,}".replace(",", " ")
    return f"{val:.2f}".rstrip("0").rstrip(".")

def get_country(context: ContextTypes.DEFAULT_TYPE) -> str | None:
    return context.user_data.get("country")

def get_cart(context: ContextTypes.DEFAULT_TYPE) -> list:
    return context.user_data.setdefault("cart", [])

def country_label(code: str) -> str:
    c = COUNTRIES[code]
    return f"{c['flag']} {c['name']}"

# ── Клавиатура выбора страны ─────────────────────────────────────────────────
def country_kb(prefix: str = "country") -> InlineKeyboardMarkup:
    codes = list(COUNTRIES.keys())
    rows  = []
    for i in range(0, len(codes), 2):
        row = []
        for code in codes[i:i+2]:
            c = COUNTRIES[code]
            row.append(InlineKeyboardButton(f"{c['flag']} {c['name']}", callback_data=f"{prefix}:{code}"))
        rows.append(row)
    return InlineKeyboardMarkup(rows)

# ── /start ────────────────────────────────────────────────────────────────────
async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    country = get_country(context)
    if country:
        c = COUNTRIES[country]
        await update.message.reply_text(
            f"👋 Привет! Твоя страна: {c['flag']} <b>{c['name']}</b>\n\n"
            f"Напиши цену в юанях — я переведу в {c['sym']}.",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🌍 Сменить страну", callback_data="change_country")],
                [InlineKeyboardButton("🛒 Корзина",        callback_data="cart_view")],
            ])
        )
    else:
        await update.message.reply_text(
            "👋 Привет! Я калькулятор цен <b>POIZON SNG</b> 🇨🇳\n\n"
            "Выбери свою страну:",
            parse_mode="HTML",
            reply_markup=country_kb()
        )

# ── Текст: цена в юанях ───────────────────────────────────────────────────────
async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    raw = (update.message.text or "").strip().replace(",", ".").replace("¥", "").replace(" ", "")
    try:
        cny = float(raw)
        if not (1 <= cny <= 1_000_000):
            raise ValueError
    except ValueError:
        country = get_country(context)
        if not country:
            await update.message.reply_text("Выбери страну:", reply_markup=country_kb())
        else:
            await update.message.reply_text("Напиши цену в юанях, например: <b>350</b>", parse_mode="HTML")
        return

    country = get_country(context)
    if not country:
        context.user_data["pending_cny"] = cny
        await update.message.reply_text("Сначала выбери страну:", reply_markup=country_kb())
        return

    await send_price_msg(update, context, cny)


async def send_price_msg(update, context, cny: float, edit_msg=None):
    rates   = await get_rates()
    country = get_country(context)
    c       = COUNTRIES[country]
    rate    = rates[c["cur"]]
    price   = cny * rate

    cart     = get_cart(context)
    cart_cnt = len(cart)
    cart_sum = sum(i["cny"] for i in cart)

    text = (
        f"🧮 <b>{int(cny)} ¥  =  {fmt(price)} {c['sym']}</b>\n"
        f"Курс: 1 ¥ = {rate} {c['sym']}"
    )
    if cart_cnt:
        text += f"\n\n🛒 В корзине: {cart_cnt} поз. · {fmt(cart_sum * rate)} {c['sym']}"

    kb = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🛒 В корзину",   callback_data=f"cart_add:{cny}"),
            InlineKeyboardButton("📦 + Доставка",  callback_data=f"d_start:{cny}"),
        ],
        [InlineKeyboardButton("📩 Заказать", url=TG_LINK)],
    ])

    if edit_msg:
        await edit_msg.edit_text(text, parse_mode="HTML", reply_markup=kb)
    else:
        await update.message.reply_text(text, parse_mode="HTML", reply_markup=kb)


# ── Callback handler ──────────────────────────────────────────────────────────
async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q    = update.callback_query
    data = q.data
    await q.answer()

    # Выбор/смена страны
    if data.startswith("country:"):
        code = data.split(":")[1]
        context.user_data["country"] = code
        c = COUNTRIES[code]

        pending = context.user_data.pop("pending_cny", None)
        if pending:
            await q.edit_message_text(
                f"✅ Страна: {c['flag']} {c['name']}\n\nСчитаю...",
                parse_mode="HTML"
            )
            await send_price_msg(None, context, pending, edit_msg=q.message)
        else:
            await q.edit_message_text(
                f"✅ Страна: {c['flag']} <b>{c['name']}</b>\n\n"
                f"Напиши цену в юанях — переведу в {c['sym']}.",
                parse_mode="HTML",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🛒 Корзина", callback_data="cart_view")]
                ])
            )

    elif data == "change_country":
        await q.edit_message_text("Выбери страну:", reply_markup=country_kb())

    # ── Корзина ──
    elif data.startswith("cart_add:"):
        cny  = float(data.split(":")[1])
        cart = get_cart(context)
        cart.append({"cny": cny})
        await q.answer(f"✅ Добавлено в корзину!", show_alert=False)
        # Обновить сообщение
        await send_price_msg(None, context, cny, edit_msg=q.message)

    elif data == "cart_view":
        await show_cart(q, context)

    elif data == "cart_clear":
        context.user_data["cart"] = []
        await q.edit_message_text("🗑 Корзина очищена.\n\nНапиши цену в юанях чтобы начать.")

    elif data == "cart_delivery":
        cart = get_cart(context)
        if not cart:
            await q.answer("Корзина пуста", show_alert=True)
            return
        await q.edit_message_reply_markup(reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("👟 Кроссовки (1.2 кг/пара)", callback_data="cart_d_item:sneakers")],
            [InlineKeyboardButton("👕 Одежда (1 кг/шт)",        callback_data="cart_d_item:clothes")],
            [InlineKeyboardButton("👟+👕 Смешанно",              callback_data="cart_d_item:mixed")],
        ]))

    elif data.startswith("cart_d_item:"):
        item_type = data.split(":")[1]
        cart      = get_cart(context)
        n         = len(cart)
        if item_type == "mixed":
            weight = n * 1.1
        else:
            weight = n * WEIGHT[item_type]
        weight = max(weight, 1.0)
        context.user_data["cart_weight"] = weight
        await show_delivery_type_kb(q, context, weight, prefix="cart_d_type")

    elif data.startswith("cart_d_type:"):
        dtype   = data.split(":")[1]
        weight  = context.user_data.get("cart_weight", 1.0)
        await show_cart_with_delivery(q, context, dtype, weight)

    # ── Доставка для одного товара ──
    elif data.startswith("d_start:"):
        cny = data.split(":")[1]
        await q.edit_message_reply_markup(reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("👟 Кроссовки (1.2 кг)", callback_data=f"d_item:sneakers:{cny}")],
            [InlineKeyboardButton("👕 Одежда (1 кг)",      callback_data=f"d_item:clothes:{cny}")],
        ]))

    elif data.startswith("d_item:"):
        _, item, cny = data.split(":")
        weight       = WEIGHT[item]
        country      = get_country(context)
        options      = DELIVERY[country]

        if len(options) == 1:
            _, label, rate_cny, days = options[0]
            await show_single_delivery_result(q, context, float(cny), weight, rate_cny, label, days)
        else:
            rows = [[InlineKeyboardButton(
                f"{label} · {days}",
                callback_data=f"d_type:{item}:{cny}:{code}"
            )] for code, label, rate_cny, days in options]
            await q.edit_message_reply_markup(reply_markup=InlineKeyboardMarkup(rows))

    elif data.startswith("d_type:"):
        _, item, cny, dtype = data.split(":")
        country = get_country(context)
        weight  = WEIGHT[item]
        option  = next((o for o in DELIVERY[country] if o[0] == dtype), None)
        if option:
            _, label, rate_cny, days = option
            await show_single_delivery_result(q, context, float(cny), weight, rate_cny, label, days)


# ── Показать корзину ──────────────────────────────────────────────────────────
async def show_cart(q, context):
    cart    = get_cart(context)
    country = get_country(context)
    c       = COUNTRIES[country]
    rates   = await get_rates()
    rate    = rates[c["cur"]]

    if not cart:
        await q.edit_message_text(
            "🛒 Корзина пуста.\n\nНапиши цену в юанях чтобы добавить товар.",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("📩 Заказать", url=TG_LINK)
            ]])
        )
        return

    lines     = []
    total_cny = 0
    for i, item in enumerate(cart, 1):
        cny       = item["cny"]
        total_cny += cny
        lines.append(f"{i}. {int(cny)} ¥ = {fmt(cny * rate)} {c['sym']}")

    text = (
        f"🛒 <b>Корзина</b> ({c['flag']} {c['name']})\n"
        f"─────────────────\n"
        + "\n".join(lines) +
        f"\n─────────────────\n"
        f"💰 <b>Итого: {fmt(total_cny * rate)} {c['sym']}</b>"
    )
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("📦 Рассчитать доставку", callback_data="cart_delivery")],
        [
            InlineKeyboardButton("🗑 Очистить", callback_data="cart_clear"),
            InlineKeyboardButton("📩 Заказать", url=TG_LINK),
        ],
    ])
    await q.edit_message_text(text, parse_mode="HTML", reply_markup=kb)


async def show_delivery_type_kb(q, context, weight: float, prefix: str):
    country = get_country(context)
    options = DELIVERY[country]
    if len(options) == 1:
        code, label, rate_cny, days = options[0]
        if prefix == "cart_d_type":
            await show_cart_with_delivery(q, context, code, weight)
        return
    rows = [[InlineKeyboardButton(
        f"{label} · {days}",
        callback_data=f"{prefix}:{code}"
    )] for code, label, rate_cny, days in options]
    await q.edit_message_reply_markup(reply_markup=InlineKeyboardMarkup(rows))


async def show_single_delivery_result(q, context, cny: float, weight: float, rate_cny: int, label: str, days: str):
    rates   = await get_rates()
    country = get_country(context)
    c       = COUNTRIES[country]
    rate    = rates[c["cur"]]

    weight       = max(weight, 1.0)
    item_price   = cny * rate
    delivery     = rate_cny * weight * rate
    total        = item_price + delivery

    text = (
        f"📦 <b>Итого с доставкой</b>\n"
        f"─────────────────\n"
        f"🏷  Товар:     {fmt(item_price)} {c['sym']}\n"
        f"📦 Доставка:  {fmt(delivery)} {c['sym']}\n"
        f"   {label} · {days} · {weight} кг\n"
        f"─────────────────\n"
        f"💰 <b>Итого: {fmt(total)} {c['sym']}</b>\n\n"
        f"<i>Без учёта комиссии байера</i>"
    )
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("📩 Написать @PoizonAdvisor", url=TG_LINK)],
        [InlineKeyboardButton("🛒 Корзина", callback_data="cart_view")],
    ])
    await q.edit_message_text(text, parse_mode="HTML", reply_markup=kb)


async def show_cart_with_delivery(q, context, dtype: str, weight: float):
    rates   = await get_rates()
    country = get_country(context)
    c       = COUNTRIES[country]
    rate    = rates[c["cur"]]
    cart    = get_cart(context)

    option    = next((o for o in DELIVERY[country] if o[0] == dtype), DELIVERY[country][0])
    _, label, rate_cny, days = option

    total_cny = sum(i["cny"] for i in cart)
    items_sum = total_cny * rate
    delivery  = rate_cny * max(weight, 1.0) * rate
    total     = items_sum + delivery

    text = (
        f"📦 <b>Корзина с доставкой</b> ({c['flag']} {c['name']})\n"
        f"─────────────────\n"
        f"🏷  Товары ({len(cart)} шт): {fmt(items_sum)} {c['sym']}\n"
        f"📦 Доставка: {fmt(delivery)} {c['sym']}\n"
        f"   {label} · {days} · {weight} кг\n"
        f"─────────────────\n"
        f"💰 <b>Итого: {fmt(total)} {c['sym']}</b>\n\n"
        f"<i>Без учёта комиссии байера</i>"
    )
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("📩 Написать @PoizonAdvisor", url=TG_LINK)],
        [InlineKeyboardButton("🗑 Очистить корзину", callback_data="cart_clear")],
    ])
    await q.edit_message_text(text, parse_mode="HTML", reply_markup=kb)


# ── Запуск ────────────────────────────────────────────────────────────────────
persistence = PicklePersistence(filepath="data.pkl")
app = Application.builder().token(TOKEN).persistence(persistence).build()
app.add_handler(CommandHandler("start", cmd_start))
app.add_handler(CallbackQueryHandler(handle_callback))
app.add_handler(MessageHandler(filters.TEXT & filters.ChatType.PRIVATE, handle_text))

print("Калькулятор запущен...")
app.run_polling()
