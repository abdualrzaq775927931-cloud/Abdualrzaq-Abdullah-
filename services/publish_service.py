import logging
import json
from telegram import Bot
from telegram.constants import ParseMode
import config

# إعداد السجلات (Logs) لمراقبة عمليات النشر
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class PublishService:
    def __init__(self):
        # إنشاء كائن البوت باستخدام التوكن من ملف الإعدادات
        self.bot = Bot(token=config.BOT_TOKEN)

    async def send_post(self, channel_id, content_type, text_content=None, file_id=None, caption=None, metadata_json=None):
        """
        الوظيفة: إرسال المحتوى إلى القناة بناءً على نوعه.
        يدعم: النصوص، الصور، الفيديوهات، الملفات الصوتية، المستندات، والاختبارات (Quizzes).
        """
        try:
            # 1. إرسال نص فقط (Text Only)
            if content_type == "text":
                await self.bot.send_message(
                    chat_id=channel_id, 
                    text=text_content, 
                    parse_mode=ParseMode.HTML
                )
            
            # 2. إرسال صورة (Photo)
            elif content_type == "photo":
                await self.bot.send_photo(
                    chat_id=channel_id, 
                    photo=file_id, 
                    caption=caption, 
                    parse_mode=ParseMode.HTML
                )
            
            # 3. إرسال فيديو (Video)
            elif content_type == "video":
                await self.bot.send_video(
                    chat_id=channel_id, 
                    video=file_id, 
                    caption=caption, 
                    parse_mode=ParseMode.HTML
                )
            
            # 4. إرسال ملف صوتي (Audio/Voice)
            elif content_type == "audio":
                await self.bot.send_audio(
                    chat_id=channel_id, 
                    audio=file_id, 
                    caption=caption, 
                    parse_mode=ParseMode.HTML
                )
            
            # 5. إرسال مستند أو ملف (Document)
            elif content_type == "document":
                await self.bot.send_document(
                    chat_id=channel_id, 
                    document=file_id, 
                    caption=caption, 
                    parse_mode=ParseMode.HTML
                )

            # 6. إرسال اختبار أو استطلاع (Quiz / Poll)
            elif content_type in ["poll", "quiz"]:
                # تحويل بيانات الـ JSON المخزنة إلى قاموس (Dictionary)
                data = json.loads(metadata_json) if isinstance(metadata_json, str) else metadata_json
                
                if content_type == "quiz":
                    # إرسال كاختبار (يحتوي على إجابة صحيحة)
                    await self.bot.send_poll(
                        chat_id=channel_id,
                        question=data.get("question"),
                        options=data.get("options"),
                        is_anonymous=False,
                        type="quiz",
                        correct_option_id=int(data.get("correct_index", 0)),
                        explanation="الإجابة الصحيحة تم تحديدها بواسطة النظام التعليمي 🎓"
                    )
                else:
                    # إرسال كاستطلاع رأي عادي
                    await self.bot.send_poll(
                        chat_id=channel_id,
                        question=data.get("question"),
                        options=data.get("options"),
                        is_anonymous=False
                    )

            logger.info(f"✅ Successfully published {content_type} to channel {channel_id}")
            return True, None

        except Exception as e:
            error_msg = f"❌ Publishing Error to {channel_id}: {str(e)}"
            logger.error(error_msg)
            return False, error_msg

# تصدير نسخة جاهزة للاستخدام في ملف scheduler_service.py
publisher = PublishService()
                      
