from sqlalchemy import create_engine, Column, Integer, String, BigInteger, Boolean, DateTime, ForeignKey, Text, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime
import config

Base = declarative_base()
engine = create_engine(config.DATABASE_URL)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)

class User(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True)
    tg_id = Column(BigInteger, unique=True, nullable=False)
    username = Column(String)
    full_name = Column(String)
    
    # الصلاحيات والحالة
    is_admin = Column(Boolean, default=False)
    is_banned = Column(Boolean, default=False)
    is_subscribed = Column(Boolean, default=False) # للاشتراك الإجباري
    
    # قيود النشر (Rate Control)
    daily_post_limit = Column(Integer, default=10) # عدد المنشورات المسموحة يومياً
    posts_today = Column(Integer, default=0)       # عداد المنشورات لليوم الحالي
    last_post_date = Column(DateTime, default=datetime.utcnow)
    
    joined_at = Column(DateTime, default=datetime.utcnow)
    
    channels = relationship("Channel", back_populates="owner", cascade="all, delete-orphan")
    queue_items = relationship("ContentQueue", back_populates="user")

class Channel(Base):
    __tablename__ = 'channels'
    id = Column(Integer, primary_key=True)
    channel_id = Column(BigInteger, unique=True, nullable=False)
    title = Column(String)
    owner_id = Column(BigInteger, ForeignKey('users.tg_id'))
    
    owner = relationship("User", back_populates="channels")

class ContentQueue(Base):
    __tablename__ = 'queue'
    id = Column(Integer, primary_key=True)
    user_id = Column(BigInteger, ForeignKey('users.tg_id'))
    target_channel_id = Column(BigInteger) # القناة المستهدفة للنشر
    
    # أنواع المحتوى
    content_type = Column(String) # text, photo, video, audio, document, poll, quiz
    text_content = Column(Text)
    file_id = Column(String)      # لمعرفات الملفات في تليجرام
    caption = Column(Text)        # الوصف المرافق للملفات
    
    # البيانات المتقدمة (Polls/Quizzes)
    # نستخدم JSON لتخزين خيارات التصويت أو الأسئلة بشكل مرن
    metadata_json = Column(JSON) 
    
    # الجدولة والحالة
    scheduled_at = Column(DateTime, nullable=False)
    priority = Column(Integer, default=0) # نظام الأولوية (Priority Queue)
    status = Column(String, default="pending") # pending, posted, failed
    
    created_at = Column(DateTime, default=datetime.utcnow)
    user = relationship("User", back_populates="queue_items")

# --- دوال الإدارة المباشرة (Helper Functions) ---

def init_db():
    Base.metadata.create_all(engine)

def get_session():
    return SessionLocal()

# دالة سريعة للتحقق من المالك أو إضافة مستخدم جديد
def get_or_create_user(tg_id, username=None, full_name=None):
    session = get_session()
    user = session.query(User).filter(User.tg_id == tg_id).first()
    if not user:
        # إذا كان هو المالك المحدد في config
        is_admin = (tg_id == config.OWNER_ID)
        user = User(tg_id=tg_id, username=username, full_name=full_name, is_admin=is_admin)
        session.add(user)
        session.commit()
    session.close()
    return user
    
