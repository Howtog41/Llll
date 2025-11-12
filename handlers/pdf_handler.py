import os, fitz

from PIL import Image

from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton

from telegram.ext import ContextTypes, ConversationHandler, CommandHandler, MessageHandler, CallbackQueryHandler, filters

from telegram.constants import ParseMode

# States

PDF_FILE, SPLIT_CHOICE, PAGE_CHOICE, PAGE_RANGE = range(4)

# User-specific data storage

user_data = {}

async def convertpdf(update: Update, context: ContextTypes.DEFAULT_TYPE):

    await update.message.reply_text("📤 Kripya mujhe apna PDF bhejiye...")

    return PDF_FILE

async def get_pdf(update: Update, context: ContextTypes.DEFAULT_TYPE):

    doc = update.message.document

    if doc.mime_type != "application/pdf":

        await update.message.reply_text("❌ Sirf PDF file send karein.")

        return PDF_FILE

    if doc.file_size > 20 * 1024 * 1024:  # 20 MB limit

        await update.message.reply_text("⚠️ Ye PDF bahut badi hai. Max 20MB tak allowed hai.")

        return ConversationHandler.END

    file = await doc.get_file()

    user_data["pdf_path"] = await file.download_to_drive(custom_path="input.pdf")

    keyboard = [

        [InlineKeyboardButton("✅ Haan (Split Left/Right)", callback_data="split_yes")],

        [InlineKeyboardButton("❌ Nahi (Normal)", callback_data="split_no")]

    ]

    await update.message.reply_text(

        "Kya aap PDF pages ko left/right 2 parts me todna chahte ho?",

        reply_markup=InlineKeyboardMarkup(keyboard)

    )

    return SPLIT_CHOICE

async def split_choice(update: Update, context: ContextTypes.DEFAULT_TYPE):

    query = update.callback_query

    await query.answer()

    user_data["split"] = query.data == "split_yes"

    keyboard = [

        [InlineKeyboardButton("📕 All (max 20 pages)", callback_data="all")],

        [InlineKeyboardButton("🔢 Page Range", callback_data="range")]

    ]

    await query.edit_message_text(

        "Aapko pure PDF convert karna hai ya specific page range?",

        reply_markup=InlineKeyboardMarkup(keyboard)

    )

    return PAGE_CHOICE

async def page_choice(update: Update, context: ContextTypes.DEFAULT_TYPE):

    query = update.callback_query

    await query.answer()

    pdf_path = user_data["pdf_path"]

    split = user_data["split"]

    pdf_doc = fitz.open(pdf_path)

    if query.data == "all":

        pages = list(range(min(20, len(pdf_doc))))

        await process_pdf(update, context, pdf_doc, pages, split)

        return ConversationHandler.END

    else:

        await query.edit_message_text("✍️ Kripya page range dijiye (e.g. 20-40, max 20 pages):")

        return PAGE_RANGE

async def page_range(update: Update, context: ContextTypes.DEFAULT_TYPE):

    text = update.message.text.strip()

    pdf_path = user_data["pdf_path"]

    split = user_data["split"]

    pdf_doc = fitz.open(pdf_path)

    try:

        start, end = map(int, text.split("-"))

        if end - start + 1 > 20:

            await update.message.reply_text("⚠️ Ek baar me max 20 pages hi convert kar sakte ho.")

            return PAGE_RANGE

        pages = list(range(start-1, min(end, len(pdf_doc))))

        await process_pdf(update, context, pdf_doc, pages, split)

        return ConversationHandler.END

    except Exception:

        await update.message.reply_text("❌ Invalid format. Example: 5-20")

        return PAGE_RANGE

