from app.models.base import Base
from app.libs.extensions import db
from datetime import datetime


class Ljson(Base):
    """
    json模型类
    """
    __tablename__ = 'ljson'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, unique=True)  # 外键关联到用户表，且唯一
    jsonFile = db.Column(db.JSON, nullable=False)  # 使用 JSON 类型存储文件
    created_at = db.Column(db.DateTime, default=datetime.utcnow)  # 创建时间


    # 定义与用户表的关系
    user = db.relationship('User', backref=db.backref('ljson', uselist=False))  # 一对一关系
