# proxyAPI



## 介绍

### 目录介绍

```shell
.
├── api							         # proxyAPI servic 目录
│   ├── __pycache__
│   │   ├── confBase.cpython-310.pyc
│   │   ├── confBase.cpython-311.pyc
│   │   └── confBase.cpython-39.pyc
│   ├── confBase.py						 # api 配置文件
│   ├── proxyAPI.py						 # api 主服务
│   ├── proxyAPI.service					 # systemd 托管文件
│   └── requirements.txt				         # python 依赖库
├── baseProxy.sh						 # 系统代理服务管理脚本
├── clash							 # clash 代理家目录（暂未使用）
│   ├── ClashR_1701234391.yaml
│   ├── clash
│   └── clash.service_example

└── v2ray							 # v2ray 家目录
    ├── config.json					         # 代理配置文件
    ├── geoip.dat						 # 全球ip库
    ├── geosite.dat						 # 全球域名库
    ├── v2ray							 # v2ray core程序
    ├── v2ray.service						 # 系统systemd 托管文件
    ├── v2ray.service_example					 # 系统托管文件模板
    ├── v2ray.sub						 # 订阅节点文件
    └── v2ray.url						 # 订阅地址
└── proxyAPI							 # 发布打包目录，需包含以上4个目录及baseProxy.sh文件
```

### 功能介绍

**baseProxy.sh**

> 1. 手动注入配置文件`config.json`到系统托管服务
> 2. 代理服务管理（启动，停止，重启）
> 3. 代理状态检测
>
> 显示帮助信息：
>
> `baseProxy.sh -h`

## 部署

### python

> 要求：
>
> 版本：`3.10+`

### 服务

> 目前只支持`v2ray`

```shell
# 克隆代码并把代码放置在/soft/proxy目录
git clone "仓库地址"

# 安装baseProxy.sh
ln -s /soft/proxy/baseProxy.sh /bin/baseProxy
chmod +x /soft/proxy/baseProxy.sh

# 安装v2ray 系统托管服务
baseProxy v2ray install /soft/proxy/v2ray/config.json
chmod +x /soft/proxy/v2ray/v2ray

# 安装api 系统服务
ln -s /soft/proxy/api/proxyAPI.service /lib/systemd/system/
systemctl daemon-reload

# 安装依赖
cd /soft/proxy/api/ && pip3 install requirements.txt

# 启动api
systemctl start proxyAPI

# 查看服务状态
systemctl status proxyAPI
```

### 部署到其他路径下，需修改以下2个文件：

> 默认为 `/soft/proxy`

`baseProxy.sh`: baseDir 代理基本目录

`confBase.py`: api 配置文件中代理家目录

## 接口

### 设置订阅

**接口：**`/api/setSubscribe`

**请求参数：**

| 参数名       | 参数值       | 备注                              |
| ------------ | ------------ | --------------------------------- |
| type（可选） | 类型         | 示例：<br />type=update，更新订阅 |
| proxyApp     | 代理软件名称 | 示例：<br />proxyApp=v2ray        |

**返回值：**

> 前3个为通用参数

| 参数名    | 参数值     | 备注                                  |
| --------- | ---------- | ------------------------------------- |
| code      | 8200,8500  | api返回状态码                         |
| type      | 接口简述   | 接口类型/描述，示例：<br />“订阅设置” |
| timestamp | 1701586072 | 数据返回的时间戳                      |

### 更换代理节点

**接口：**`/api/changeNode`
> 更换选择的代理节点
> **热加载:**会reload服务

**请求参数：**

| 参数名   | 参数值                             | 备注                               |
| -------- | ---------------------------------- | ---------------------------------- |
| idx      | 更换的节点id                       | 示例：<br />idx=0                  |
| proxyApp | 代理软件名称                       | 示例：<br />proxyApp=v2ray         |
| nodeAddr | 需要更换的目标代理节点地址（可选） | 示例：<br />nodeAddr=tw01.test.com |

### 代理信息查询

> 查询已配置的代理情况

**接口：**`/api/proxyInfo`

**请求参数：**

| 参数名   | 参数值       | 备注                       |
| -------- | ------------ | -------------------------- |
| proxyApp | 代理软件名称 | 示例：<br />proxyApp=v2ray |

### 代理服务管理

**接口：**`/api/runProxy`

**请求参数：**

| 参数名   | 参数值       | 备注                                               |
| -------- | ------------ | -------------------------------------------------- |
| proxyApp | 代理软件名称 | 示例：<br />proxyApp=v2ray                         |
| action   | 动作类型     | start: 启动， stop: 停止，示例：<br />action=start |

### 节点延迟测试

**接口：**`/api/delayTest`

**请求参数：**

| 参数名   | 参数值   | 备注                                                         |
| -------- | -------- | ------------------------------------------------------------ |
| nodeList | 节点列表 | 示例：<br />nodeList=[{"addr": "vjp01.holytechx.com","port": 23335}] |