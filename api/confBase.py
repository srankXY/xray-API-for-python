# -*- utf:8 -*-

class CONFIG(object):

    LOG = {
        # 是否打印屏幕日志
        'screenLOG': True,
        'logFile': 'proxyApi.log'
    }

    proxyAppDir = {
        # 必须以/结尾
        'v2ray': '/soft/proxy/v2ray/'
    }

    v2ray = '''
    {
        "log": {
            "access": "/soft/proxy/v2ray/access.log",
            "loglevel": "info"
        },
        "inbounds": [
            {
                "port": 1080,
                "listen": "127.0.0.1",
                "protocol": "http",
                "settings": {
                    "udp": true
                }
            }
        ],
        "outbounds": [
        {
          "tag": "direct",
          "protocol": "freedom"
        }],
        "routing": {
            "domainStrategy": "IPOnDemand",
            "domainMatcher": "mph",
            "rules": [
                {
                    "type": "field",
                    "ip": ["geoip:private"],
                    "outboundTag": "direct"
                },
                {
                    "type": "field",
                    "ip": [
                        "geoip:!cn"
                    ],
                    "outboundTag": "proxy"
                }
            ]
        }
    }'''

    clash = None