async def process_pdf(update, context, pdf_doc, pages, split):

    chat_id = update.effective_chat.id

    for page_num in pages:

        page = pdf_doc[page_num]

        pix = page.get_pixmap(matrix=fitz.Matrix(2.5, 2.5))

        img_path = f"page_{page_num+1}.png"

        pix.save(img_path)

        if split:

            img = Image.open(img_path)

            w, h = img.size

            left = img.crop((0, 0, w//2, h))

            right = img.crop((w//2, 0, w, h))

            left.save("left.png")

            right.save("right.png")

            await context.bot.send_photo(chat_id, photo=open("left.png", "rb"),

                                         caption=f"📄 Page {page_num+1} (Left)")

            await context.bot.send_photo(chat_id, photo=open("right.png", "rb"),

                                         caption=f"📄 Page {page_num+1} (Right)")

            os.remove("left.png")

            os.remove("right.png")

        else:

            await context.bot.send_photo(chat_id, photo=open(img_path, "rb"),

                                         caption=f"📄 Page {page_num+1}")

        os.remove(img_path)

    pdf_doc.close()

    os.remove(user_data["pdf_path"])

    

    keyboard = [

        [InlineKeyboardButton("🔹 OCR with @TranslateIDrobot", url="https://t.me/TranslateIDrobot")],

        [InlineKeyboardButton("🔹 Convert to CSV with @gpt3_unlim_chatbot", url="https://t.me/gpt3_unlim_chatbot")],

        [InlineKeyboardButton("🔹 Convert to CSV with chatgpt Web", url="https://chatgpt.com")],

        [InlineKeyboardButton("🔹 CSV Code To CSV File ", url="https://tableconvert.com/csv-to-csv")]

    ]

    reply_markup = InlineKeyboardMarkup(keyboard)

    LONG_GUIDE_MESSAGE = """✅ Conversion Complete!  

    अब आपके पास PDF से निकली हुई IMAGES आ चुकी हैं। अब अगला प्रोसेस ये है 👇  

    📌 Step 1: सबसे पहले इन IMAGES का OCR करना है।  

    इसके लिए नीचे दिए गए बटन से @TranslateIDrobot को खोलें और हर एक IMAGE वहां भेजें।  

    ➡️ Bot आपको IMAGE से निकला TEXT वापस देगा।  

    📌 Step 2: अब आपके पास OCR से मिला हुआ TEXT है।  

    अब नीचे दिए गए बटन से @gpt3_unlim_chatbot को खोलें।  

    ⚠️ इस bot को पहले /start करके पुराना CACHE क्लियर कर लें।  

    📌 Step 3: अब इस bot को नीचे वाला MESSAGE भेजें (copy–paste करें):  

    👇👇👇👇👇Tap and copy 👇👇👇👇👇

    <pre><code>

    Mene jo question or unke answe bheje hai unko csv ꜰᴏʀᴍᴀᴛ:

    "Question", "Option A", "Option B", "Option C", "Option D", "Answer","Description"

    Bnakar de sakte ho yhi pr chia Muje code Format me file mt dena

    Note:- Answer should be A B C D Format

    Note:- Description 240 characters se jyada nahi hona chahiye

    </code></pre>

    

    📌 Step 4: OCR से निकला हुआ TEXT इस message के बाद भेज दें।  

    ➡️ Bot आपको उसी TEXT का तैयार CSV बना कर देगा।

    """

    await context.bot.send_message(

        chat_id=chat_id,

        text=LONG_GUIDE_MESSAGE,

        reply_markup=reply_markup,

        parse_mode=ParseMode.HTML

    )

def get_pdf_conversation_handler():

    return ConversationHandler(

        entry_points=[CommandHandler("convertpdf", convertpdf)],

        states={

            PDF_FILE: [MessageHandler(filters.Document.PDF, get_pdf)],

            SPLIT_CHOICE: [CallbackQueryHandler(split_choice)],

            PAGE_CHOICE: [CallbackQueryHandler(page_choice)],

            PAGE_RANGE: [MessageHandler(filters.TEXT & ~filters.COMMAND, page_range)],

        },

        fallbacks=[],

        allow_reentry=True

  )