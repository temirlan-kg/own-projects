import logging
import sqlite3
from datetime import datetime

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)
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
BOT_TOKEN = "8171121939:AAFA6dxk-EOSkrfuavwXZhTOcV94HIhawj0"
# Admin Chat ID bekommst du z.B. über @userinfobot oder indem du dir /start im Bot loggst
ADMIN_CHAT_ID = 703296214

DB_PATH = "signups.db"

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
            flow TEXT NOT NULL,            -- "uni" or "german"
            name TEXT NOT NULL,
            contact TEXT NOT NULL,
            details TEXT NOT NULL           -- stored as plain text summary
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
# HELPERS
# ======================
def main_menu_kb():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🎓 Studienkolleg / Uni Beratung", callback_data="flow_uni")],
        [InlineKeyboardButton("🇩🇪 Deutschkurs", callback_data="flow_german")],
        [InlineKeyboardButton("ℹ️ Kontakt / Info", callback_data="info")],
    ])

def cancel_kb():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("❌ Abbrechen", callback_data="cancel")]
    ])

def confirm_kb(confirm_data: str):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ Anmelden", callback_data=confirm_data)],
        [InlineKeyboardButton("↩️ Zurück zum Menü", callback_data="back_menu")],
        [InlineKeyboardButton("❌ Abbrechen", callback_data="cancel")],
    ])

def clean_user_text(text: str) -> str:
    return (text or "").strip()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Hi! 👋 Ich bin der Beratungs-Bot.\n\nWobei kann ich helfen?",
        reply_markup=main_menu_kb(),
    )
    return CHOOSE_FLOW

async def menu_from_query(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(
        "Wähle bitte eine Option:",
        reply_markup=main_menu_kb(),
    )
    return CHOOSE_FLOW

async def info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(
        "ℹ️ Info:\n"
        "- Hier kannst du Beratung anfragen und dich anmelden.\n"
        "- Deine Angaben werden nur für die Kontaktaufnahme genutzt.\n\n"
        "Drücke unten, um zurückzugehen.",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("↩️ Zurück", callback_data="back_menu")]
        ])
    )
    return CHOOSE_FLOW

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # works for callback and message
    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.edit_message_text("Abgebrochen. 👌", reply_markup=main_menu_kb())
    else:
        await update.message.reply_text("Abgebrochen. 👌", reply_markup=main_menu_kb())

    context.user_data.clear()
    return CHOOSE_FLOW

# ======================
# UNI FLOW
# ======================
async def choose_flow(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "flow_uni":
        context.user_data.clear()
        context.user_data["flow"] = "uni"
        await query.edit_message_text("🎓 Super! Wie heißt du? (Vorname reicht)", reply_markup=cancel_kb())
        return UNI_NAME

    if query.data == "flow_german":
        context.user_data.clear()
        context.user_data["flow"] = "german"
        await query.edit_message_text("🇩🇪 Super! Wie heißt du? (Vorname reicht)", reply_markup=cancel_kb())
        return GER_NAME

    if query.data == "info":
        return await info(update, context)

    return CHOOSE_FLOW

async def uni_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    name = clean_user_text(update.message.text)
    if len(name) < 2:
        await update.message.reply_text("Bitte gib einen gültigen Namen ein 🙂", reply_markup=cancel_kb())
        return UNI_NAME

    context.user_data["name"] = name
    await update.message.reply_text("Danke! Wie kann ich dich erreichen? (WhatsApp Nummer oder Telegram @name)", reply_markup=cancel_kb())
    return UNI_CONTACT

async def uni_contact(update: Update, context: ContextTypes.DEFAULT_TYPE):
    contact = clean_user_text(update.message.text)
    if len(contact) < 5:
        await update.message.reply_text("Bitte gib eine gültige Kontaktmöglichkeit ein 🙂", reply_markup=cancel_kb())
        return UNI_CONTACT

    context.user_data["contact"] = contact

    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("Studienkolleg", callback_data="uni_target_stk")],
        [InlineKeyboardButton("Universität", callback_data="uni_target_uni")],
        [InlineKeyboardButton("Beides / noch unsicher", callback_data="uni_target_both")],
        [InlineKeyboardButton("❌ Abbrechen", callback_data="cancel")]
    ])
    await update.message.reply_text("Was ist dein Ziel?", reply_markup=kb)
    return UNI_TARGET

