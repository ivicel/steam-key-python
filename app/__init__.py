import os
from base64 import b64encode

from flask import Flask
from .websocket import WebSocket


sock = WebSocket()


def create_app():
    app = Flask(__name__)
    if not hasattr(app.config, 'SECRET_KEY'):
        app.config['SECRET_KEY'] = rand_str()

    sock.init_app(app)
    from .views import main
    app.register_blueprint(main)

    return app


def rand_str():
    return b64encode(os.urandom(32))
