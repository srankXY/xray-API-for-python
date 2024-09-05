#!/usr/bin/env /bin/bash
#
# 底层代理可统一放置在某一目录，具体的代理文件放置在该目录下
# 参数解释
# proxyApp=$1        # 代理软件|验证的代理: clash|ssr
# runType=$2         # 脚本运行类型: start|stop|restart|install
# configFile=$3      # 代理配置文件(可选，绝对路径): clash.yaml
#

# 所有底层代理的放置目录
baseDir=/soft/proxy

##### 公共函数 ########
# 日志
LOG(){
  : '
  接收参数:
  $1  前缀
  $2  日志内容
  $3  特别标注
  '
  echo -e "\e[0;33m [ $1 ] \e[0m$2\e[36m$3\e[0m"
}

# json
JSON(){
  # 接收参数:
  # $1  json 数据
  echo -e "$1"
}

# 服务安装函数
installProxy(){
  # 接收参数
  # proxyApp=$1   # 安装的代理类型

  # 判断系统服务中是否存在该服务
  rm -rf /lib/systemd/system/${1}.service || pass
  # 安装service
  ln -s ${baseDir}/${1}/${1}.service /lib/systemd/system && echo -e "\e[0;33m [ $1 ] \e[0m 系统服务已载入"

  # reload systemd
  systemctl daemon-reload
}

# 启动服务
start(){
  systemctl enable ${1}.service > /dev/null 2>&1
  systemctl start ${1}.service && JSON '{"code":200, "osMsg": "启动成功"}'
}

# 停止服务
stop(){
  systemctl disable ${1}.service > /dev/null 2>&1
  systemctl stop ${1}.service && JSON '{"code":200, "osMsg": "停止成功"}'
}

# restart
restart(){
  stop "$1" > /dev/null && start "$1" > /dev/null && JSON '{"code":200, "osMsg": "重启成功"}'
}

# 删除系统代理变量
undoEnvironment(){
  sed -i '/\w\+_proxy/d' /etc/profile
  sed -i '/\w\+_proxy/d' /etc/environment
}

# 设置系统变量
setEnvrionment(){
  # 接受参数:  $1=ip:port

  # 先清理变量
  undoEnvironment

  # 重新设置变量
  echo -e "http_proxy=$1
https_proxy=$1
all_proxy=$1" >> /etc/environment

  echo -e "export http_proxy=$1
export https_proxy=$1
export all_proxy=$1" >> /etc/profile

}

# help
help(){
  echo -e "
  格式：
  baseProxy [proxyApp] [runType] [configFile]

  参数：
  -h            显示帮助信息

  参数示例：
  proxyApp      clash|v2ray|ssr：代理软件
  runType       start|stop|restart|install|check
  configFile    对应代理软件的配置文件，<绝对路径> [可选，仅在安装系统服务时有效]
  "
}

# 验证
checkProxy(){
  LOG 检测 "[ $1 ] 服务监听情况:\n" "$(netstat -tpunl | grep "$1" | awk '{print "", $4, $NF}')"
  # 当前脚本所属shell导入环境变量
  source /etc/profile && LOG "检测" '当前外部出口IP为: ' "$(curl ifconfig.io 2> /dev/null)"
}

# 服务运行情况
checkService(){
  # $1 查看的服务
  status=$(systemctl is-active "$1")
  JSON "{\"code\":200, \"serviceStatus\": \"$status\"}"
}
##### 公共函数结束 ########

# clash
clashFunc(){
  # 接受参数:
  runType=$2
  configFile=$3  # 安装时使用

  # 修改为用户上传的配置文件
  alterService(){

    # 判断有无传入配置文件
    if [[ ! ${configFile} ]];then
      echo -e "\e[0;33m [ clash ] \e[0m 安装底层代理需传入配置文件"
      exit 1
    fi
    # 使用模板处理配置文件，方便用户重新上传配置文件
    rm -rf ${baseDir}/clash/clash.service
    cp -pr ${baseDir}/clash/clash.service_example ${baseDir}/clash/clash.service

    # 修改配置
    sed -i '/ExecStart=/d' ${baseDir}/clash/clash.service
    sed -i "/ExecStartPre/a\ExecStart=${baseDir}/clash/clash '-f' '$1'" ${baseDir}/clash/clash.service
  }

  case ${runType} in
    start)
      start clash
#      setEnvrionment 127.0.0.1:7890
    ;;
    stop)
      stop clash
      undoEnvironment
    ;;
    restart)
      restart clash
    ;;
    check)
      checkProxy clash
    ;;
    service)
      checkService clash
    ;;
    install)
      alterService ${configFile}
      installProxy clash
    ;;
  esac
}

# v2ray
v2rayFunc(){
  # 接受参数:
  runType=$2
  configFile=$3  # 安装时使用

  # 修改为用户上传的配置文件
  alterService(){

    # 判断有无传入配置文件
    if [[ ! ${configFile} ]];then
      LOG v2ray '安装底层代理需传入配置文件'
      exit 1
    fi
    # 使用模板处理配置文件，方便用户重新上传配置文件
    rm -rf ${baseDir}/v2ray/v2ray.service
    cp -pr ${baseDir}/v2ray/v2ray.service_example ${baseDir}/v2ray/v2ray.service

    # 修改配置
    sed -i '/ExecStart=/d' ${baseDir}/v2ray/v2ray.service
    sed -i "/ExecStartPre/a\ExecStart=${baseDir}/v2ray/v2ray 'run' '-c' '$1'" ${baseDir}/v2ray/v2ray.service
  }

  case ${runType} in
    start)
      start v2ray
#      setEnvrionment http://127.0.0.1:1080
    ;;
    stop)
      stop v2ray
      undoEnvironment
    ;;
    restart)
      restart v2ray
    ;;
    check)
      checkProxy v2ray
    ;;
    service)
      checkService v2ray
    ;;
    install)
      alterService ${configFile}
      installProxy v2ray
    ;;
  esac
}

# 主入口
case "$1" in
  clash)
    clashFunc "$@"
  ;;
  v2ray)
    v2rayFunc "$@"
  ;;
  *)
    help
  ;;
esac