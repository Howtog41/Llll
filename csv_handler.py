import csv

import logging

import asyncio

from io import StringIO

from datetime import datetime

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup

from telegram.ext import (

    Application, CommandHandler, MessageHandler, filters,

    CallbackQueryHandler, ContextTypes, ConversationHandler

)

from telegram.error import RetryAfter

from helpers.db import users_collection

from config import ADMIN_ID

# Conversation states

UPLOAD_CSV, COLLECT_TEXT, CHOOSE_DESTINATION, CHOOSE_CHANNEL = range(4)

user_state = {}

user_csv_text = {}  # store text CSV per user

# -------------------------------

# /uploadcsv Command

# -------------------------------

async def upload_csv_command(update: Update, context: ContextTypes.DEFAULT_TYPE):

    user_id = update.effective_user.id

    user_info = users_collection.find_one({'user_id': user_id})

    now = datetime.now()

    # Access check

    if user_id == ADMIN_ID:

        pass_access = True

    elif user_info and user_info.get('authorized', False):

        expires_on = user_info.get('expires_on')

        pass_access = expires_on and expires_on > now

    else:

        pass_access = False

    if not pass_access:

        await update.message.reply_text(

            "⚠️ Your free trial has expired.\nContact admin for full access. @lkd_ak"

        )

        return ConversationHandler.END

    # Ask user how to upload

    keyboard = [

        [InlineKeyboardButton("📎 Upload CSV File", callback_data='file')],

        [InlineKeyboardButton("✍️ Paste CSV Text", callback_data='text')]

    ]

    await update.message.reply_text(

        "How would you like to upload your MCQs?",

        reply_markup=InlineKeyboardMarkup(keyboard)

    )

    return UPLOAD_CSV

# -------------------------------

# Handle choice: file or text

# -------------------------------

async def handle_upload_choice(update: Update, context: ContextTypes.DEFAULT_TYPE):

    query = update.callback_query

    await query.answer()

    user_id = query.from_user.id

    if query.data == "file":

        await query.edit_message_text("📁 Please send your CSV file now.")

        return UPLOAD_CSV

    elif query.data == "text":

        user_csv_text[user_id] = []

        await query.edit_message_text(

            "📝 Send your CSV data in text format.\n"

            "You can send multiple messages. When finished, type /done."

        )

        return COLLECT_TEXT

# -------------------------------

# Collect CSV text messages

# -------------------------------

async def collect_text_csv(update: Update, context: ContextTypes.DEFAULT_TYPE):

    user_id = update.effective_user.id

    text = update.message.text.strip()

    if user_id not in user_csv_text:

        user_csv_text[user_id] = []

    user_csv_text[user_id].append(text)

    await update.message.reply_text("✅ Added! Send more or type /done when finished.")

# -------------------------------

# When user types /done

# -------------------------------

async def done_collecting(update: Update, context: ContextTypes.DEFAULT_TYPE):

    user_id = update.effective_user.id

    if user_id not in user_csv_text or not user_csv_text[user_id]:

        await update.message.reply_text("⚠️ No CSV data received.")

        return ConversationHandler.END

    csv_text = "\n".join(user_csv_text[user_id])

    csv_file = StringIO(csv_text)

    try:

        reader = csv.DictReader(csv_file)

        questions = [row for row in reader if any(row.values())]

        if not questions:

            await update.message.reply_text("⚠️ No valid CSV rows found.")

            return ConversationHandler.END

        # Store in context

        context.user_data['questions'] = questions

        await update.message.reply_text(f"✅ {len(questions)} questions loaded successfully!")

        # Ask destination

        keyboard = [

            [InlineKeyboardButton("🤖 Bot", callback_data='bot')],

            [InlineKeyboardButton("📢 Channel", callback_data='channel')]

        ]

        await update.message.reply_text("Where do you want to send them?", reply_markup=InlineKeyboardMarkup(keyboard))

        return CHOOSE_DESTINATION

    except Exception as e:

        logging.error(f"CSV text processing error: {e}")

        await update.message.reply_text("❌ Error reading CSV text. Check your format.")

        return ConversationHandler.END

# -------------------------------

# Handle CSV File Upload (merged with advanced checks)

# -------------------------------

async def handle_csv_file(update: Update, context: ContextTypes.DEFAULT_TYPE):

    user_id = update.effective_user.id

    try:

        file = await update.message.document.get_file()

        file_path = f"{file.file_id}.csv"

        await file.download_to_drive(file_path)

        # Read file and remove empty lines

        with open(file_path, 'r', encoding='utf-8-sig') as f:

            lines = [line.strip() for line in f if line.strip()]

        expected_headers = ["Question", "Option A", "Option B", "Option C", "Option D", "Answer", "Description"]

        # Check header

        first_line = lines[0] if lines else ""

        has_header = any(key.lower() in first_line.lower() for key in ["question", "option", "answer", "description"])

        if not has_header:

            lines.insert(0, ",".join(expected_headers))

            with open(file_path, 'w', encoding='utf-8', newline='') as f:

                f.write("\n".join(lines))

            await update.message.reply_text("ℹ️ Header missing detected. Default header added automatically ✅")

        # Read CSV properly

        with open(file_path, 'r', encoding='utf-8-sig') as f:

            reader = csv.DictReader(f)

            reader.fieldnames = [h.strip().title() for h in reader.fieldnames]

            questions = []

            for row in reader:

                clean_row = {k.strip().title(): (v.strip() if v else "") for k, v in row.items()}

                if not any(clean_row.values()):

                    continue

                questions.append(clean_row)

        total_questions = len(questions)

        if total_questions == 0:

            await update.message.reply_text("⚠️ CSV file is empty or invalid.")

            return ConversationHandler.END

        if total_questions > 60:

            questions = questions[:60]

            await update.message.reply_text(

                f"⚠️ CSV contains {total_questions} MCQs. Bot will only upload first 60 due to Telegram limits."

            )

        else:

            await update.message.reply_text(f"✅ CSV upload successful. {total_questions} MCQs detected.")

        context.user_data['questions'] = questions

        keyboard = [

            [InlineKeyboardButton("Bot", callback_data='bot')],

            [InlineKeyboardButton("Channel", callback_data='channel')]

        ]

        await update.message.reply_text(

            "Do you want to upload these quizzes to the bot or forward them to a channel?",

            reply_markup=InlineKeyboardMarkup(keyboard)

        )

        return CHOOSE_DESTINATION

    except Exception as e:

        logging.error(f"Error processing CSV file: {e}")

        await update.message.reply_text("❌ Failed to process CSV file.")

        return ConversationHandler.END

