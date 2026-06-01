# app/models/base.py
from app.libs.extensions import db


class Base(db.Model):
    """
    数据表模型基类
    """
    __abstract__ = True

    def set_attr(self, attrs_dict):
        """
        将表单字段传递给数据表模型对应字段
        """
        for key, value in attrs_dict.items():
            if key != "id" and hasattr(self, key):
                if value:
                    setattr(self, key, value)
