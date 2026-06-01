from app.models.base import Base
from app.libs.extensions import db
from datetime import datetime


# class Texture(Base):
#     """
#     图片纹理类
#     """
#     __tablename__ = 'texture'
#
#     id = db.Column(db.Integer, primary_key=True)
#     creation_id = db.Column(db.Integer, db.ForeignKey('creation.id'), primary_key=True)
#     sub_id = db.Column(db.Integer, primary_key=True)
#     base64_code = db.Column(db.Text, nullable=False)
#     texture_info = db.Column(db.String(255))
#     created_at = db.Column(db.DateTime, default=datetime.utcnow)
#
#     # 关系定义
#     creations = db.relationship('Creation', backref=db.backref('texture', lazy='dynamic'))
#
#
# def to_dict(self):
#     return {
#         'creation_id': self.creation_id,
#         'sub_id': self.sub_id,
#         'base64_code': self.base64_code,
#         'texture_info': self.texture_info,
#         'created_at': self.created_at.isoformat()
#     }