async def uni_target(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    mapping = {
        "uni_target_stk": "Studienkolleg",
        "uni_target_uni": "Universität",
        "uni_target_both": "Beides/unsicher",
    }
    context.user_data["target"] = mapping.get(query.data, "Unbekannt")

    await query.edit_message_text("In welcher Stadt / in welchem Land möchtest du studieren?", reply_markup=cancel_kb())
    return UNI_CITY

async def uni_city(update: Update, context: ContextTypes.DEFAULT_TYPE):
    city = clean_user_text(update.message.text)
    if len(city) < 2:
        await update.message.reply_text("Bitte gib Stadt/Land an 🙂", reply_markup=cancel_kb())
        return UNI_CITY

    context.user_data["city"] = city
    await update.message.reply_text("Welche Fachrichtung interessiert dich? (z.B. Informatik, BWL, Medizin ...)", reply_markup=cancel_kb())
    return UNI_MAJOR

async def uni_major(update: Update, context: ContextTypes.DEFAULT_TYPE):
    major = clean_user_text(update.message.text)
    if len(major) < 2:
        await update.message.reply_text("Bitte gib eine Fachrichtung an 🙂", reply_markup=cancel_kb())
        return UNI_MAJOR

    context.user_data["major"] = major
    await update.message.reply_text("Wann möchtest du starten? (z.B. nächstes Semester / 2026 / so früh wie möglich)", reply_markup=cancel_kb())
    return UNI_START

async def uni_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    start_time = clean_user_text(update.message.text)
    if len(start_time) < 2:
        await update.message.reply_text("Bitte gib einen Startzeitpunkt an 🙂", reply_markup=cancel_kb())
        return UNI_START

    context.user_data["start"] = start_time

    summary = (
        "✅ Bitte prüfen:\n\n"
        f"Flow: Studienkolleg/Uni\n"
        f"Name: {context.user_data['name']}\n"
        f"Kontakt: {context.user_data['contact']}\n"
        f"Ziel: {context.user_data['target']}\n"
        f"Ort: {context.user_data['city']}\n"
        f"Fach: {context.user_data['major']}\n"
        f"Start: {context.user_data['start']}\n\n"
        "Wenn alles stimmt, klicke **Anmelden**."
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
            name=context.user_data["name"],
            contact=context.user_data["contact"],
            details=context.user_data["summary"],
        )

        # Admin notification
        admin_msg = (
            "📩 Neue Anmeldung (Uni/Studienkolleg)\n\n"
            f"User: @{u.username}" if u.username else f"User ID: {u.id}"
        )
        admin_msg += "\n\n" + context.user_data["summary"]

        try:
            await context.bot.send_message(chat_id=ADMIN_CHAT_ID, text=admin_msg)
        except Exception as e:
            logger.warning("Admin notify failed: %s", e)

        await query.edit_message_text("🎉 Danke! Du bist angemeldet. Wir melden uns bald bei dir.", reply_markup=main_menu_kb())
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
        await update.message.reply_text("Bitte gib einen gültigen Namen ein 🙂", reply_markup=cancel_kb())
        return GER_NAME

    context.user_data["name"] = name
    await update.message.reply_text("Danke! Wie kann ich dich erreichen? (WhatsApp Nummer oder Telegram @name)", reply_markup=cancel_kb())
    return GER_CONTACT

async def ger_contact(update: Update, context: ContextTypes.DEFAULT_TYPE):
    contact = clean_user_text(update.message.text)
    if len(contact) < 5:
        await update.message.reply_text("Bitte gib eine gültige Kontaktmöglichkeit ein 🙂", reply_markup=cancel_kb())
        return GER_CONTACT

    context.user_data["contact"] = contact

    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("A1", callback_data="level_A1"),
         InlineKeyboardButton("A2", callback_data="level_A2"),
         InlineKeyboardButton("B1", callback_data="level_B1")],
        [InlineKeyboardButton("B2", callback_data="level_B2"),
         InlineKeyboardButton("C1", callback_data="level_C1"),
         InlineKeyboardButton("Weiß nicht", callback_data="level_unknown")],
        [InlineKeyboardButton("❌ Abbrechen", callback_data="cancel")]
    ])
    await update.message.reply_text("Welches Niveau brauchst du?", reply_markup=kb)
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
        [InlineKeyboardButton("Online", callback_data="format_online")],
        [InlineKeyboardButton("Präsenz", callback_data="format_offline")],
        [InlineKeyboardButton("Egal", callback_data="format_any")],
        [InlineKeyboardButton("❌ Abbrechen", callback_data="cancel")]
    ])
    await query.edit_message_text("Welches Kursformat möchtest du?", reply_markup=kb)
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

    await query.edit_message_text("Wann möchtest du starten? (z.B. sofort / Januar / nächstes Monat)", reply_markup=cancel_kb())
    return GER_START

