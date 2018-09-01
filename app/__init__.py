import os
from base64 import b64encode

from flask import Flask
from flask_sockets import Sockets


sock = Sockets()


def create_app(obj):
    app = Flask(__name__)
    for k, v in obj.items():
        app.config[k] = v
    if not hasattr(app.config, 'SECRET_KEY'):
        app.config['SECRET_KEY'] = rand_str()

    sock.init_app(app)
    from .views import main
    app.register_blueprint(main)

    return app


def rand_str():
    return b64encode(os.urandom(32))