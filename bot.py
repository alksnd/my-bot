import os
import asyncio
from dotenv import load_dotenv
from groq import Groq
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, LabeledPrice
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

# 1. إعداد الاتصال والبيئة
load_dotenv()
# تأكد من إضافة المفاتيح في إعدادات السيرفر أو ملف .env
groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))

# 2. إعدادات الحدود (في الذاكرة - سيتم تصديرها عند إعادة تشغيل البوت)
paid_users = set()
FREE_LIMIT = 3
user_counts = {}

max_tokens_map = {
    "social": 300,
    "blog": 1200,
    "ad": 400,
    "email": 600,
    "product": 500
}

# 3. القائمة الرئيسية
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("📱 منشور سوشيال ميديا", callback_data="social")],
        [InlineKeyboardButton("📝 مقال بلوق", callback_data="blog")],
        [InlineKeyboardButton("📢 إعلان تسويقي", callback_data="ad")],
        [InlineKeyboardButton("📦 وصف منتج", callback_data="product")],
        [InlineKeyboardButton("✨ اشتراك النجوم ✨", callback_data="sub_info")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("مرحباً بك! اختر نوع المحتوى الذي تريده:", reply_markup=reply_markup)

# 4. نظام الاشتراك
async def subscribe(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # في حال كان النداء من زر (CallbackQuery)
    chat_id = update.effective_chat.id
    await context.bot.send_invoice(
        chat_id=chat_id,
        title="✨ النسخة الاحترافية ✨",
        description="استخدام غير محدود لكافة الأدوات",
        payload="monthly_sub",
        provider_token="", # اتركها فارغة في حال استخدام Telegram Stars (XTR)
        currency="XTR",
        prices=[LabeledPrice("اشتراك شهري", 100)]
    )

async def successful_payment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    paid_users.add(uid)
    user_counts[uid] = 0
    await update.message.reply_text("✅ تم تفعيل الاشتراك بنجاح! استمتع بميزات البريميوم. ✅")

# 5. معالج الأزرار
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if query.data == "sub_info":
        await subscribe(update, context)
        return

    context.user_data["content_type"] = query.data
    prompts = {
        "social": "✍️ أرسل الموضوع وسأكتب منشوراً جذاباً:",
        "blog": "✍️ أعطني عنوان المقال وسأكتبه لك:",
        "ad": "✍️ أخبرني عن المنتج وسأكتب إعلاناً مقنعاً:",
        "product": "✍️ أرسل اسم المنتج ومميزاته لوصفه بيعياً:"
    }
    await query.edit_message_text(prompts.get(query.data, "تفضل بإرسال موضوعك:"))

# 6. توليد المحتوى بواسطة الذكاء الاصطناعي
async def generate_content(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    
    # التحقق من الحدود المجانية
    user_counts[uid] = user_counts.get(uid, 0) + 1
    if uid not in paid_users and user_counts[uid] > FREE_LIMIT:
        await update.message.reply_text("⚠️ انتهت طلباتك المجانية! للاستمرار يرجى الاشتراك عبر الأمر /subscribe")
        return

    content_type = context.user_data.get("content_type", "social")
    system_prompts = {
        "social": "أنت خبير سوشيال ميديا. اكتب منشوراً جذاباً ومختصراً بالعربية.",
        "blog": "أنت كاتب محتوى محترف. اكتب مقالاً منظماً بعناوين فرعية بالعربية.",
        "ad": "أنت متخصص في الإعلانات. اكتب إعلاناً تسويقياً مقنعاً بالعربية.",
        "product": "أنت خبير تجارة إلكترونية. اكتب وصفاً جذاباً للمنتج يركز على الفوائد."
    }

    status_msg = await update.message.reply_text("⏳ جاري التفكير والكتابة...")
    
    try:
        response = groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": system_prompts.get(content_type, "اكتب رداً مفيداً بالعربية")},
                {"role": "user", "content": update.message.text}
            ],
            max_tokens=max_tokens_map.get(content_type, 500)
        )
        result = response.choices[0].message.content
        
        remaining = max(0, FREE_LIMIT - user_counts[uid])
        footer = f"\n\n---\n💡 متبقي {remaining} طلبات مجانية" if uid not in paid_users else "\n\n---\n👑 حساب بريميوم"
        
        await status_msg.edit_text(result + footer)
        
    except Exception as e:
        await status_msg.edit_text(f"❌ حدث خطأ تقني: {e}")

# 7. تشغيل البوت
def main():
    token = os.getenv("TELEGRAM_TOKEN")
    if not token:
        print("خطأ: لم يتم العثور على TELEGRAM_TOKEN!")
        return

    app = Application.builder().token(token).build()

    # ربط الأوامر والمعالجات
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("subscribe", subscribe))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.SUCCESSFUL_PAYMENT, successful_payment))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, generate_content))
    
    print("🚀 البوت بدأ العمل الآن...")
    app.run_polling()

if __name__ == "__main__":
    main()

