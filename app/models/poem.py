from app.models.base import Base
from app.libs.extensions import db
from datetime import datetime


class Poem(Base):
    """
    诗歌模型类
    """
    __tablename__ = 'poem'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    content = db.Column(db.Text, nullable=False)
    poem_info = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    creations = db.relationship('Creation', backref='poem', lazy='dynamic')
