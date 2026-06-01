from app.models.base import Base
from app.libs.extensions import db
from datetime import datetime


class Behavior(Base):
    """
    行为模型类
    """
    __tablename__ = 'behavior'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, unique=True)  # 外键关联到用户表，且唯一
    behaviorFile = db.Column(db.JSON, nullable=False)  # 使用 JSON 类型存储行为数据
    created_at = db.Column(db.DateTime, default=datetime.utcnow)  # 创建时间


    # 定义与用户表的关系
    user = db.relationship('User', backref=db.backref('behavior', uselist=False))  # 一对一关系