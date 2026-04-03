import json
import logging
from datetime import datetime
from database.db import get_session, ContentQueue, User
from sqlalchemy import func

# إعداد السجلات
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class QueueService:
    def __init__(self):
        self.session_factory = get_session

    def add_to_queue(self, user_id, channel_id, content_type, text_content=None, file_id=None, caption=None, metadata=None, scheduled_at=None):
        """إضافة منشور جديد إلى طابور النشر"""
        session = self.session_factory()
        try:
            # التحقق من سعة النشر اليومية للمستخدم (Rate Control)
            user = session.query(User).filter(User.tg_id == user_id).first()
            if not user:
                return False, "المستخدم غير موجود."

            # إذا لم يتم تحديد وقت، يتم النشر فوراً (أو في أقرب وقت متاح)
            if not scheduled_at:
                scheduled_at = datetime.utcnow()

            # تحويل الميتاداتا (للكويزات والاستطلاعات) إلى JSON
            meta_json = json.dumps(metadata) if metadata else None

            new_item = ContentQueue(
                user_id=user_id,
                target_channel_id=channel_id,
                content_type=content_type,
                text_content=text_content,
                file_id=file_id,
                caption=caption,
                metadata_json=meta_json,
                scheduled_at=scheduled_at,
                status="pending"
            )

            session.add(new_item)
            session.commit()
            logger.info(f"Added {content_type} to queue for user {user_id}")
            return True, "تمت إضافة المنشور إلى الطابور بنجاح."
        
        except Exception as e:
            session.rollback()
            logger.error(f"Queue Error: {str(e)}")
            return False, f"خطأ أثناء الإضافة للطابور: {str(e)}"
        finally:
            session.close()

    def get_pending_posts(self):
        """جلب جميع المنشورات التي حان موعد نشرها"""
        session = self.session_factory()
        now = datetime.utcnow()
        try:
            posts = session.query(ContentQueue).filter(
                ContentQueue.status == "pending",
                ContentQueue.scheduled_at <= now
            ).all()
            return posts
        finally:
            session.close()

    def mark_as_posted(self, post_id):
        """تحديث حالة المنشور بعد نشره بنجاح"""
        session = self.session_factory()
        try:
            post = session.query(ContentQueue).get(post_id)
            if post:
                post.status = "posted"
                post.is_posted = True
                
                # تحديث عداد النشر اليومي للمستخدم
                user = session.query(User).filter(User.tg_id == post.user_id).first()
                if user:
                    user.posts_today += 1
                    user.last_post_date = datetime.utcnow()
                
                session.commit()
        except Exception as e:
            session.rollback()
            logger.error(f"Status Update Error: {str(e)}")
        finally:
            session.close()

    def delete_from_queue(self, post_id):
        """حذف منشور من الطابور"""
        session = self.session_factory()
        try:
            post = session.query(ContentQueue).get(post_id)
            if post:
                session.delete(post)
                session.commit()
                return True
            return False
        finally:
            session.close()

# تصدير نسخة جاهزة للاستخدام
queue_manager = QueueService()
      
