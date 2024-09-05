# -*- utf-8 -*-

import os.path
import confBase
import flask
import json
import base64
import datetime
import functools
import time
import subprocess
import socket
from flask_cors import CORS
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import urlparse, parse_qs
from urllib import request
import ssl


# Flask API
api = flask.Flask(__name__)
api.json.ensure_ascii = False
CORS(api)


# 日志
def LOG(msg: str, prefix: str = '[ General ]'):
    """
    :param prefix:   前缀标识
    :param msg:     具体信息
    :return:
    """

    if confBase.CONFIG.LOG.get('screenLOG'):
        # 控制台打印
        print(time.strftime('%Y-%m-%d %H:%M', time.localtime(time.time())), prefix, msg)

    with open(confBase.CONFIG.LOG.get('logFile'), "a") as f:
        # 写入日志文件
        print(time.strftime('%Y-%m-%d %H:%M', time.localtime(time.time())), prefix, msg, file=f)


# 通用异常处理，装饰器
def generalTryCatch(func):
    """
    通用异常装饰器
    :param func:    传入具体的函数名称以装饰该函数
    :return:
    """

    # 保留被装饰函数原始元数据
    @functools.wraps(func)
    # 装饰函数
    def wrapper(*args, **kwargs):

        # 异常捕获
        try:
            # 执行实际函数
            return func(*args, **kwargs)
        # 实际函数通用出错处理
        except Exception as e:
            # 调试打印
            print("函数%s, 出现异常： %s" % (func.__name__, e))
            # 异常返回
            return response(code=8500, result={
                'type': "错误",
                "data": {
                    'msg': "API调用失败，请联系管理员或者核实您的订阅地址是否能正常获取"
                }
            })
    # 返回装饰函数
    return wrapper


# 返回框架
def response(code=8200, **kwargs):
    """
    :param code:    响应状态码
    :param kwargs:  返回的具体数据，示例：{'type': '盘中k线','symbol': 'LEE','data': result}，result为具体的k线数据
    :return:
    """

    data = {
        'code': code,
        'timestamp': datetime.datetime.now().timestamp()
    }

    # 根据传参重组返回数据
    for k, v in kwargs['result'].items():
        data[k] = v

    return data


def excuteCMD(cmd: str):
    """
    系统命令执行
    :param cmd:     需要执行的系统命令
    :return:
    """

    try:
        # 执行Linux命令
        result = subprocess.check_output(cmd, shell=True)

        return {
            "msg": "系统命令调用成功",
            "osResult": json.loads(result.decode())
        }
    except Exception as e:
        LOG(prefix="[ OS ]", msg="命令执行失败！错误信息为：%s" % str(e))
        return False


def saveConf(data: str, fileName: str):
    """
    文件下载
    :param data:        配置文件数据
    :param fileName:    保存的文件名
    :return:
    """

    try:
        with open(fileName, 'w') as f:
            f.write(data)
            return True
    except:
        return False


def parserSub(proxyApp: str, nodeList: list):
    """
    根据代理软件类型，订阅数据生成对应的节点配置文件
    :param nodeList:     订阅节点数据
    :param proxyApp:    传入的代理软件类型
    :return:
    """

    if proxyApp == 'v2ray':
        logPrefix = '[ %s ]' % proxyApp
        # 组装outbounds列表，订阅节点列表
        outBounds = []

        try:
            # 循环添加节点
            for id, node in enumerate(nodeList):
                nodeInfo = {
                    "id": id,
                    "nickName": node.get('ps'),
                    "protocol": node.get('protocol'),
                    "tag": "proxy",
                    "settings": {
                        "vnext": [{
                            "address": node.get('add').replace('/', ''),
                            "port": int(node.get('port')),
                            "users": [{
                                "id": node.get('id'),
                                "alterId": node.get('aid'),
                                "security": "auto",
                                "flow": node.get('flow'),
                                "encryption": "none",
                                "level": 0
                            }]
                        }]
                    },
                    "streamSettings": {
                        "network": node.get('net'),
                        "security": node.get('tls') if node.get('tls') != "" else None,
                        "tlsSettings": {
                            "allowInsecure": True,
                            "serverName": None
                        },
                        "tcpSettings": None,
                    }
                }
                # 其他配置
                if node.get('net') == "ws":
                    nodeInfo["streamSettings"]["wsSettings"] = {
                        "path": node.get('path'),
                        "connectionReuse": True,
                        "headers": {
                            "Host": None if node.get('host') == "" else node.get('host'),
                        },
                    }
                outBounds.append(nodeInfo)
        # 解析异常
        except Exception as e:
            LOG(prefix=logPrefix, msg=str(e))
            return False

        # 写入订阅配置文件
        if saveConf(data=json.dumps(outBounds), fileName='%s%s.sub' % (confBase.CONFIG.proxyAppDir.get(proxyApp), proxyApp)):
            return outBounds
        else:
            return False


