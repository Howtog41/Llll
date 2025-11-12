from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CallbackQueryHandler
from helpers.db import users_collection
from config import ADMIN_ID


async def set_channel(update: Update, context: ContextTypes.DEFAULT_TYPE):

    user_id = update.effective_user.id
    user_info = users_collection.find_one({'user_id': user_id})

    if user_id == ADMIN_ID or (user_info and user_info.get('authorized', False)):

        try:

            channel_id = context.args[0]

            users_collection.update_one({'user_id': user_id}, {'$addToSet': {'channels': channel_id}})

            await update.message.reply_text(f"Channel ID {channel_id} has been added.")

        except IndexError:

            await update.message.reply_text("Usage: /setchannel <channel_id>")

    else:

        await update.message.reply_text("You are not authorized to use this command.")

# Command to manage channels



async def channels(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_info = users_collection.find_one({'user_id': user_id})

    if user_id == ADMIN_ID or (user_info and user_info.get('authorized', False)): # Check if the user is the admin
        

        # Get the list of channels (assuming it's a list of strings)
        channels = user_info.get('channels', [])

        if not channels:  # If no channels are set
            await update.message.reply_text(
                "No channels are set. Use /setchannel <channel_name> to add a new channel."
            )
            return

        # Create inline keyboard with channel names
        keyboard = [
            [
                InlineKeyboardButton(
                    channel, callback_data=f"remove_prompt_{channel}"
                )
                for channel in channels
            ],
            [InlineKeyboardButton("Add new channel", callback_data="add_channel")],
            [InlineKeyboardButton("Back", callback_data="back")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await update.message.reply_text("Manage your channels:", reply_markup=reply_markup)
    else:
        await update.message.reply_text("You are not authorized to use this command.")

# Callback handler for channel management
async def channel_management_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    callback_data = query.data

    if callback_data.startswith("remove_prompt_"):
        channel_name = callback_data.replace("remove_prompt_", "")

        # Ask for confirmation before removing the channel
        keyboard = [
            [
                InlineKeyboardButton("Yes, remove", callback_data=f"remove_confirm_{channel_name}"),
                InlineKeyboardButton("No, cancel", callback_data="cancel")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(
            f"Are you sure you want to remove the channel: {channel_name}?",
            reply_markup=reply_markup
        )

    elif callback_data.startswith("remove_confirm_"):
        channel_name = callback_data.replace("remove_confirm_", "")

        # Remove the channel from the database
        users_collection.update_one(
            {'user_id': update.effective_user.id},
            {'$pull': {'channels': channel_name}}
        )

        await query.edit_message_text("Channel removed successfully!")

    elif callback_data == "add_channel":
        await query.edit_message_text("Send the channel details to add it.")

    elif callback_data == "cancel":
        await query.edit_message_text("Action canceled.")

    elif callback_data == "back":
        await channels(update, context)