async def ger_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    start_time = clean_user_text(update.message.text)
    if len(start_time) < 2:
        await update.message.reply_text("Bitte gib einen Startzeitpunkt an 🙂", reply_markup=cancel_kb())
        return GER_START

    context.user_data["start"] = start_time

    summary = (
        "✅ Bitte prüfen:\n\n"
        f"Flow: Deutschkurs\n"
        f"Name: {context.user_data['name']}\n"
        f"Kontakt: {context.user_data['contact']}\n"
        f"Niveau: {context.user_data['level']}\n"
        f"Format: {context.user_data['format']}\n"
        f"Start: {context.user_data['start']}\n\n"
        "Wenn alles stimmt, klicke **Anmelden**."
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
            name=context.user_data["name"],
            contact=context.user_data["contact"],
            details=context.user_data["summary"],
        )

        admin_msg = (
            "📩 Neue Anmeldung (Deutschkurs)\n\n"
            f"User: @{u.username}" if u.username else f"User ID: {u.id}"
        )
        admin_msg += "\n\n" + context.user_data["summary"]

        try:
            await context.bot.send_message(chat_id=ADMIN_CHAT_ID, text=admin_msg)
        except Exception as e:
            logger.warning("Admin notify failed: %s", e)

        await query.edit_message_text("🎉 Danke! Du bist angemeldet. Wir melden uns bald bei dir.", reply_markup=main_menu_kb())
        context.user_data.clear()
        return CHOOSE_FLOW

    if query.data == "back_menu":
        context.user_data.clear()
        return await menu_from_query(update, context)

    if query.data == "cancel":
        return await cancel(update, context)

    return CHOOSE_FLOW

# ======================
# RUN APP
# ======================
def build_app() -> Application:
    app = Application.builder().token(BOT_TOKEN).build()

    conv = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            CHOOSE_FLOW: [
                CallbackQueryHandler(choose_flow),
            ],

            UNI_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, uni_name)],
            UNI_CONTACT: [MessageHandler(filters.TEXT & ~filters.COMMAND, uni_contact)],
            UNI_TARGET: [CallbackQueryHandler(uni_target)],
            UNI_CITY: [MessageHandler(filters.TEXT & ~filters.COMMAND, uni_city)],
            UNI_MAJOR: [MessageHandler(filters.TEXT & ~filters.COMMAND, uni_major)],
            UNI_START: [MessageHandler(filters.TEXT & ~filters.COMMAND, uni_start)],
            UNI_CONFIRM: [CallbackQueryHandler(uni_confirm)],

            GER_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, ger_name)],
            GER_CONTACT: [MessageHandler(filters.TEXT & ~filters.COMMAND, ger_contact)],
            GER_LEVEL: [CallbackQueryHandler(ger_level)],
            GER_FORMAT: [CallbackQueryHandler(ger_format)],
            GER_START: [MessageHandler(filters.TEXT & ~filters.COMMAND, ger_start)],
            GER_CONFIRM: [CallbackQueryHandler(ger_confirm)],
        },
        fallbacks=[
            CallbackQueryHandler(cancel, pattern="^cancel$"),
            CommandHandler("cancel", cancel),
            CallbackQueryHandler(menu_from_query, pattern="^back_menu$"),
        ],
        name="signup_conversation",
        persistent=False,
    )

    app.add_handler(conv)
    app.add_handler(CallbackQueryHandler(menu_from_query, pattern="^back_menu$"))
    app.add_handler(CallbackQueryHandler(cancel, pattern="^cancel$"))
    app.add_handler(CallbackQueryHandler(info, pattern="^info$"))
    return app

def main():
    init_db()
    app = build_app()
    print("✅ Bot läuft... Drücke CTRL+C zum Stoppen.")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    import asyncio
    asyncio.set_event_loop(asyncio.new_event_loop())
    main()

