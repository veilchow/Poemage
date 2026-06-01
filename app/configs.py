import os
from datetime import timedelta

try:
    from app.local_config import DATABASE, HOST, PASSWORD, PORT, SECRET_KEY, USERNAME
except ImportError:
    SECRET_KEY = os.getenv("SECRET_KEY", "change-me")
    USERNAME = os.getenv("MYSQL_USER", "root")
    PASSWORD = os.getenv("MYSQL_PASSWORD", "")
    HOST = os.getenv("MYSQL_HOST", "127.0.0.1")
    PORT = os.getenv("MYSQL_PORT", "3306")
    DATABASE = os.getenv("MYSQL_DATABASE", "flaskserver")


class BaseConfig:
    """
    配置基类，公用配置写在这里
    """
    # 设置用户勾选了 “记住我” 之后登陆状态保留 7 天
    REMEMBER_COOKIE_DURATION = timedelta(days=30)
    # 设置默认的 session cookie 过期时间，就让它 1 天过期吧
    PERMANENT_SESSION_LIFETIME = timedelta(days=1)
    SECRET_KEY = SECRET_KEY
    DIALECT = 'mysql'
    DRIVER = 'pymysql'

    # 用户名，密码
    USERNAME = USERNAME
    PASSWORD = PASSWORD

    # ip， 端口
    HOST = HOST
    PORT = PORT

    # 连接的数据库
    DATABASE = DATABASE

    SQLALCHEMY_DATABASE_URI = "{}+{}://{}:{}@{}:{}/{}?charset=utf8".format(DIALECT, DRIVER, USERNAME, PASSWORD, HOST,
                                                                           PORT,
                                                                           DATABASE)
    SQLALCHEMY_COMMIT_ON_TEARDOWN = True
    SQLALCHEMY_TRACK_MODIFICATIONS = True

    SQLALCHEMY_POOL_SIZE = 10
    SQLALCHEMY_MAX_OVERFLOW = 5


class DevelopmentConfig(BaseConfig):
    """
    开发环境配置类
    """
    # 设置缓存时间为 1 秒，这样就不存在需要我们手动清空缓存的问题了
    SEND_FILE_MAX_AGE_DEFAULT = timedelta(seconds=1)
    pass


class TestConfig(BaseConfig):
    """
    测试环境配置类
    """
    pass


class ProductionConfig(BaseConfig):
    """
    生产环境配置类
    """
    pass


# 配置类字典，根据传递的 key 选择不同的配置类
configs = {
    "development": DevelopmentConfig,
    "test": TestConfig,
    "production": ProductionConfig
}