# -------------------------------

# Flood-safe message sending

# -------------------------------

async def send_message_with_retry(bot, chat_id, text):

    try:

        await bot.send_message(chat_id=chat_id, text=text)

    except RetryAfter as e:

        await asyncio.sleep(e.retry_after)

        await send_message_with_retry(bot, chat_id, text)

# -------------------------------

# Send polls in batches

# -------------------------------

async def send_all_polls(chat_id, context, questions):

    for q in questions:

        try:

            question_text = q.get("Question", "Untitled Question")

            options = [q.get("Option A", ""), q.get("Option B", ""), q.get("Option C", ""), q.get("Option D", "")]

            await context.bot.send_poll(chat_id, question=question_text, options=options, is_anonymous=False)

            await asyncio.sleep(2)

        except RetryAfter as e:

            await asyncio.sleep(e.retry_after)

        except Exception as e:

            logging.error(f"Error sending poll: {e}")

# -------------------------------

# Choose Destination (bot or channel)

# -------------------------------

async def choose_destination(update: Update, context: ContextTypes.DEFAULT_TYPE):

    query = update.callback_query

    await query.answer()

    user_id = query.from_user.id

    choice = query.data

    questions = context.user_data.get('questions', [])

    if choice == 'bot':

        chat_id = query.message.chat_id

        total_polls = len(questions)

        batch_size = 19

        sent_polls = 0

        for i in range(0, total_polls, batch_size):

            batch = questions[i:i + batch_size]

            await send_all_polls(chat_id, context, batch)

            sent_polls += len(batch)

            await send_message_with_retry(context.bot, chat_id, f"{sent_polls} polls sent to bot.")

            if i + batch_size < total_polls:

                await asyncio.sleep(30)

        await send_message_with_retry(context.bot, chat_id, f"Total of {sent_polls} quizzes sent to bot.")

        return ConversationHandler.END

    elif choice == 'channel':

        user_info = users_collection.find_one({'user_id': user_id})

        if 'channels' not in user_info or not user_info['channels']:

            await query.edit_message_text("⚠️ No channels found. Use /setchannel first.")

            return ConversationHandler.END

        if len(user_info['channels']) == 1:

            channel_id = user_info['channels'][0]

            total_polls = len(questions)

            batch_size = 19

            sent_polls = 0

            for i in range(0, total_polls, batch_size):

                batch = questions[i:i + batch_size]

                await send_all_polls(channel_id, context, batch)

                sent_polls += len(batch)

                await send_message_with_retry(context.bot, channel_id, f"{sent_polls} polls sent to channel {channel_id}.")

                if i + batch_size < total_polls:

                    await asyncio.sleep(30)

            await send_message_with_retry(context.bot, channel_id, f"Total of {sent_polls} quizzes sent to channel {channel_id}.")

            return ConversationHandler.END

        else:

            keyboard = [[InlineKeyboardButton(ch, callback_data=ch)] for ch in user_info['channels']]

            await query.edit_message_text("Choose a channel:", reply_markup=InlineKeyboardMarkup(keyboard))

            return CHOOSE_CHANNEL

# -------------------------------

# Channel selection callback

# -------------------------------

async def channel_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):

    query = update.callback_query

    await query.answer()

    channel_id = query.data

    questions = context.user_data.get('questions', [])

    total_polls = len(questions)

    batch_size = 19

    sent_polls = 0

    for i in range(0, total_polls, batch_size):

        batch = questions[i:i + batch_size]

        await send_all_polls(channel_id, context, batch)

        sent_polls += len(batch)

        await send_message_with_retry(context.bot, channel_id, f"{sent_polls} polls sent to {channel_id}.")

        if i + batch_size < total_polls:

            await asyncio.sleep(30)

    await send_message_with_retry(context.bot, channel_id, f"Total of {sent_polls} quizzes sent to {channel_id}.")

    return ConversationHandler.END

# -------------------------------

# Conversation Handler Setup

# -------------------------------

upload_csv_handler = ConversationHandler(

    entry_points=[CommandHandler("uploadcsv", upload_csv_command)],

    states={

        UPLOAD_CSV: [CallbackQueryHandler(handle_upload_choice)],

        COLLECT_TEXT: [

            MessageHandler(filters.TEXT & ~filters.COMMAND, collect_text_csv),

            CommandHandler("done", done_collecting)

        ],

        CHOOSE_DESTINATION: [CallbackQueryHandler(choose_destination)],

        CHOOSE_CHANNEL: [CallbackQueryHandler(channel_callback)],

    },

    fallbacks=[],

)

