import os, asyncio
from dotenv import load_dotenv
from groq import Groq
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, LabeledPrice
from telegram.ext import Application, CommandHandler, MessageHandler, \
    CallbackQueryHandler, filters, ContextTypes

# إعدادات البيئة
load_dotenv()
groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))

# ذاكرة المستخدمين المؤقتة
paid_users = set()
FREE_LIMIT = 3
user_counts = {}

# خريطة طول المحتوى (التي حددتها أنت)
max_tokens_map = {
    "social": 300,
    "blog": 1200,
    "ad": 400,
    "email": 600,
    "product": 500
}

async def start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("منشور سوشيال ميديا", callback_data="social")],
        [InlineKeyboardButton("مقال بلوق", callback_data="blog")],
        [InlineKeyboardButton("إعلان تسويقي", callback_data="ad")],
        [InlineKeyboardButton("إيميل احترافي", callback_data="email")],
        [InlineKeyboardButton("وصف منتج 🛍️", callback_data="product")],
        [InlineKeyboardButton("🌟 اشترك بالنجوم", callback_data="sub_info")],
    ]
    await update.message.reply_text(
        "مرحباً بك! اختر نوع المحتوى الذي تريده:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def subscribe(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await ctx.bot.send_invoice(
        chat_id=update.effective_chat.id,
        title="النسخة الاحترافية 🌟",
        description="استخدام غير محدود لكافة الأدوات",
        payload="monthly_sub",
        currency="XTR", 
        prices=[LabeledPrice("اشتراك شهري", 100)]
    )

async def successful_payment(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    paid_users.add(uid)
    user_counts[uid] = 0
    await update.message.reply_text("✅ تم الاشتراك بنجاح! استمتع باستخدام غير محدود.")

async def button_handler(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if query.data == "sub_info":
        await subscribe(update, ctx)
        return

    ctx.user_data["content_type"] = query.data
    prompts = {
        "social": "أرسل الموضوع وسأكتب منشوراً جذاباً",
        "blog": "أعطني عنوان المقال وسأكتبه لك",
        "ad": "أخبرني عن المنتج وسأكتب إعلاناً مقنعاً",
        "email": "أخبرني الغرض من الإيميل وسأكتبه",
        "product": "أرسل اسم المنتج ومميزاته لوصفه بيعياً",
    }
    await query.message.reply_text(prompts.get(query.data))

async def generate_content(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    user_counts[uid] = user_counts.get(uid, 0) + 1

    if uid not in paid_users and user_counts[uid] > FREE_LIMIT:
        await update.message.reply_text("⚠️ انتهت طلباتك المجانية! للاشتراك: /subscribe")
        return

    content_type = ctx.user_data.get("content_type", "social")
    system_prompts = {
        "social": "أنت خبير سوشيال ميديا. اكتب منشوراً جذاباً بالعربية.",
        "blog": "أنت كاتب محتوى محترف. اكتب مقالاً منظماً بالعربية.",
        "ad": "أنت متخصص في التسويق. اكتب إعلاناً مقنعاً.",
        "email": "أنت كاتب بريد إلكتروني محترف. اكتب إيميلاً رسمياً.",
        "product": "أنت كاتب تجارة إلكترونية. اكتب وصفاً جذاباً للمنتج يبرز مميزاته.",
    }

    await update.message.reply_text("جاري الكتابة... ✍️")

    try:
        response = groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": system_prompts.get(content_type, "اكتب رداً مفيداً")},
                {"role": "user", "content": update.message.text}
            ],
            max_tokens=max_tokens_map.get(content_type, 500)
        )
        result = response.choices.message.content
        remaining = max(0, FREE_LIMIT - user_counts[uid])
        footer = f"\n\n— متبقي {remaining} طلبات مجانية" if uid not in paid_users else "✨ حساب بريميوم"
        await update.message.reply_text(result + footer)
    except:
        await update.message.reply_text("عذراً، حدث خطأ تقني.")

def main():
    app = Application.builder().token(os.getenv("TELEGRAM_TOKEN")).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("subscribe", subscribe))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.SUCCESSFUL_PAYMENT, successful_payment))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, generate_content))
    
    app.run_polling()

if __name__ == "__main__":
    main()
