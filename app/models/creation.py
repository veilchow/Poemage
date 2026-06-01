from app.models.base import Base
from app.libs.extensions import db
from datetime import datetime


class Creation(Base):
    """
    创作模型类
    """
    __tablename__ = 'creation'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    poem_id = db.Column(db.Integer, db.ForeignKey('poem.id'), nullable=False)
    content = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    creation_info = db.Column(db.Text)
