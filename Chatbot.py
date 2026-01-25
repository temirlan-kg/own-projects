import asyncio
import logging
import sqlite3
from datetime import datetime

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ConversationHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

# ======================
# CONFIG
# ======================
BOT_TOKEN = "8171121939:AAGpbWNiiFsO0vvxkD-oVBoy4ZnWzD0mnLc"
ADMIN_CHAT_ID = 703296214
DB_PATH = "signups.db"

# ======================
# LOGGING
# ======================
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# ======================
# DB SETUP
# ======================
def init_db():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS signups (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at TEXT NOT NULL,
            user_id INTEGER,
            username TEXT,
            flow TEXT NOT NULL,
            name TEXT NOT NULL,
            contact TEXT NOT NULL,
            details TEXT NOT NULL
        )
    """)
    conn.commit()
    conn.close()

def save_signup(user_id: int, username: str, flow: str, name: str, contact: str, details: str):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO signups (created_at, user_id, username, flow, name, contact, details)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (datetime.utcnow().isoformat(), user_id, username, flow, name, contact, details))
    conn.commit()
    conn.close()

# ======================
# CONVERSATION STATES
# ======================
(
    CHOOSE_FLOW,

    UNI_NAME,
    UNI_CONTACT,
    UNI_TARGET,
    UNI_CITY,
    UNI_MAJOR,
    UNI_START,
    UNI_CONFIRM,

    GER_NAME,
    GER_CONTACT,
    GER_LEVEL,
    GER_FORMAT,
    GER_START,
    GER_CONFIRM,
) = range(14)

# ======================
# HELPERS / KEYBOARDS
# ======================
def main_menu_kb():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🎓 Штудиенколлег / Университет", callback_data="flow_uni")],
        [InlineKeyboardButton("🇩🇪 Немис курсу", callback_data="flow_german")],
        [InlineKeyboardButton("📞 Байланыш/ ℹ️ Маалымат:", callback_data="info")],
    ])

def cancel_kb():
    return InlineKeyboardMarkup([[InlineKeyboardButton("❌ Жокко чыгаруу", callback_data="cancel")]])

def confirm_kb(confirm_data: str):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ Катталуу", callback_data=confirm_data)],
        [InlineKeyboardButton("↩️ Менюга кайтуу", callback_data="back_menu")],
        [InlineKeyboardButton("❌ Жокко чыгаруу", callback_data="cancel")],
    ])

def clean_user_text(text: str) -> str:
    return (text or "").strip()

# ======================
# GENERIC HANDLERS
# ======================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Салам! 👋 Мен консультация берүүчү ботмун.\n\nСизге кандай жардам бере алам?",
        reply_markup=main_menu_kb(),
    )
    return CHOOSE_FLOW

async def menu_from_query(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("Төмөндөн бир вариантты тандаңыз:", reply_markup=main_menu_kb())
    return CHOOSE_FLOW

async def info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(
        "ℹ️ Маалымат:\n"
        "- Бул жерден консультацияга кайрылып, каттала аласыз.\n"
        "- Сиздин маалыматтар байланыш үчүн гана колдонулат.\n\n"
        "Артка кайтуу үчүн төмөндөгү баскычты басыңыз.",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("↩️ Артка", callback_data="back_menu")]]),
    )
    return CHOOSE_FLOW

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.edit_message_text("Жокко чыгарылды. 👌", reply_markup=main_menu_kb())
    else:
        await update.message.reply_text("Жокко чыгарылды. 👌", reply_markup=main_menu_kb())

    context.user_data.clear()
    return CHOOSE_FLOW

# ======================
# FLOW SELECTION
# ======================
async def choose_flow(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "flow_uni":
        context.user_data.clear()
        context.user_data["flow"] = "uni"
        await query.edit_message_text("🎓 Супер! Атың ким? (Атыңды гана жазсаң жетиштүү)", reply_markup=cancel_kb())
        return UNI_NAME

    if query.data == "flow_german":
        context.user_data.clear()
        context.user_data["flow"] = "german"
        await query.edit_message_text("🇩🇪 Супер! Атың ким? (Атыңды гана жазсаң жетиштүү)", reply_markup=cancel_kb())
        return GER_NAME

    if query.data == "info":
        return await info(update, context)

    return CHOOSE_FLOW

# ======================
# UNI FLOW
# ======================
async def uni_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    name = clean_user_text(update.message.text)
    if len(name) < 2:
        await update.message.reply_text("Сураныч, жарактуу ат жазыңыз. 🙂", reply_markup=cancel_kb())
        return UNI_NAME

    context.user_data["name"] = name
    await update.message.reply_text(
        "Рахмат! Сиз менен кантип байланышсак болот? (WhatsApp номери же Telegram @аты)",
        reply_markup=cancel_kb()
    )
    return UNI_CONTACT

async def uni_contact(update: Update, context: ContextTypes.DEFAULT_TYPE):
    contact = clean_user_text(update.message.text)
    if len(contact) < 5:
        await update.message.reply_text("Сураныч, жарактуу байланыш маалыматын жазыңыз 🙂", reply_markup=cancel_kb())
        return UNI_CONTACT

    context.user_data["contact"] = contact

    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("Штудиенколлег", callback_data="uni_target_stk")],
        [InlineKeyboardButton("Университет", callback_data="uni_target_uni")],
        [InlineKeyboardButton("Экөө тең / Так эмес", callback_data="uni_target_both")],
        [InlineKeyboardButton("❌ Жокко чыгаруу", callback_data="cancel")],
    ])
    await update.message.reply_text("Сиздин максатыңыз эмне??", reply_markup=kb)
    return UNI_TARGET

async def uni_target(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    mapping = {
        "uni_target_stk": "Штудиенколлег",
        "uni_target_uni": "Университет",
        "uni_target_both": "Экөө тең / Так эмес",
    }
    context.user_data["target"] = mapping.get(query.data, "Белгисиз")

    await query.edit_message_text("Кайсы шаарда же кайсы өлкөдө окууну каалайсыз?", reply_markup=cancel_kb())
    return UNI_CITY

async def uni_city(update: Update, context: ContextTypes.DEFAULT_TYPE):
    city = clean_user_text(update.message.text)
    if len(city) < 2:
        await update.message.reply_text("Сураныч, шаарды / өлкөнү жазыңыз 🙂", reply_markup=cancel_kb())
        return UNI_CITY

    context.user_data["city"] = city
    await update.message.reply_text(
        "Кайсы адистик сизди кызыктырат? (мисалы: информатика, бизнес, медицина …)",
        reply_markup=cancel_kb()
    )
    return UNI_MAJOR

async def uni_major(update: Update, context: ContextTypes.DEFAULT_TYPE):
    major = clean_user_text(update.message.text)
    if len(major) < 2:
        await update.message.reply_text("Сураныч, адистикти жазыңыз 🙂", reply_markup=cancel_kb())
        return UNI_MAJOR

    context.user_data["major"] = major
    await update.message.reply_text(
        "Качан окууну баштагыңыз келет? (мисалы: кийинки семестр / 2026/2027 / мүмкүн болушунча эртерээк)",
        reply_markup=cancel_kb(),
    )
    return UNI_START

async def uni_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    start_time = clean_user_text(update.message.text)
    if len(start_time) < 2:
        await update.message.reply_text("Сураныч, баштоо убактысын жазыңыз 🙂", reply_markup=cancel_kb())
        return UNI_START

    context.user_data["start"] = start_time

    summary = (
        "✅ Сураныч, текшериңиз:\n\n"
        "Багыт: Штудиенколлег / Университет\n"
        f"Аты-жөнү: {context.user_data['name']}\n"
        f"Байланыш: {context.user_data['contact']}\n"
        f"Максаты: {context.user_data['target']}\n"
        f"Шаар / Өлкө: {context.user_data['city']}\n"
        f"Адистиги: {context.user_data['major']}\n"
        f"Баштоо убактысы: {context.user_data['start']}\n\n"
        "Баары туура болсо, «Катталуу» баскычын басыңыз."
    )

    context.user_data["summary"] = summary
    await update.message.reply_text(summary, reply_markup=confirm_kb("uni_confirm"), parse_mode="Markdown")
    return UNI_CONFIRM

async def uni_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "uni_confirm":
        u = query.from_user

        save_signup(
            user_id=u.id,
            username=u.username or "",
            flow="uni",
            name=context.user_data.get("name", ""),
            contact=context.user_data.get("contact", ""),
            details=context.user_data.get("summary", ""),
        )

        who = f"User: @{u.username}" if u.username else f"User ID: {u.id}"
        admin_msg = "📩 Жаңы катталуу (Университет / Штудиенколлег)\n\n" + who + "\n\n" + context.user_data.get("summary", "")

        try:
            await context.bot.send_message(chat_id=ADMIN_CHAT_ID, text=admin_msg)
        except Exception as e:
            logger.warning("Admin notify failed: %s", e)

        await query.edit_message_text("🎉 Рахмат! Катталуу ийгиликтүү болду. Жакында сизге байланышабыз 🙂.",
                                      reply_markup=main_menu_kb())
        context.user_data.clear()
        return CHOOSE_FLOW

    if query.data == "back_menu":
        context.user_data.clear()
        return await menu_from_query(update, context)

    if query.data == "cancel":
        return await cancel(update, context)

    return CHOOSE_FLOW

# ======================
# GERMAN COURSE FLOW
# ======================
async def ger_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    name = clean_user_text(update.message.text)
    if len(name) < 2:
        await update.message.reply_text("Сураныч, жарактуу ат жазыңыз 🙂", reply_markup=cancel_kb())
        return GER_NAME

    context.user_data["name"] = name
    await update.message.reply_text(
        "Рахмат! Сиз менен кантип байланышсак болот? (WhatsApp номери же Telegram @аты)",
        reply_markup=cancel_kb()
    )
    return GER_CONTACT

async def ger_contact(update: Update, context: ContextTypes.DEFAULT_TYPE):
    contact = clean_user_text(update.message.text)
    if len(contact) < 5:
        await update.message.reply_text("Сураныч, жарактуу байланыш маалыматын жазыңыз 🙂", reply_markup=cancel_kb())
        return GER_CONTACT

    context.user_data["contact"] = contact

    kb = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("A1", callback_data="level_A1"),
            InlineKeyboardButton("A2", callback_data="level_A2"),
            InlineKeyboardButton("B1", callback_data="level_B1"),
        ],
        [
            InlineKeyboardButton("🤷‍♂️ Билбейм", callback_data="level_unknown")
        ],
        [
            InlineKeyboardButton("❌ Жокко чыгаруу", callback_data="cancel")
        ],
    ])

    await update.message.reply_text("Сизге кайсы деңгээл керек?", reply_markup=kb)
    return GER_LEVEL

async def ger_level(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    mapping = {
        "level_A1": "A1",
        "level_A2": "A2",
        "level_B1": "B1",
        "level_B2": "B2",
        "level_C1": "C1",
        "level_unknown": "Unklar",
    }
    context.user_data["level"] = mapping.get(query.data, "Unklar")

    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("Онлайн", callback_data="format_online")],
        [InlineKeyboardButton("❌ Жокко чыгаруу", callback_data="cancel")],
    ])
    await query.edit_message_text("Кайсы форматтагы курс каалайсың?", reply_markup=kb)
    return GER_FORMAT

async def ger_format(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    mapping = {
        "format_online": "Online",
        "format_offline": "Präsenz",
        "format_any": "Egal",
    }
    context.user_data["format"] = mapping.get(query.data, "Egal")

    await query.edit_message_text("Качан баштагыңыз келет? (мисалы: дароо / январь / кийинки ай)",
                                  reply_markup=cancel_kb())
    return GER_START

async def ger_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    start_time = clean_user_text(update.message.text)
    if len(start_time) < 2:
        await update.message.reply_text("Сураныч, баштоо убактысын жазыңыз 🙂", reply_markup=cancel_kb())
        return GER_START

    context.user_data["start"] = start_time

    summary = (
        "✅ Сураныч, текшериңиз:\n\n"
        "Багыт: Немис курсу\n"
        f"Аты-жөнү: {context.user_data['name']}\n"
        f"Байланыш: {context.user_data['contact']}\n"
        f"Деңгээл: {context.user_data['level']}\n"
        f"Формат: {context.user_data['format']}\n"
        f"Баштоо убактысы: {context.user_data['start']}\n\n"
        "Баары туура болсо, «Катталуу» баскычын басыңыз."
    )

    context.user_data["summary"] = summary
    await update.message.reply_text(summary, reply_markup=confirm_kb("ger_confirm"), parse_mode="Markdown")
    return GER_CONFIRM

async def ger_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "ger_confirm":
        u = query.from_user

        save_signup(
            user_id=u.id,
            username=u.username or "",
            flow="german",
            name=context.user_data.get("name", ""),
            contact=context.user_data.get("contact", ""),
            details=context.user_data.get("summary", ""),
        )

        who = f"User: @{u.username}" if u.username else f"User ID: {u.id}"
        admin_msg = "📩 Немис тили курсуна жаңы катталуу\n\n" + who + "\n\n" + context.user_data.get("summary", "")

        try:
            await context.bot.send_message(chat_id=ADMIN_CHAT_ID, text=admin_msg)
        except Exception as e:
            logger.warning("Admin notify failed: %s", e)

        await query.edit_message_text("🎉 Рахмат! Катталуу ийгиликтүү болду 😊 Жакында сизге байланышабыз.",
                                      reply_markup=main_menu_kb())
        context.user_data.clear()
        return CHOOSE_FLOW

    if query.data == "back_menu":
        context.user_data.clear()
        return await menu_from_query(update, context)

    if query.data == "cancel":
        return await cancel(update, context)

    return CHOOSE_FLOW

# ======================
# ERROR HANDLER
# ======================
async def on_error(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.exception("Unhandled error", exc_info=context.error)

# ======================
# BUILD APP
# ======================
def build_app() -> Application:
    app = Application.builder().token(BOT_TOKEN).build()

    conv = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            CHOOSE_FLOW: [
                CallbackQueryHandler(choose_flow, pattern="^(flow_uni|flow_german|info)$"),
                CallbackQueryHandler(menu_from_query, pattern="^back_menu$"),
                CallbackQueryHandler(cancel, pattern="^cancel$"),
            ],

            UNI_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, uni_name)],
            UNI_CONTACT: [MessageHandler(filters.TEXT & ~filters.COMMAND, uni_contact)],
            UNI_TARGET: [
                CallbackQueryHandler(uni_target, pattern="^uni_target_"),
                CallbackQueryHandler(cancel, pattern="^cancel$"),
            ],
            UNI_CITY: [MessageHandler(filters.TEXT & ~filters.COMMAND, uni_city)],
            UNI_MAJOR: [MessageHandler(filters.TEXT & ~filters.COMMAND, uni_major)],
            UNI_START: [MessageHandler(filters.TEXT & ~filters.COMMAND, uni_start)],
            UNI_CONFIRM: [CallbackQueryHandler(uni_confirm, pattern="^(uni_confirm|back_menu|cancel)$")],

            GER_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, ger_name)],
            GER_CONTACT: [MessageHandler(filters.TEXT & ~filters.COMMAND, ger_contact)],
            GER_LEVEL: [
                CallbackQueryHandler(ger_level, pattern="^level_"),
                CallbackQueryHandler(cancel, pattern="^cancel$"),
            ],
            GER_FORMAT: [
                CallbackQueryHandler(ger_format, pattern="^format_"),
                CallbackQueryHandler(cancel, pattern="^cancel$"),
            ],
            GER_START: [MessageHandler(filters.TEXT & ~filters.COMMAND, ger_start)],
            GER_CONFIRM: [CallbackQueryHandler(ger_confirm, pattern="^(ger_confirm|back_menu|cancel)$")],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
        name="signup_conversation",
        persistent=False,
    )

    app.add_handler(conv)
    app.add_error_handler(on_error)
    return app

# ======================
# ASYNC START (stable on Python 3.14)
# ======================
async def main_async():
    if not BOT_TOKEN or BOT_TOKEN == "PASTE_YOUR_NEW_TOKEN_HERE":
        raise RuntimeError("Bitte BOT_TOKEN oben eintragen (neuen Token von BotFather).")

    init_db()
    app = build_app()

    # sauberer Start ohne Application.run_polling()
    await app.initialize()
    await app.start()
    await app.updater.start_polling(allowed_updates=Update.ALL_TYPES)

    print("✅ Bot läuft... Drücke CTRL+C zum Stoppen.")
    await asyncio.Event().wait()  # läuft für immer

def main():
    asyncio.run(main_async())

if __name__ == "__main__":
    main()
