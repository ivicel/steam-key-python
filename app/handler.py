import json
import logging
import struct
import os

from steam import SteamClient
from steam.enums import EResult
from steam.enums.emsg import EMsg
from .result import EPurchaseResultDetail


class SocketHandler(object):

    def __init__(self, ws, serv_name=None):
        self._ws = ws
        self._client = None
        self.serv_name = serv_name or 'Unknown'
        self.username = None
        self.password = None
        self.count = 0
        self._LOG = logging.getLogger("SocketHandler")

    def init(self):
        self._client = SteamClient()
        self._client.once(EMsg.ClientAccountInfo, self.send_account_info)
        # connected
        self.send({
            'action': 'connect',
            'result': 'success',
            'server': self.serv_name
        })

    def __enter__(self):
        self.init()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.disconnect()

    def disconnect(self):
        self._client.logout()
        self._client.disconnect()

    def send(self, msg):
        try:
            self._ws.send(json.dumps(msg))
        except Exception as err:
            self._LOG.error('Send message error: %s(%s)', err, msg)

    def handle_logon(self, msg):
        self._client.disconnect()
        result = self._client.login(username=self.username,
                                    password=self.password,
                                    two_factor_code=msg['authcode'],
                                    login_id=self.id)

        if result in (EResult.InvalidLoginAuthCode,
                      EResult.AccountLoginDeniedNeedTwoFactor,
                      EResult.TwoFactorCodeMismatch):
            # authcode required
            self.send({
                'action': 'authCode'
            })
        elif result == EResult.OK:
            # login success
            self._LOG.debug('Login steam success with %s' % repr(self.username))
            del self.password
        else:
            self.send({
                'action': 'logOn',
                'result': 'failed',
                'message': result.name
            })

    def handle_authcode(self, msg):
        self.handle_logon({
            'username': self.username,
            'password': self.password,
            'authcode': msg.get('authCode', '')
        })

    def handle_ping(self, msg):
        self.count += 1
        if self.count > 20:
            self._ws.close()
            self.disconnect()
        else:
            self.send({
                'action': 'pong',
                'count': self.count
            })

    def handle_redeem(self, msg):
        keys = msg.get('keys')
        if keys is None:
            return

        for key in keys:
            result, presult, detail = self._client.register_product_key(key)
            self.send({
                'action': 'redeem',
                'detail': {
                    'key': key,
                    'result': result.name,
                    'detail': EPurchaseResultDetail(presult).name,
                    'packages': detail.get('PackageID', -1)
                }
            })

    def send_account_info(self, msg):
        self.send({
            'action': 'logOn',
            'result': 'success',
            'detail': {
                'name': msg.body.persona_name,
                'country': msg.body.ip_country
            }
        })

    @property
    def id(self):
        return struct.unpack_from('<L', os.urandom(4))[0]

    def run(self):
        while not self._ws.closed:
            try:
                message = self._ws.receive()
                message = json.loads(message)
            except (json.JSONDecodeError, TypeError) as err:
                self._LOG.error('Got error message: %s, %s', message, err)
                break

            self._LOG.debug('receive message: %s', message)
            action = message.get('action', None)
            if action == 'ping':
                self.handle_ping(message)
            elif action == 'logOn':
                self.username = message.get('username')
                self.password = message.get('password')
                if not self.username or not self.password:
                    self.send({
                        'action': 'logOn',
                        'result': 'failed',
                        'message': 'login error'
                    })
                else:
                    self.handle_logon(message)
            elif action == 'authCode':
                self.handle_authcode(message)
            elif action == 'redeem':
                self.handle_redeem(message)
