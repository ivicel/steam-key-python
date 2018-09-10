"""This is a simple implement wrapper websocket from
    https://github.com/zeekay/flask-uwsgi-websocket/
"""
import logging

import uwsgi
import gevent
from gevent.queue import Empty, Queue
from gevent.event import Event
from gevent.select import select as gselect
from gevent.monkey import patch_all
from werkzeug.routing import Map, Rule
from werkzeug.exceptions import HTTPException


LOGGER = logging.getLogger("WebSocket")


class WebSocketMiddleware(object):
    def __init__(self, wsgi_app, websocket):
        self.wsgi_app = wsgi_app
        self.ws = websocket

    def __call__(self, environ, start_response):
        adapter = self.ws.url_map.bind_to_environ(environ)
        try:
            endpoint, args = adapter.match()
            handler = self.ws.view_functions[endpoint]
        except HTTPException:
            handler = None

        if handler is None or 'HTTP_SEC_WEBSOCKET_KEY' not in environ:
            return self.wsgi_app(environ, start_response)

        uwsgi.websocket_handshake(environ['HTTP_SEC_WEBSOCKET_KEY'], environ.get('HTTP_ORIGIN', ''))

        send_event = Event()
        send_queue = Queue()

        recv_event = Event()
        recv_queue = Queue()

        client = WebSocketWrapper(environ, uwsgi.connection_fd(), send_event,
                                  send_queue, recv_event, recv_queue, self.ws.timeout)

        handler = gevent.spawn(handler, client, *args)

        def listener(client):
            gselect([client.fd], [], [])
            recv_event.set()

        listening = gevent.spawn(listener, client)

        while True:
            if client.closed:
                recv_queue.put(None)
                listening.kill()
                handler.join(client.timeout)
                return ''

            gevent.wait([handler, send_event, recv_event], None, 1)

            if send_event.is_set():
                try:
                    while True:
                        msg = send_queue.get_nowait()
                        LOGGER.debug('Send event: %r' % msg)
                        uwsgi.websocket_send(msg)
                except gevent.queue.Empty:
                    send_event.clear()
                except IOError:
                    client.closed = True
            elif recv_event.is_set():
                recv_event.clear()
                try:
                    message = uwsgi.websocket_recv_nb()
                    while message:
                        LOGGER.debug('<- Recv event: %r' % message)
                        recv_queue.put(message)
                        message = uwsgi.websocket_recv_nb()
                    listening = gevent.spawn(listener, client)
                except IOError:
                    client.closed = True

            elif handler.ready():
                listening.kill()
                return ''


class WebSocket(object):
    def __init__(self, app=None, timeout=120):
        # websocket connection timeout
        self.timeout = timeout
        self.url_map = Map()
        self.view_functions = {}
        if app:
            self.init_app(app)

    def init_app(self, app):
        patch_all()
        self.app = app
        app.wsgi_app = WebSocketMiddleware(app.wsgi_app, self)
        if uwsgi.opt.get('DEBUG', False):
            from werkzeug.debug import DebuggedApplication
            app.debug = True
            app.wsgi_app = DebuggedApplication(app.wsgi_app, True)

    def add_url_map(self, url, endpoint=None, view_func=None, **options):
        if endpoint is None:
            endpoint = view_func.__name__
        options['endpoint'] = endpoint
        methods = options.get('methods', None)
        if methods is not None and set(methods) != {'GET'}:
            raise AssertionError('Only GET support!!!')
        methods = ('GET',)
        rule = Rule(url, methods=methods, **options)
        self.url_map.add(rule)
        if view_func is not None:
            old_func = self.view_functions.get(endpoint, None)
            if old_func is not None and view_func != old_func:
                raise AssertionError('View function mapping is overwriting an '
                                     'existing endpoint function: %s' % endpoint)
            self.view_functions[endpoint] = view_func

    def route(self, rule, **options):
        def decorator(f):
            endpoint = options.get('endpoint', None)
            self.add_url_map(rule, endpoint, f, **options)
            return f
        return decorator


class WebSocketWrapper(object):
    def __init__(self, environ, fd, send_event, send_queue, recv_event, recv_queue, timeout):
        self.environ = environ
        self.fd = fd
        self.timeout = timeout
        self.send_event = send_event
        self.send_queue = send_queue
        self.recv_event = recv_event
        self.recv_queue = recv_queue
        self.closed = False

    def send(self, msg, binary=False):
        if binary:
            return self.send_binary(msg)
        self.send_queue.put(msg)
        self.send_event.set()

    def send_binary(self, msg):
        self.send_queue.put(msg)
        self.send_event.set()

    def recv(self):
        return self.recv_queue.get()

    def receive(self):
        return self.recv()

    def close(self):
        self.closed = True
