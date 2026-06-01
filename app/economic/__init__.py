from flask import Blueprint

economic = Blueprint('economic', __name__)

# 执行蓝图的模块文件，确保视图被识别
import app.economic.main
