from telegram.ext import CommandHandler
from config import ADMIN_ID
from helpers.db import users_collection

async def broadcast(update, context):
    user_id = update.effective_user.id

    # Sirf Admin broadcast kar sake
    if user_id != ADMIN_ID:
        await update.message.reply_text("🚫 Only admin can use this command.")
        return

    # Jo message broadcast karna hai
    if not context.args:
        await update.message.reply_text("⚠️ Usage: /broadcast <message>")
        return

    message = " ".join(context.args)

    # MongoDB se sabhi users ka user_id nikaalna
    all_users = users_collection.find({}, {"user_id": 1})
    sent_count = 0

    for user in all_users:
        try:
            await context.bot.send_message(chat_id=user["user_id"], text=message)
            sent_count += 1
        except Exception as e:
            print(f"Failed to send to {user['user_id']}: {e}")

    await update.message.reply_text(f"✅ Broadcast sent to {sent_count} users.")

def setup_broadcast_handlers(app):
    app.add_handler(CommandHandler("broadcast", broadcast))

