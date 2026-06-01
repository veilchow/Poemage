from app.api import api


# 测试路由
@api.route('/', methods=['POST', 'GET'])
def helloword():
    return 'Hello World!'
