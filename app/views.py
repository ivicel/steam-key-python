import uwsgi
import logging
from flask import Blueprint, render_template, current_app
from .handler import SocketHandler
from . import sock


# show steamclient and websocket message in debug
if uwsgi.opt.get('DEBUG', b'') not in (b'0', b'false', b'no'):
    logging.basicConfig(format="[%(levelname)s] %(asctime)s:%(name)s - %(funcName)s: %(message)s",
                        level=logging.DEBUG)

main = Blueprint('main', __name__)


@main.route('/')
def index():
    return render_template('index.html')


@sock.route('/ws')
def sockets(ws):
    server_name = uwsgi.opt.get('SERVER_NAME', b'')
    with SocketHandler(ws, server_name.decode()) as handler:
        handler.run()
