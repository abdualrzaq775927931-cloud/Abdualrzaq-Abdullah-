import logging
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from database.db import get_session, User, Channel, get_or_create_user
from services.queue_service import queue_manager
from services.publish_service import publisher

# إعداد الـ Logger لتتبع الأخطاء في السيرفر
logger = logging.getLogger(__name__)

# --- وظائف مساعدة ---

def get_user_channels(user_id):
    session = get_session()
    channels = session.query(Channel).filter(Channel.owner_id == user_id).all()
    session.close()
    return channels

def build_channel_keyboard(channels, callback_prefix):
    buttons = [[InlineKeyboardButton(ch.title, callback_data=f"{callback_prefix}:{ch.channel_id}")] for ch in channels]
    return InlineKeyboardMarkup(buttons)

# --- المعالجات (Handlers) ---

async def start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_tg = update.effective_user
    get_or_create_user(user_tg.id, user_tg.username, user_tg.full_name)
    
    msg = (
        f"👋 أهلاً بك {user_tg.first_name}\n\n"
        "🚀 **أوامر التحكم:**\n"
        "• `/add_quiz` : إضافة اختبار مجدول\n"
        "• `/post_now` : نشر نص فوراً\n"
        "• `/add_channel` : ربط قناة/مجموعة\n"
        "• `/list_channels` : عرض قنواتك"
    )
    await update.message.reply_text(msg, parse_mode='Markdown')

async def add_quiz_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    الصيغة: /add_quiz الإجابة ; السؤال ; [الوقت بالدقائق اختياري] ; خيار1 ; خيار2 ...
    """
    user_id = update.effective_user.id
    raw_text = " ".join(context.args)
    
    if not raw_text or ";" not in raw_text:
        example = "`/add_quiz went ; Yesterday I ___ to school ; 30 ; go ; went ; gone`"
        await update.message.reply_text(f"⚠️ **صيغة خاطئة!**\nالاستخدام:\n{example}\n*(ملاحظة: الوقت بالدقائق اختياري، الافتراضي 60 دقيقة)*", parse_mode='Markdown')
        return

    try:
        parts = [p.strip() for p in raw_text.split(";")]
        # التحقق إذا كان الجزء الثالث رقماً (وقت) أم خياراً
        if parts[2].isdigit():
            wait_mins = int(parts[2])
            options = parts[3:]
        else:
            wait_mins = 60 # افتراضي ساعة
            options = parts[2:]

        correct_ans = parts[0]
        question = parts[1]

        if correct_ans not in options:
            await update.message.reply_text(f"❌ الإجابة `{correct_ans}` غير موجودة في الخيارات!", parse_mode='Markdown')
            return

        # تخزين البيانات مؤقتاً
        context.user_data['temp_quiz'] = {
            "metadata": {"question": question, "options": options, "correct_index": options.index(correct_ans)},
            "wait_mins": wait_mins
        }

        channels = get_user_channels(user_id)
        if not channels:
            await update.message.reply_text("❌ اربط قناة أولاً عبر عمل Forward لرسالة منها.")
            return

        await update.message.reply_text("🎯 اختر القناة للجدولة:", reply_markup=build_channel_keyboard(channels, "q_sel"))
    except Exception:
        logger.exception("Error in add_quiz_command")
        await update.message.reply_text("❌ حدث خطأ في معالجة البيانات.")

async def post_now_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = " ".join(context.args)
    if not text:
        await update.message.reply_text("✍️ اكتب النص المراد نشره فوراً بعد الأمر.")
        return

    context.user_data['temp_text'] = text
    channels = get_user_channels(update.effective_user.id)
    if not channels:
        await update.message.reply_text("❌ لا توجد قنوات مربوطة.")
        return

    await update.message.reply_text("🚀 اختر القناة للنشر الفوري الآن:", reply_markup=build_channel_keyboard(channels, "p_now"))

# --- معالج الأزرار (Callback) ---

async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    data = query.data.split(":")
    action, ch_id = data[0], int(data[1])
    user_id = update.effective_user.id

    # التحقق من المستخدم والحد اليومي
    session = get_session()
    user = session.query(User).filter(User.tg_id == user_id).first()
    
    if user.posts_today >= user.daily_post_limit:
        await query.edit_message_text(f"🚫 عذراً! تجاوزت الحد اليومي ({user.daily_post_limit}) منشوراً.")
        session.close()
        return
    session.close()

    try:
        if action == "q_sel":
            quiz = context.user_data.get('temp_quiz')
            if not quiz:
                await query.edit_message_text("⚠️ انتهت الجلسة. يرجى إعادة إرسال الأمر.")
                return

            pub_time = datetime.utcnow() + timedelta(minutes=quiz['wait_mins'])
            success, msg = queue_manager.add_to_queue(
                user_id=user_id, channel_id=ch_id, content_type="quiz",
                metadata=quiz['metadata'], scheduled_at=pub_time
            )
            await query.edit_message_text(f"✅ تم الجدولة!\n📅 الموعد: `{pub_time.strftime('%H:%M')}` UTC", parse_mode='Markdown')

        elif action == "p_now":
            content = context.user_data.get('temp_text')
            if not content:
                await query.edit_message_text("⚠️ البيانات مفقودة. أعد المحاولة.")
                return

            # النشر الفوري المباشر
            success, err = await publisher.send_post(channel_id=ch_id, content_type="text", text_content=content)
            if success:
                # تحديث العداد حتى في النشر الفوري
                queue_manager.add_to_queue(user_id=user_id, channel_id=ch_id, content_type="text", text_content=content, status="posted")
                await query.edit_message_text("✅ تم النشر بنجاح فوراً!")
            else:
                await query.edit_message_text(f"❌ فشل النشر: {err}")
    except Exception:
        logger.exception("Error in callback_handler")
        await query.edit_message_text("❌ حدث خطأ داخلي.")
      
