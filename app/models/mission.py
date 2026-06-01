from app.models.base import Base
from app.libs.extensions import db
from datetime import datetime


class Mission(Base):
    """
    Mission（关卡）模型类
    """
    __tablename__ = 'mission'

    id = db.Column(db.Integer, primary_key=True)
    curMissionIndex = db.Column(db.Integer, nullable=False, unique=True)  # curMissionIndex用于唯一标识关卡
    isBefore = db.Column(db.Boolean, nullable=False)
    charaPosition = db.Column(db.String(100), nullable=False)  # 存储Vec3为字符串，格式化时转化为cc.Vec3
    direction = db.Column(db.Boolean, nullable=False)
    missionPassedTag = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

