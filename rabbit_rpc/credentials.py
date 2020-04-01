# -*- coding: utf-8 -*
import hmac
import base64
import time
import hashlib


class AliyunCredentialsProvider:
    """
    根据阿里云的 accessKey, accessSecret, UID算出 amqp 连接使用的 username 和
    password。 UID是资源ownerID，一般是接入点第一段
    """
    ACCESS_FROM_USER = 0

    def __init__(self, access_key, access_secret, uid):
        self.accessKey = access_key
        self.accessSecret = access_secret
        self.UID = uid

    def get_username(self):
        t = '%i:%s:%s' % (self.ACCESS_FROM_USER, self.UID, self.accessKey)
        return base64.b64encode(t.encode('utf-8'))

    def get_password(self):
        ts = str(int(round(time.time() * 1000)))
        h = hmac.new(
            ts.encode('utf-8'), self.accessSecret.encode('utf-8'), hashlib.sha1)
        sig = h.hexdigest().upper()
        sig_str = "%s:%s" % (sig, ts)
        return base64.b64encode(sig_str.encode('utf-8'))
