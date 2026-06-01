from app.models.base import Base
from app.libs.extensions import db
from datetime import datetime

class Economic(Base):
    """
    经济模型类（存储用户的金币值）
    """
    __tablename__ = 'economic'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, unique=True)  # 外键关联到用户表，且唯一
    coin_value = db.Column(db.BigInteger, nullable=False, comment="用户的金币值")  # 使用 BigInteger 类型存储金币值
    created_at = db.Column(db.DateTime, default=datetime.utcnow)  # 创建时间

    # 定义与用户表的关系
    user = db.relationship('User', backref=db.backref('economic', uselist=False))  # 一对一关系