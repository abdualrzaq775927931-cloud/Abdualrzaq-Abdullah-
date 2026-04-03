from sqlalchemy import Column, Integer, BigInteger, String, DateTime, ForeignKey, Text, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime

Base = declarative_base()

class User(Base):
    """جدول المستخدمين لتخزين بيانات المعلمين وصلاحياتهم"""
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True)
    tg_id = Column(BigInteger, unique=True, nullable=False) # معرف التليجرام
    username = Column(String(100), nullable=True)
    full_name = Column(String(200), nullable=True)
    
    # قيود النشر اليومية (لحماية موارد الـ AI والضغط)
    daily_post_limit = Column(Integer, default=10) # الحد الافتراضي 10 منشورات
    posts_today = Column(Integer, default=0) # عداد المنشورات الحالية
    last_post_date = Column(DateTime, default=datetime.utcnow)
    
    is_admin = Column(Boolean, default=False) # هل هو مدير للبوت؟
    
    # علاقة مع القنوات التي يملكها المستخدم
    channels = relationship("Channel", back_populates="owner")

class Channel(Base):
    """جدول القنوات والمجموعات المربوطة بالبوت"""
    __tablename__ = 'channels'

    id = Column(Integer, primary_key=True)
    channel_id = Column(BigInteger, unique=True, nullable=False) # المعرف الذي يبدأ بـ -100
    title = Column(String(255), nullable=False)
    
    owner_id = Column(BigInteger, ForeignKey('users.tg_id'))
    owner = relationship("User", back_populates="channels")

class Post(Base):
    """جدول الطابور (Queue) للمنشورات والاختبارات المجدولة"""
    __tablename__ = 'posts'

    id = Column(Integer, primary_key=True)
    user_id = Column(BigInteger, ForeignKey('users.tg_id'))
    target_channel_id = Column(BigInteger, nullable=False)
    
    # نوع المحتوى: text, photo, video, quiz, audio, document
    content_type = Column(String(50), nullable=False)
    
    text_content = Column(Text, nullable=True) # للنصوص
    file_id = Column(String(255), nullable=True) # لمعرفات الوسائط في تليجرام
    caption = Column(Text, nullable=True) # وصف الوسائط
    
    # بيانات إضافية (مثل خيارات الكويز بصيغة JSON)
    metadata_json = Column(Text, nullable=True)
    
    # حالة المنشور: pending (منتظر), posted (تم النشر), failed (فشل)
    status = Column(String(20), default="pending")
    
    scheduled_at = Column(DateTime, nullable=False) # وقت النشر المطلوب
    created_at = Column(DateTime, default=datetime.utcnow)
  