def getSubcribe(url: str):
    """
    更新订阅地址
    :param url:         订阅地址
    :return:
    """

    # base64 判断函数
    def decodeB64(str: str):
        """
        :param str:     需要判断的字符串
        :return:
        """

        # 解决b64编码长度不正确的情况
        if len(str) % 4 != 0:
            missCount = 4 - len(str) % 4
            for i in range(missCount):
                str += '='

        try:
            result = base64.b64decode(str)
            return result
        except ValueError:
            return False

    def v2ray(subData: bytes):
        """
        v2ray 订阅格式化json
        :param subData:    b64解码后的二进制数据
        :return:
        """

        for i in subData.decode('utf-8').strip().split('\n'):

            # 处理无法正常解析的情况
            try:
                rawSubNode = i.split('://')
                subNode = {}
                if rawSubNode[0] == 'vless':
                    url_parsed = urlparse(rawSubNode[1])
                    query_params = parse_qs(url_parsed.query)
                    subNode = {
                        "add": url_parsed.path.split('@')[1].split(':')[0],
                        "host": None,
                        "id": url_parsed.path.split('@')[0],
                        "net": query_params.get('type')[0],
                        "path": None,
                        "port": url_parsed.path.split(':')[1],
                        "ps": url_parsed.fragment,
                        "tls": query_params.get('security')[0],
                        "alpn": query_params.get('alpn')[0],
                        "flow": query_params.get('flow')[0],
                        "aid": None,
                        "type": query_params.get('type')[0],
                        # "query_params": query_params
                    }
                elif rawSubNode[0] == 'vmess':
                    # 对数据进行b64解码
                    subNode = json.loads(decodeB64(rawSubNode[1]))
                    # 判断节点不是b64编码的情况
                    if subNode is False:
                        pass

                # 通用数据添加
                subNode['protocol'] = rawSubNode[0]
                # 添加进节点列表
                nodeList.append(subNode)

            except Exception as e:
                LOG(prefix='[ v2ray ]', msg="不支持的订阅协议类型 %s" % e)
                pass

    # 获取订阅数据
    try:
        context = ssl.create_default_context()
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE
        rawSubData = request.urlopen(url=url, context=context).read().decode('utf-8').strip()
    except Exception as e:
        LOG(prefix='[ req ]', msg=str(e))
        return False

    # b64解码
    subData = decodeB64(rawSubData)
    # 如果不是b64编码
    if subData is False:
        pass

    # 订阅节点列表
    nodeList = []
    # 获取v2ray订阅
    v2ray(subData=subData)

    # 返回
    return nodeList


def setProxyNode(idx: int, proxyApp: str):
    """
    根据前端传入的订阅节点索引 + 代理软件类型，设置最终使用的代理节点
    :param idx:         订阅索引
    :param proxyApp:    代理软件名称
    :return:
    """

    if proxyApp == 'v2ray':
        # 获取配置模板
        confExample = json.loads(confBase.CONFIG.v2ray)

        # 获取订阅信息
        with open('%s%s.sub' % (confBase.CONFIG.proxyAppDir.get(proxyApp), proxyApp), 'r') as f:
            nodeList = json.loads(f.readline())
            nodeList[idx].pop('nickName')
            nodeList[idx].pop('id')
        # 生成完整客户端配置文件
        confExample["outbounds"].append(nodeList[idx])
    # clash
    else:
        confExample = json.loads(confBase.CONFIG.clash)

    # 生成正式配置文件，并返回当前使用的节点
    if saveConf(data=json.dumps(confExample), fileName='%sconfig.json' % confBase.CONFIG.proxyAppDir.get('v2ray')):
        return nodeList[idx]
    else:
        return False


