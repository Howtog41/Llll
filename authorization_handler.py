from telegram import Update
from telegram.ext import ContextTypes
from helpers.db import users_collection
from config import ADMIN_ID
from datetime import datetime, timedelta

async def authorize(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    if user_id == ADMIN_ID:
        try:
            new_user_id = int(context.args[0])
            days = int(context.args[1]) if len(context.args) > 1 else 3
            now = datetime.now()
            expires = now + timedelta(days=days)

            users_collection.update_one(
                {'user_id': new_user_id},
                {'$set': {
                    'authorized': True,
                    'authorized_on': now,
                    'expires_on': expires
                }},
                upsert=True
            )

            await update.message.reply_text(
                f"✅ User {new_user_id} has been authorized for {days} days (until {expires.strftime('%Y-%m-%d')})."
            )
        except IndexError:
            await update.message.reply_text("Usage: /authorize <user_id> [days]")
        except ValueError:
            await update.message.reply_text("❌ Please enter valid numeric values.")
    else:
        await update.message.reply_text("⛔ You are not authorized to use this command.")
