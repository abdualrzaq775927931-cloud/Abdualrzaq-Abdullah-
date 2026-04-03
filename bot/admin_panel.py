import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from database.db import get_session, User, Channel
import config

# إعداد السجلات لمراقبة العمليات الإدارية في السيرفر
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def is_owner(user_id: int) -> bool:
    """التحقق من أن المستخدم هو المالك (أنت) بناءً على معرفك في config"""
    return str(user_id) == str(config.OWNER_ID)

# --- 1. لوحة التحكم الرئيسية (UI) ---

async def admin_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """إظهار قائمة الخيارات الإدارية للمالك فقط"""
    user_id = update.effective_user.id
    if not is_owner(user_id):
        return # تجاهل الرسالة إذا لم يكن المالك

    keyboard = [
        [
            InlineKeyboardButton("📊 إحصائيات النظام", callback_data="adm_stats"),
            InlineKeyboardButton("👤 البحث عن مستخدم", callback_data="adm_find")
        ],
        [
            InlineKeyboardButton("📢 إرسال إعلان (Broadcast)", callback_data="adm_bc")
        ],
        [
            InlineKeyboardButton("🔄 تصفير عدادات اليوم", callback_data="adm_reset")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "🛠 **لوحة تحكم المالك - الإدارة الذكية**\n\nمرحباً بك يا أستاذ عبدالرزاق. اختر الإجراء المطلوب من القائمة:",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

# --- 2. معالج الأزرار التفاعلية (Callback Query) ---

async def admin_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """التعامل مع ضغطات الأزرار في لوحة التحكم"""
    query = update.callback_query
    user_id = query.from_user.id

    if not is_owner(user_id):
        await query.answer("🚫 غير مسموح لك بالوصول لهذه البيانات.", show_alert=True)
        return

    await query.answer()
    action = query.data

    if action == "adm_stats":
        session = get_session()
        try:
            u_count = session.query(User).count()
            c_count = session.query(Channel).count()
            active_today = session.query(User).filter(User.posts_today > 0).count()
            
            stats_text = (
                "📈 **تقرير حالة البوت:**\n\n"
                f"👤 إجمالي المشتركين: `{u_count}`\n"
                f"📢 القنوات المربوطة: `{c_count}`\n"
                f"🔥 النشطين اليوم: `{active_today}` مستخدم\n"
            )
            await query.edit_message_text(stats_text, parse_mode='Markdown')
        finally:
            session.close()

    elif action == "adm_bc":
        await query.edit_message_text(
            "✍️ لإرسال رسالة لكل مستخدمي البوت، استخدم الصيغة التالية:\n\n`/broadcast نص الرسالة هنا`",
            parse_mode='Markdown'
        )

# --- 3. الأوامر النصية المباشرة للمالك ---

async def set_limit_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """تعديل حد النشر اليومي لمستخدم: /set_limit [ID] [العدد]"""
    if not is_owner(update.effective_user.id): return

    if len(context.args) < 2:
        await update.message.reply_text("⚠️ الصيغة: `/set_limit [معرف المستخدم] [العدد الجديد]`")
        return

    try:
        t_id, n_limit = int(context.args[0]), int(context.args[1])
        session = get_session()
        user = session.query(User).filter(User.tg_id == t_id).first()
        
        if user:
            user.daily_post_limit = n_limit
            session.commit()
            await update.message.reply_text(f"✅ تم تحديث حد النشر لـ {user.full_name} إلى {n_limit} منشوراً يومياً.")
        else:
            await update.message.reply_text("❌ لم يتم العثور على هذا المعرف في قاعدة البيانات.")
        session.close()
    except Exception as e:
        logger.error(f"Admin Set Limit Error: {e}")
        await update.message.reply_text("❌ حدث خطأ في البيانات المدخلة.")

async def broadcast_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """إرسال رسالة جماعية: /broadcast [النص]"""
    if not is_owner(update.effective_user.id): return

    msg_text = " ".join(context.args)
    if not msg_text:
        await update.message.reply_text("❌ يرجى كتابة نص الرسالة بعد الأمر /broadcast")
        return

    session = get_session()
    users = session.query(User).all()
    session.close()

    success_count = 0
    for u in users:
        try:
            await context.bot.send_message(
                chat_id=u.tg_id, 
                text=f"📢 **تنبيه إداري:**\n\n{msg_text}", 
                parse_mode='Markdown'
            )
            success_count += 1
        except: continue # تخطي المستخدمين الذين حظروا البوت
    
    await update.message.reply_text(f"✅ تم إرسال الإعلان بنجاح إلى {success_count} مستخدم.")
      