# 设置订阅
@api.route('/api/setSubscribe', methods=['GET', 'POST'])
@generalTryCatch
def setSubscribe():
    """
    :param proxyApp:    代理软件名称
    :param subUrl:      订阅地址
    :param type:        可选，设置订阅类型: update:更新订阅
    :return:
    """

    # 获取参数
    if flask.request.method == 'POST':
        params = flask.request.json
    else:
        params = flask.request.args
    proxyApp = params.get('proxyApp')
    subUrl = params.get('subUrl')
    type = params.get('type')
    # 更新订阅的情况
    if type == 'update':
        # 获取原订阅地址
        with open('%s%s.url' % (confBase.CONFIG.proxyAppDir.get(proxyApp), proxyApp), 'r') as f:
            subUrl = f.readline()

    # 获取订阅
    subList = getSubcribe(subUrl)

    # 订阅链接无法访问的情况
    if subList is False:
        return response(code=8500, result={
            "type": "订阅设置",
            "method": "set" if type is None else type,
            "data": {
                "msg": "无法访问订阅地址，请检查本地网络、核实订阅地址是否正确"
            }
        })

    # 解析订阅数据并存储
    parserResult = parserSub(proxyApp, nodeList=subList)
    # 处理订阅解析失败的情况
    if parserResult is False:
        return response(code=8500, result={
            "type": "订阅设置",
            "method": "set" if type is None else type,
            "data": {
                "msg": "订阅解析失败，请核实订阅地址或更换其他vmess订阅地址"
            }
        })

    # 设置默认代理节点
    if setProxyNode(idx=0, proxyApp=proxyApp):

        # 保存订阅地址
        if saveConf(data=subUrl, fileName="%s%s.url" % (confBase.CONFIG.proxyAppDir.get(proxyApp), proxyApp)) is False:
            subUrl = None       # 如果保存失败则订阅地址为None
        return response(code=8200, result={
            "type": "订阅设置",
            "method": "set" if type is None else type,
            "data": {
                "msg": "订阅解析、设置完成",
                "subUrl": subUrl,
                "nodeList": parserResult,
                "useNodeIdx": 0,
                "useNodeInfo": parserResult[0]
            }
        })

    # 订阅解析成功，但配置生成失败的情况
    return response(code=8500, result={
        "type": "订阅设置",
        "method": "set" if type is None else type,
        "data": {
            "msg": "订阅解析成功，默认配置文件生成失败，请重新选择节点尝试"
        }
    })


# 更换节点
@api.route('/api/changeNode', methods=['GET', 'POST'])
@generalTryCatch
def changeNode():
    """
    :param proxyApp:    代理软件名称
    :param idx:         节点索引
    :param nodeAddr:    节点地址
    :return:
    """

    # 获取参数
    if flask.request.method == 'POST':
        params = flask.request.json
    else:
        params = flask.request.args
    idx = int(params.get('idx'))
    proxyApp = params.get('proxyApp')
    nodeAddr = params.get('nodeAddr')

    # 获取订阅信息
    with open('%s%s.sub' % (confBase.CONFIG.proxyAppDir.get(proxyApp), proxyApp), 'r') as f:
        nodeList = json.loads(f.readline())

    # 判断前端传入的idx和文件中获取的idx不一致的情况
    if nodeList[idx].get('id') != idx:
        for node in nodeList:
            if node.get('id') == idx:
                idx = nodeList.index(node)

    # 设置默认代理节点
    changeNodeResult = setProxyNode(idx=idx, proxyApp=params.get('proxyApp'))

    if changeNodeResult:
        # 执行系统命令
        if excuteCMD(cmd="baseProxy %s restart" % proxyApp):
            return response(code=8200, result={
                "type": "更换代理节点",
                "data": {
                    "msg": "节点更换完成",
                    "useNodeIdx": idx,
                    "useNodeInfo": changeNodeResult
                }
            })
        else:
            return response(code=8500, result={
                "type": "更换代理节点",
                "data": {
                    "msg": "节点更换完成，但代理服务启动失败，请手动点击按钮开启代理",
                    "useNodeIdx": idx,
                    "useNodeInfo": changeNodeResult
                }
            })


