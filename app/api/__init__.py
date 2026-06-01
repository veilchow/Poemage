from flask import Blueprint

api = Blueprint('api', __name__)

# 执行蓝图的模块文件，确保视图被识别
import app.api.main
