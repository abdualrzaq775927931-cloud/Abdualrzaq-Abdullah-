import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from database.db import get_session, Channel, User, get_or_create_user
from services.queue_service import queue_manager

# إعداد السجلات لتتبع العمليات في Railway
logger = logging.getLogger(__name__)

async def handle_incoming_content(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    المعالج الرئيسي للمحتوى الوارد:
    1. رسائل محولة (Forward) لربط القنوات/المجموعات.
    2. وسائط (صور، فيديو، ملفات) للجدولة.
    """
    user_tg = update.effective_user
    # التأكد من وجود المستخدم في قاعدة البيانات (تسجيل تلقائي)
    user = get_or_create_user(user_tg.id, user_tg.username, user_tg.full_name)

    # --- أولاً: التعامل مع الرسائل المحولة (لربط القنوات) ---
    if update.message.forward_from_chat:
        f_chat = update.message.forward_from_chat
        # التأكد أنها قناة أو مجموعة
        if f_chat.type in ["channel", "group", "supergroup"]:
            session = get_session()
            try:
                # التحقق إذا كانت القناة مضافة مسبقاً
                exists = session.query(Channel).filter(Channel.channel_id == f_chat.id).first()
                if exists:
                    await update.message.reply_text("⚠️ هذه القناة/المجموعة مربوطة بالفعل بنظامنا.")
                    return

                new_channel = Channel(
                    channel_id=f_chat.id,
                    title=f_chat.title or "بدون عنوان",
                    owner_id=user_tg.id
                )
                session.add(new_channel)
                session.commit()
                
                type_ar = "قناة" if f_chat.type == "channel" else "مجموعة"
                await update.message.reply_text(
                    f"✅ تم ربط {type_ar} بنجاح!\n"
                    f"📌 الاسم: **{f_chat.title}**\n"
                    f"🆔 المعرف: `{f_chat.id}`", 
                    parse_mode='Markdown'
                )
            except Exception as e:
                logger.error(f"Error in linking channel: {str(e)}")
                await update.message.reply_text("❌ حدث خطأ أثناء محاولة ربط القناة.")
            finally:
                session.close()
            return

    # --- ثانياً: التعامل مع الوسائط (صور، فيديوهات، ملفات) للجدولة ---
    content_type = None
    file_id = None
    caption = update.message.caption or ""

    if update.message.photo:
        content_type = "photo"
        file_id = update.message.photo[-1].file_id  # اختيار أعلى جودة
    elif update.message.video:
        content_type = "video"
        file_id = update.message.video.file_id
    elif update.message.audio:
        content_type = "audio"
        file_id = update.message.audio.file_id
    elif update.message.document:
        content_type = "document"
        file_id = update.message.document.file_id

    if content_type:
        # حفظ بيانات الوسائط مؤقتاً في جلسة المستخدم
        context.user_data['temp_media'] = {
            "type": content_type,
            "file_id": file_id,
            "caption": caption
        }
        
        # جلب قائمة القنوات المربوطة بهذا المستخدم
        from bot.handlers import get_user_channels, build_channel_keyboard
        channels = get_user_channels(user_tg.id)
        
        if not channels:
            await update.message.reply_text(
                "❌ لا يمكنك جدولة وسائط قبل ربط قناة.\n"
                "قم بعمل Forward لرسالة من قناتك المربوطة أولاً."
            )
            return

        # عرض قائمة القنوات كأزرار ليختار المستخدم أين يريد الجدولة
        reply_markup = build_channel_keyboard(channels, "media_sel")
        await update.message.reply_text(
            f"📦 استلمت {content_type} بنجاح.\n"
            "في أي قناة تريد جدولة هذا المحتوى؟", 
            reply_markup=reply_markup
          )
      
