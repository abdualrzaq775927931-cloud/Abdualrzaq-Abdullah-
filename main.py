import asyncio
import logging
import sys

# إعداد السجلات (Logging) لمتابعة الأداء وتصحيح الأخطاء في Railway
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

from telegram.ext import (
    ApplicationBuilder, 
    CommandHandler, 
    MessageHandler, 
    CallbackQueryHandler, 
    filters
)

# 1. استيراد الإعدادات والذاكرة
import config
from database.db import Base, engine, get_session
from services.scheduler_service import scheduler_worker

# 2. استيراد معالجات الأوامر (Handlers) من مجلد bot
from bot.handlers import (
    start_handler, 
    add_quiz_command, 
    post_now_command, 
    list_channels_handler, 
    callback_handler
)
from bot.content_handlers import handle_incoming_content
from bot.admin_panel import (
    admin_main_menu, 
    admin_callback_handler, 
    set_user_limit_command, 
    broadcast_command
)

async def init_database():
    """تجهيز جداول قاعدة البيانات عند التشغيل الأول"""
    try:
        logger.info("⚙️ Initializing database tables...")
        # استخدام engine.begin للتعامل مع قاعدة البيانات بشكل صحيح
        Base.metadata.create_all(bind=engine)
        logger.info("✅ Database is ready.")
    except Exception as e:
        logger.error(f"❌ Database error: {e}")
        raise

async def main():
    # أ. تهيئة قاعدة البيانات قبل البدء
    await init_database()

    # ب. بناء تطبيق التليجرام باستخدام التوكن من الإعدادات
    if not config.BOT_TOKEN:
        logger.critical("❌ BOT_TOKEN is missing in config/environment!")
        return

    application = ApplicationBuilder().token(config.BOT_TOKEN).build()

    # --- تسجيل المعالجات (Handlers Registration) ---

    # 1. الأوامر العامة للمستخدمين (Teachers)
    application.add_handler(CommandHandler("start", start_handler))
    application.add_handler(CommandHandler("add_quiz", add_quiz_command))
    application.add_handler(CommandHandler("post_now", post_now_command))
    application.add_handler(CommandHandler("list_channels", list_channels_handler))
    application.add_handler(CommandHandler("add_channel", lambda u, c: u.message.reply_text("🔗 لربط قناة، قم بعمل Forward لرسالة منها إلى هنا.")))

    # 2. أوامر لوحة التحكم (للمالك فقط)
    application.add_handler(CommandHandler("admin", admin_main_menu))
    application.add_handler(CommandHandler("set_limit", set_user_limit_command))
    application.add_handler(CommandHandler("broadcast", broadcast_command))

    # 3. معالج المحتوى الذكي (الوسائط والرسائل المحولة لربط القنوات)
    # هذا المعالج يتعامل مع: الرسائل المحولة من القنوات، الصور، الفيديوهات، الملفات الصوتية، والمستندات.
    application.add_handler(MessageHandler(
        (filters.FORWARDED & filters.ChatType.CHANNEL) | 
        filters.PHOTO | 
        filters.VIDEO | 
        filters.Document.ALL | 
        filters.Audio, 
        handle_incoming_content
    ))

    # 4. معالج الأزرار التفاعلية (Callback Queries)
    # يدعم الأزرار التي تبدأ بـ 'adm_' للوحة التحكم، والبقية للجدولة العامة
    application.add_handler(CallbackQueryHandler(admin_callback_handler, pattern="^adm_"))
    application.add_handler(CallbackQueryHandler(callback_handler))

    # ج. تشغيل عامل الجدولة (Scheduler) في الخلفية كـ Task مستقل
    # هذا يسمح للبوت بالتحقق من أوقات النشر كل دقيقة دون توقف
    asyncio.create_task(scheduler_worker(application.bot))
    logger.info("⏰ Scheduler worker is active in the background.")

    # د. انطلاق البوت رسمياً واستقبال الرسائل (Polling)
    logger.info("🚀 Smart Publisher Bot has started successfully.")
    
    # استخدام run_polling لبدء البوت في بيئة التطوير والإنتاج (Railway)
    await application.run_polling()

if __name__ == '__main__':
    try:
        # تشغيل حلقة الأحداث (Event Loop)
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("👋 Bot has been stopped manually.")
    except Exception as e:
        logger.error(f"🔥 Critical error: {e}")
