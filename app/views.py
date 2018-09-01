from flask import Blueprint, render_template, current_app
from .handler import SocketHandler
from . import sock


main = Blueprint('main', __name__)


@main.route('/')
def index():
    return render_template('index.html')


@sock.route('/ws')
def sockets(ws):
    with SocketHandler(ws, current_app.config.get('name')) as handler:
        handler.run()
