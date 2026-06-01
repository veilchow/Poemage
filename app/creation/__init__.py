from flask import Blueprint

creation = Blueprint('creation', __name__)

# 执行蓝图的模块文件，确保视图被识别
import app.creation.main
