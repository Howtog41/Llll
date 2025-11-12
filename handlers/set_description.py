import logging

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup

from telegram.ext import (

    ConversationHandler, CommandHandler, CallbackQueryHandler,

    MessageHandler, ContextTypes, filters

)

logger = logging.getLogger(__name__)

SET_CHOOSE, WAIT_DESCRIPTION = range(2)

STORAGE_MODE = "global"   # Channel-wise storage

DEFAULT_DESCRIPTION = "Join:- @How_To_Google"

MAX_LEN = 200

def _get_desc_key_for_global(update: Update):

    return update.effective_chat.id

def get_description(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if STORAGE_MODE == "user":

        return context.user_data.get("channel_description")

    elif STORAGE_MODE == "chat":

        return context.chat_data.get("channel_description")

    else:

        chat_id = _get_desc_key_for_global(update)

        descriptions = context.bot_data.setdefault("channel_descriptions", {})

        return descriptions.get(chat_id)

# 🔹 New helper to get description directly by chat_id (used in poll sending)

def get_description_for_chat_id(context: ContextTypes.DEFAULT_TYPE, chat_id: int):

    descriptions = context.bot_data.setdefault("channel_descriptions", {})

    return descriptions.get(chat_id)

def set_description(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str):

    if STORAGE_MODE == "user":

        context.user_data["channel_description"] = text

    elif STORAGE_MODE == "chat":

        context.chat_data["channel_description"] = text

    else:

        chat_id = _get_desc_key_for_global(update)

        descriptions = context.bot_data.setdefault("channel_descriptions", {})

        descriptions[chat_id] = text

def reset_to_default(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if STORAGE_MODE == "user":

        context.user_data.pop("channel_description", None)

    elif STORAGE_MODE == "chat":

        context.chat_data.pop("channel_description", None)

    else:

        chat_id = _get_desc_key_for_global(update)

        descriptions = context.bot_data.setdefault("channel_descriptions", {})

        descriptions.pop(chat_id, None)

async def set_channel_description(update: Update, context: ContextTypes.DEFAULT_TYPE):

    desc = get_description(update, context)

    # Agar kuch set nahi hai to display ke liye default dikhayenge, save nahi karenge

    if desc is None:

        display_desc = DEFAULT_DESCRIPTION

    else:

        display_desc = desc

    buttons = [InlineKeyboardButton("✏️ Edit Description", callback_data="edit_description")]

    if desc:  # Sirf tab delete ka option jab custom description set hai

        buttons.append(InlineKeyboardButton("❌ Delete Description", callback_data="delete_description"))

    reply_markup = InlineKeyboardMarkup([buttons])

    await update.message.reply_text(

        f"📌 Current Description:\n\n`{display_desc}`",

        parse_mode="Markdown",

        reply_markup=reply_markup

    )

    return SET_CHOOSE

async def description_choice_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):

    query = update.callback_query

    await query.answer()

    choice = query.data

    logger.info(f"Button clicked: {choice}")

    if choice == "edit_description":

        await query.edit_message_text("📝 Send new description (max 200 characters). Send /cancel to abort.")

        return WAIT_DESCRIPTION

    elif choice == "delete_description":

        reset_to_default(update, context)

        await query.edit_message_text(f"🗑️ Description reset to default:\n\n`{DEFAULT_DESCRIPTION}`", parse_mode="Markdown")

        return ConversationHandler.END

async def receive_new_description(update: Update, context: ContextTypes.DEFAULT_TYPE):

    text = update.message.text.strip()

    if len(text) == 0:

        await update.message.reply_text("⚠️ Empty description — please send some text or /cancel.")

        return WAIT_DESCRIPTION

    if len(text) > MAX_LEN:

        await update.message.reply_text(f"⚠️ Description {MAX_LEN} characters se zyada nahi ho sakti. Abhi {len(text)} characters hain. Kripya chhota karke bhejein.")

        return WAIT_DESCRIPTION

    set_description(update, context, text)

    await update.message.reply_text(

        f"✅ New description set:\n\n`{text}`",

        parse_mode="Markdown"

    )

    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if update.callback_query:

        await update.callback_query.answer()

        await update.callback_query.edit_message_text("❌ Operation cancelled.")

    else:

        await update.message.reply_text("❌ Operation cancelled.")

    return ConversationHandler.END

def get_set_description_handler():

    return ConversationHandler(

        entry_points=[CommandHandler("setchanneldescription", set_channel_description)],

        states={

            SET_CHOOSE: [

                CallbackQueryHandler(description_choice_callback, pattern="^(edit_description|delete_description)$")

            ],

            WAIT_DESCRIPTION: [

                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_new_description)

            ],

        },

        fallbacks=[CommandHandler("cancel", cancel)],

        per_chat=True,

        allow_reentry=True

    )