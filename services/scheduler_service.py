import logging
import asyncio
from datetime import datetime
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from services.queue_service import queue_manager
from services.publish_service import publisher

# إعداد السجلات (Logs) لمراقبة عمل المجدول في Railway
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

class SchedulerService:
    def __init__(self):
        # استخدام المجدول المتوافق مع نظام البرمجة غير المتزامنة (Asyncio)
        self.scheduler = AsyncIOScheduler()

    async def check_and_publish(self):
        """
        الوظيفة: فحص قاعدة البيانات كل دقيقة لجلب المنشورات التي حان وقتها ونشرها.
        """
        logger.info("⏰ Scheduler: Checking queue for pending posts...")
        
        # 1. جلب المنشورات التي حالتها 'pending' وحان وقت نشرها
        try:
            pending_posts = queue_manager.get_pending_posts()
            
            if not pending_posts:
                logger.info("Scheduler: No posts to publish right now.")
                return

            for post in pending_posts:
                logger.info(f"🚀 Processing Post ID {post.id} for Channel {post.target_channel_id}")
                
                # 2. إرسال المنشور (نص، صورة، فيديو، كويز، إلخ) عبر خدمة النشر
                success, error = await publisher.send_post(
                    channel_id=post.target_channel_id,
                    content_type=post.content_type,
                    text_content=post.text_content,
                    file_id=post.file_id,
                    caption=post.caption,
                    metadata_json=post.metadata_json
                )
                
                if success:
                    # 3. تحديث حالة المنشور في قاعدة البيانات لمنع التكرار
                    queue_manager.mark_as_posted(post.id)
                    logger.info(f"✅ Success: Post ID {post.id} published.")
                else:
                    # في حالة الفشل (مثلاً البوت ليس مشرفاً)، يتم تسجيل الخطأ
                    logger.error(f"❌ Failed: Post ID {post.id} - Error: {error}")
                    
        except Exception as e:
            logger.error(f"❌ Scheduler Error: {str(e)}")

    def start(self):
        """
        تشغيل المجدول ليعمل في الخلفية بشكل مستقل.
        """
        if not self.scheduler.running:
            # إضافة المهمة لتعمل كل (1) دقيقة بشكل متكرر
            self.scheduler.add_job(
                self.check_and_publish, 
                'interval', 
                minutes=1,
                id='main_publish_job',
                replace_existing=True
            )
            self.scheduler.start()
            logger.info("🚀 Scheduler service started. Monitoring queue every 60 seconds.")
        else:
            logger.warning("Scheduler is already active.")

# تصدير نسخة جاهزة للاستخدام ليتم استدعاؤها في main.py
scheduler_handler = SchedulerService()
