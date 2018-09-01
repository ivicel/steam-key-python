from gevent import monkey
monkey.patch_all(ssl=False)
import os
import json

from app import create_app


CONFIG_FILE = os.path.join(os.path.dirname(__file__), 'config.json')

obj = dict()
if os.path.exists(CONFIG_FILE):
    with open(CONFIG_FILE) as fp:
        obj = json.loads(fp.read())

app = create_app(obj)

if __name__ == '__main__':
    from gevent import pywsgi
    from geventwebsocket.handler import WebSocketHandler
    server = pywsgi.WSGIServer(('', 5000), app, handler_class=WebSocketHandler)
    server.serve_forever()
