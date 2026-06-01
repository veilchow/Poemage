from app.models.base import Base
from app.libs.extensions import db
from datetime import datetime


class Save(Base):
    """
    存档模型类
    """
    __tablename__ = 'save'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, unique=True)  # 外键关联到用户表，且唯一
    curMissionIndex = db.Column(db.Integer, nullable=False)  # 当前关卡索引
    isBefore = db.Column(db.Boolean, nullable=False)  # 当前状态是否为之前
    charaPosition = db.Column(db.JSON, nullable=False)  # 使用 JSON 类型存储 Vec3
    direction = db.Column(db.Boolean, nullable=False)  # 方向
    poemFinishStatus = db.Column(db.JSON, nullable=False)  # 使用 JSON 类型存储数组
    created_at = db.Column(db.DateTime, default=datetime.utcnow)  # 创建时间

    # 新增字段
    curPoetId = db.Column(db.String(100), nullable=False)  # 字符类型，不可为空
    poetFinishStatus = db.Column(db.JSON, nullable=False)  # JSON 数组，不可为空

    # 定义与用户表的关系
    user = db.relationship('User', backref=db.backref('save', uselist=False))  # 一对一关系
