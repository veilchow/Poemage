from flask import Blueprint

ljson = Blueprint('ljson', __name__)

# 执行蓝图的模块文件，确保视图被识别
import app.ljson.main
