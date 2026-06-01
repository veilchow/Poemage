from app.models.base import Base
from app.libs.extensions import db
from datetime import datetime

class LearnData(Base):
    """
    学习数据模型类（存储用户学习诗歌的情况）
    """
    __tablename__ = 'learndata'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, unique=True)  # 外键关联到用户表，且唯一
    poem_data = db.Column(db.JSON, nullable=False, comment="存储用户学习诗歌的情况")  # 使用 JSON 类型存储不定长的数组，单个元素也是 JSON 类型
    created_at = db.Column(db.DateTime, default=datetime.utcnow)  # 创建时间

    # 定义与用户表的关系
    user = db.relationship('User', backref=db.backref('learndata', uselist=False))  # 一对一关系