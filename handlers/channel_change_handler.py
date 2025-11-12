import re
from telegram import Update
from telegram.ext import CommandHandler, MessageHandler, filters, ConversationHandler

# Define states
CHANNEL, MESSAGE = range(2)

# Store user data
user_data = {}

# Remove the start function, as it is no longer needed

async def change_channel(update: Update, context) -> int:
    await update.message.reply_text('Please enter the new CHANNEL name:')
    return CHANNEL

async def set_channel_name(update: Update, context) -> int:
    user_data['channel_name'] = update.message.text
    await update.message.reply_text('Please send your messages (text, photos, or videos). When you are done, click /done.')
    return MESSAGE

async def receive_message(update: Update, context) -> int:
    if 'messages' not in user_data:
        user_data['messages'] = []

    if update.message.text:
        user_data['messages'].append(update.message.text)
    elif update.message.photo:
        file_id = update.message.photo[-1].file_id
        caption = update.message.caption if update.message.caption else ""
        user_data['messages'].append({'photo': file_id, 'caption': caption})
    elif update.message.video:
        file_id = update.message.video.file_id
        caption = update.message.caption if update.message.caption else ""
        user_data['messages'].append({'video': file_id, 'caption': caption})

    return MESSAGE

async def done(update: Update, context) -> int:
    channel_name = user_data.get('channel_name', '@SecondCoaching')
    messages = user_data.get('messages', [])
    updated_messages = []

    for message in messages:
        if isinstance(message, str):
            updated_message = replace_channel_name(message, channel_name)
            updated_messages.append(updated_message)
        elif isinstance(message, dict):
            if 'photo' in message:
                updated_caption = replace_channel_name(message['caption'], channel_name)
                updated_messages.append({'photo': message['photo'], 'caption': updated_caption})
            elif 'video' in message:
                updated_caption = replace_channel_name(message['caption'], channel_name)
                updated_messages.append({'video': message['video'], 'caption': updated_caption})

    for msg in updated_messages:
        if isinstance(msg, str):
            await update.message.reply_text(msg)
        elif isinstance(msg, dict):
            if 'photo' in msg:
                await update.message.reply_photo(photo=msg['photo'], caption=msg['caption'])
            elif 'video' in msg:
                await update.message.reply_video(video=msg['video'], caption=msg['caption'])

    # Clear user data
    user_data.clear()
    return ConversationHandler.END

def replace_channel_name(message: str, new_channel: str) -> str:
    # Regex to find @mentions or Telegram links
    channel_name_pattern = re.compile(r'@[\w.]+')
    telegram_link_pattern = re.compile(r'https://t\.me/\w+\?start=\d+')

    updated_message = message
    # Replace all occurrences of channel names and Telegram links
    updated_message = channel_name_pattern.sub(new_channel, updated_message)
    updated_message = telegram_link_pattern.sub(new_channel, updated_message)

    return updated_message
