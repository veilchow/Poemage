# 引入 Flask 核心依赖 werkzeug 的 security 模块，专门处理密码的储存和校验
from werkzeug.security import generate_password_hash, check_password_hash
from app.models.base import Base
from app.libs.extensions import db
# 引入 UserMixin 基类
from flask_login import UserMixin
from datetime import datetime


# 让 Admin 模型继承 UserMixin
class User(Base, UserMixin):
    """
    用户模型类
    """
    __tablename__ = 'user'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    _password = db.Column(db.String(256), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    user_info = db.Column(db.Text)

    creations = db.relationship('Creation', backref='author', lazy='dynamic')

    # 处理密码相关的查询、储存、校验工作
    @property
    def password(self):
        return self._password

    @password.setter
    def password(self, row):
        self._password = generate_password_hash(row)

    def check_password(self, row):
        return check_password_hash(self._password, row)