@api.route('/api/proxyInfo', methods=['GET', 'POST'])
@generalTryCatch
def proxyInfo():
    """
    返回默认的代理信息：有无使用订阅，节点列表，代理软件列表等
    :param proxyApp:    代理软件名称
    :return:
    """
    # 获取参数
    if flask.request.method == 'POST':
        params = flask.request.json
    else:
        params = flask.request.args
    proxyApp = params.get('proxyApp')

    # 处理没有订阅的情况
    if os.path.exists('%s%s.url' % (confBase.CONFIG.proxyAppDir.get(proxyApp), proxyApp)) is False or \
        os.path.exists('%s%s.sub' % (confBase.CONFIG.proxyAppDir.get(proxyApp), proxyApp)) is False or \
            os.path.exists('%sconfig.json' % confBase.CONFIG.proxyAppDir.get(proxyApp)) is False:
        # 返回
        return response(code=8200, result={
            "type": "代理信息查询",
            "data": {
                "msg": "未设置代理或者代理出现异常，请更新订阅/重新设置订阅",
                "subUrl": None,
                "nodeList": None,
                "useNodeInfo": None,
                "serviceStatus": None
            }
        })

    # 获取订阅地址
    with open('%s%s.url' % (confBase.CONFIG.proxyAppDir.get(proxyApp), proxyApp), 'r') as f:
        subUrl = f.readline()

    # 获取订阅节点
    with open('%s%s.sub' % (confBase.CONFIG.proxyAppDir.get(proxyApp), proxyApp), 'r') as f:
        nodeList = json.loads(f.readline())

    # 获取当前使用节点
    with open('%sconfig.json' % confBase.CONFIG.proxyAppDir.get(proxyApp), 'r') as f:
        conf = json.loads(f.readline())
        useNode = conf.get('outbounds')[0]

    # 获取服务运行情况
    serviceStatus = excuteCMD(cmd="baseProxy %s service" % proxyApp)

    # 返回
    return response(code=8200, result={
        "type": "代理信息查询",
        "data": {
            "msg": "获取代理信息成功",
            "subUrl": subUrl,
            "nodeList": nodeList,
            "useNodeInfo": useNode,
            "serviceStatus": serviceStatus if serviceStatus is not False else None
        }
    })


@api.route('/api/runProxy', methods=['GET', 'POST'])
@generalTryCatch
def runProxy():
    """
    flask API, 用于前端启动代理返回代理状态等
    :param proxyApp:    代理软件名称
    :param action:      动作类型, start: 启动， stop: 停止
    :return:
    """
    # 获取参数
    if flask.request.method == 'POST':
        params = flask.request.json
    else:
        params = flask.request.args
    proxyApp = params.get('proxyApp')
    action = params.get('action')

    # 执行命令
    osResult = excuteCMD(cmd="baseProxy %s %s" % (proxyApp, action))

    # 返回
    if osResult:
        return response(code=8200, result={
            "type": "代理服务管理",
            "data": osResult
    })

    return response(code=8500, result={
        "type": "代理服务管理",
        "data": {
            "msg": "服务开启失败"
        }
    })


@api.route('/api/delayTest', methods=['GET', 'POST'])
@generalTryCatch
def delayTest():
    """
    flask API, 节点延迟测试
    :param nodeList:    节点列表，示例：[{"addr": "1.1.1.1", "port": 80}, {"addr": "1.1.1.2", "port": 88}]
    :return:
    """
    # 获取参数
    if flask.request.method == 'POST':
        params = flask.request.json
    else:
        params = flask.request.args
    nodeList = params.get('nodeList')

    # 延迟测试列表
    nodesDelay = []

    # 测试延迟函数
    def delayTestTask():
        while True:

            # 使用socket测试端口连通性
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5)

            # 判断节点列表中是否存在未验证节点
            if len(nodeList) == 0:
                break
            else:
                node = nodeList.pop()

            nodeDelay = {
                "addr": node.get("addr"),
                "delay": False
            }

            timeBegin = time.time()
            try:
                status = sock.connect_ex((node.get("addr"), int(node.get("port"))))
            except Exception as e:
                LOG(msg=str(e))
                status = 500
            timeEnd = time.time()
            # 存储延迟
            if status == 0:
                delay = (timeEnd - timeBegin) * 1000
                nodeDelay["delay"] = delay

            # 添加进列表
            nodesDelay.append(nodeDelay)
            # 关闭socket
            sock.close()

    # 多线程，获取需要测试的节点总数
    nodeCount = len(nodeList)
    maxThread = 5
    # 定义线程池
    p = ThreadPoolExecutor(maxThread)
    for T in range(maxThread):

        # 判断启动的任务已经大于需要测试的总节点数的情况
        if T+1 > nodeCount:
            break
        p.submit(delayTestTask)

    # 阻塞父线程
    p.shutdown()

    # 返回
    return response(code=8200, result={
        "type": "节点延迟测试",
        "data": nodesDelay
    })


if __name__ == '__main__':
    api.run(port=8888, debug=True, host='0.0.0.0')