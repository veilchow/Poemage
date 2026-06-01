import click
from flask import Flask
from flask_cors import CORS

# 引入配置字典
from app.configs import configs

from app.libs.extensions import db, migrate, get_login_manager


# 工厂函数
def create_app(config="development"):
    """
    工厂函数
    """
    app = Flask(__name__)
    # 环境配置
    app.config.from_object(configs[config])
    # 注册扩展
    register_extensions(app)
    # 注册蓝图
    register_blueprints(app)
    # 调用注册命令函数
    register_cli(app)
    return app


def register_extensions(app):
    """
    注册第三方插件
    """
    # API 允许游戏前端携带登录 cookie 跨端口访问。
    CORS(
        app,
        supports_credentials=True,
        resources={
            r"/api/*": {
                "origins": [
                    "https://your-domain.example",
                    "https://your-domain.example",
                    "http://127.0.0.1:5001",
                    "http://localhost:5001",
                ]
            }
        },
    )
    db.init_app(app)
    migrate.init_app(app, db)
    # 获取 login_manager 并调用 init_app 方法将其注册到 Flask 核心对象上
    login_manager = get_login_manager()
    login_manager.init_app(app)


def register_blueprints(app):
    """
    注册蓝图
    """
    # 因为我们只会在这里用到 `view` 蓝图实例，所以就再函数内部引用它
    # from app.admin import admin
    from app.auth import auth
    from app.creation import creation
    from app.poem import poem
    from app.user import user
    from app.texture import texture
    from app.mission import mission
    from app.save import save
    from app.aiapi import aiapi
    from app.ljson import ljson
    from app.behavior import behavior
    from app.economic import economic
    from app.learndata import learndata
    from app.classroom import classroom


    # 注册蓝图
    app.register_blueprint(auth, url_prefix="/api")
    app.register_blueprint(creation, url_prefix="/api")
    app.register_blueprint(poem, url_prefix="/api")
    app.register_blueprint(user, url_prefix="/api")
    app.register_blueprint(texture, url_prefix="/api")
    app.register_blueprint(mission, url_prefix="/api")
    app.register_blueprint(save, url_prefix="/api")
    app.register_blueprint(aiapi, url_prefix="/api")
    app.register_blueprint(ljson, url_prefix="/api")
    app.register_blueprint(behavior, url_prefix="/api")
    app.register_blueprint(economic, url_prefix="/api")
    app.register_blueprint(learndata, url_prefix="/api")
    app.register_blueprint(classroom, url_prefix="/api")


def register_cli(app: Flask):
    """
    注册命令行命令
    """

    @app.cli.command()
    @click.option('--drop', is_flag=True, help='删除数据表并重建')
    # --_init 参数是为了再内部初始化数据库时不再二次确认用的
    @click.option('--_init', is_flag=True, help='删除并重建数据表 (内部调用)')
    def initdb(drop, _init):
        """初始化数据库"""
        if drop:
            click.confirm('确定要删除所有数据表?', abort=True)
            db.drop_all()
            click.echo('数据表删除成功')

        # 如果传递的是 --_init 参数，那么会直接删除数据库
        if _init:
            db.drop_all()
            click.echo('数据表删除成功')

        db.create_all()
        click.echo('数据表已成功创建')
