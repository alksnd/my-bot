import os
from groq import Groq
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, LabeledPrice
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

# إعداد الاتصال
groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))
FREE_LIMIT = 3
user_counts = {}
paid_users = set()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [[InlineKeyboardButton("📱 منشور سوشيال ميديا", callback_data="social")],
                [InlineKeyboardButton("✨ اشتراك النجوم ✨", callback_data="sub_info")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("مرحباً بك! اختر نوع المحتوى:", reply_markup=reply_markup)

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.data == "sub_info":
        await update.effective_chat.send_message("ميزة الاشتراك قيد التفعيل...")
        return
    context.user_data["content_type"] = query.data
    await query.edit_message_text("✍️ أرسل موضوعك الآن:")

async def generate_content(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    user_counts[uid] = user_counts.get(uid, 0) + 1
    if user_counts[uid] > FREE_LIMIT:
        await update.message.reply_text("⚠️ انتهت محاولاتك المجانية!")
        return

    await update.message.reply_text("⏳ جاري الكتابة...")
    try:
        response = groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": update.message.text}],
            max_tokens=500
        )
        await update.message.reply_text(response.choices[0].message.content)
    except Exception as e:
        await update.message.reply_text(f"خطأ: {e}")

def main():
    token = os.getenv("TELEGRAM_TOKEN")
    app = Application.builder().token(token).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, generate_content))
    app.run_polling()

if __name__ == "__main__":
    main()
