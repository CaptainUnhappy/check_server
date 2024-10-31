#!/bin/bash
# File Name: 巡检脚本
# Version: V1
# Author: yy
# CREATED  DATE: 2023/06/28
   
   
IPV4_REGEX="^(([0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])\.){3}([0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])(\/([0-9]|[1-2][0-9]|3[0-2]))?$"
   
   
USER_INFO(){
# 特权用户
local SUPER_USER=$(cat /etc/shadow | awk -F: '($2==""){printf "%s ",$1}')
# 远程用户
local RLOGIN_USER=$(awk -F ":" '/\$1|\$6/{printf "%s ",$1}' /etc/shadow)
# 空密码账户
local NOPASSWD_USER=$(cat /etc/shadow | awk -F: '($2==""){printf "%s ",$1}')
# sudo账户
local SUDOER_USER=$(cat /etc/passwd | awk -F ':' '$4 ~ /^10$/{printf "%s ",$1}')
echo -e "
特权用户列表：${SUPER_USER}
可以远程登陆的用户列表：${RLOGIN_USER}
密码为空的用户列表：${NOPASSWD_USER}
具有Sudo权限的用户列表：${SUDOER_USER}"
}
   
LOGIN_SAFE(){
local LOGIN_FAILE=$(lastb | awk '/^[a-zA-Z0-9]/ && $3 ~ /\./ {count[$3]++} END {printf("%-15s %s\n", "IP", "Failes"); for (ip in count) {if (ip != "") printf("%-15s %d\n", ip, count[ip])}}')
local LOGIN_ROOT_FAILE=$(grep "Failed password for root" /var/log/secure | awk '/^[a-zA-Z0-9]/ && $11 ~ /\./ {count[$11]++} END {printf("%-15s %s\n", "IP", "Failes"); for (ip in count) {if (ip != "") printf("%-15s %d\n", ip, count[ip])}}')
echo -e "
登陆失败的IP记录:
--------------------------
${LOGIN_FAILE}
\n爆破主机root账号的可疑IP记录:
--------------------------
${LOGIN_ROOT_FAILE}"
}
   
OS_INFO(){
# 主机名
local OS_NAME=`uname -n`
# 主机IP地址
local OS_IP=`ip a | grep -v '127.0.0.1' | grep -oP "inet \K([0-9]{1,3}[.]){3}[0-9]{1,3}" | awk '{printf "%s ",$0}'`
# 系统版本
local OS_VERSION=`cat /etc/redhat-release`
# 系统类型
local OS_TYPE=`uname`
# 主机序列号
local OS_NUM=`dmidecode -t system | grep 'Serial Number' | awk '{print $3}'`
# 系统内核版本
local OS_KERNEL=`uname -r`
# 系统语言环境
local OS_LANG=`echo $LANG`
# 系统时间
local OS_DATE=`date +"%Y-%m-%d %H:%M:%S"`
# 系统运行时间
local OS_UPTIME=`uptime | awk -F',' '{sub(/.*up /,"",$1);print $1'}`
# 系统上次重启时间
local OS_LAST_REBOOT=`last reboot | head -1 | awk '{print $5,$6,$7,$8,$10}'`
# 系统上次关机时间
local OS_LAST_SHUTDOWN=`last -x | grep shutdown | head -1 | awk '{print $5,$6,$7,$8,$10}'`
echo -e "
主机名：$OS_NAME
主机ip地址(可能有多个,以实际信息为准)：$OS_IP
主机类型：$OS_TYPE
主机序列号：${OS_NUM:-获取信息失败}
系统版本：$OS_VERSION
系统内核版本：$OS_KERNEL
系统语言环境：${OS_LANG}
系统时间：$OS_DATE
系统已运行时间：$OS_UPTIME
系统上次重启时间：${OS_LAST_REBOOT:-获取信息失败}
系统上次关机时间：${OS_LAST_SHUTDOWN:-获取信息失败}"
}
   
   
OS_HDWARE(){
# CPU架构
local CPU_ARCH=$(uname -m)
# CPU型号
local CPU_TYPE=$(cat /proc/cpuinfo | grep "model name" | uniq | awk -F':' '{sub(/ /,"",$2);print $2}')
# CPU个数
local CPU_NUM=$(cat /proc/cpuinfo | grep "physical id" | sort | uniq | wc -l)
# CPU 核数
local CPU_CORE=$(cat /proc/cpuinfo | grep cores | uniq | awk -F':' '{sub(/ /,"",$2);print $2}')
# CPU 频率
local CPU_HZ=$(cat /proc/cpuinfo | grep "cpu MHz" | uniq | awk -F':' '{sub(/ /,"",$2);printf "%s MHz\n",$2}')
# 内存容量
local ME_SIZE=$(awk '/MemTotal/ {printf "%.2f", $2/1024/1024}' /proc/meminfo)
# 空闲内存
local ME_FREE=$(awk '/MemFree/ {printf "%.2f", $2/1024/1024}' /proc/meminfo)
# 可用内存
local ME_FREEE=$(awk '/^Cached:/ {cached=$2} /^MemFree:/ {free=$2} END {printf "%.2f", (cached + free)/1024/1024}' /proc/meminfo)
# 内存使用率
local ME_USE=$(awk 'BEGIN{printf "%.1f%\n",('$ME_SIZE'-'$ME_FREEE')/'$ME_SIZE'*100}')
# SWAP大小
local ME_SWAP_SIZE=$(awk '/SwapTotal/ {printf "%.2f", $2/1024/1024}' /proc/meminfo)
# SWAP可用
local ME_SWAP_FREE=$(awk '/SwapFree/ {printf "%.2f", $2/1024/1024}' /proc/meminfo)
# SWAP使用率
local ME_SWAP_USE=$(awk 'BEGIN{printf "%.1f%\n",('$ME_SWAP_SIZE'-'$ME_SWAP_FREE')/'$ME_SWAP_SIZE'*100}')
# Buffer大小
local ME_BUF=$(cat /proc/meminfo | grep 'Buffers:' | awk '{printf "%s KB",$2}')
# 内存Cache大小
local ME_CACHE=$(cat /proc/meminfo | grep '^Cached:' | awk '{printf "%s KB",$2}')
# 输出值
echo "
CPU型号：$CPU_TYPE
CPU架构：$CPU_ARCH
CPU个数：$CPU_NUM
CPU核数: $CPU_CORE
CPU频率：$CPU_HZ
内存容量：${ME_SIZE} GB
内存空闲：${ME_FREE} GB
内存可用：${ME_FREEE} GB
内存使用率：${ME_USE}
SWAP容量：$ME_SWAP_SIZE GB
SWAP可用容量：$ME_SWAP_FREE GB
SWAP使用率：$ME_SWAP_USE
内存Buffer大小：${ME_BUF}
内存Cache大小：${ME_CACHE}"
}
   
OS_RESOURCE(){
# 系统磁盘列表
local DISK_LIST=$(lsblk | egrep "^[a-z].*" | grep -v "^sr" | awk '{printf "%s ",$1}')
# 系统磁盘分区存储使用情况
local DISK_STATUS=$(df -Th)
# 系统磁盘分区inode使用情况
local DISK_INODE_STATUS=$(df -Thi)
# CPU空闲率
local CPU_FREE=$(top -bn1 | grep -m 1 "Cpu(s)" | awk '{if ($0 ~ /%us/) print $5 + 0; else if ($8 == "id,") print 100; else print $8}')
# CPU使用率
local CPU_USE=$(awk 'BEGIN{printf "%.1f%\n",100-'$CPU_FREE'}')
# CPU_TOP_TEN
local CPU_TOP_TEN=$(ps -eo user,pid,pcpu,pmem,args --sort=-pcpu | head -n 10)
# MEM_TOP_TEN
local MEM_TOP_TEN=$(ps -eo user,pid,pcpu,pmem,args --sort=-pmem | head -n 10)
# DISK_IO
local DISK_IO=$(iotop -bon 2)
# 当前进程数
local CPU_PROCESSORS=$(top -d 1 -n 1 -b | awk 'NR==2{print $2}')
# 当前正在运行进程数
local CPU_RUN_PROCESSORS=$(top -d 1 -n 1 -b | awk 'NR==2{print $4}')
# 当前正在休眠进程数
local CPU_SL_PROCESSORS=$(top -d 1 -n 1 -b | awk 'NR==2{print $6}')
# 当前停止运行进程数
local CPU_STOP_PROCESSORS=$(top -d 1 -n 1 -b | awk 'NR==2{print 8}')
# 当前僵尸进程数
local CPU_ZOM_PROCESSORS=$(top -d 1 -n 1 -b | awk 'NR==2{print $10}')
# 文件句柄数
local OS_FDS=$(cat /proc/sys/fs/file-nr | awk '{print $3}')
# 已使用的句柄
local OS_FD=$(cat /proc/sys/fs/file-nr | awk '{print $1}')
# 系统单个进程运行打开fd限制数量
local OS_FD_LIMIT=$(ulimit -n)
# 系统当前socket连接数
local OS_SOCKET=$(netstat -anp &>/dev/null && netstat -anp | wc -l)
# 系统 established socket
local OS_ES_SOCKET=$(netstat -anp &>/dev/null && netstat -anp | grep "ESTABLISHED" | wc -l)
# 系统 sync socket数量
local OS_SYNC_SOCKET=$(netstat -anp &>/dev/null && netstat -anp | grep "SYN" | wc -l)
echo -e "
CPU使用率：$CPU_USE
CPU使用率前十进程信息：
${CPU_TOP_TEN}
\n内存使用率前十进程信息：
${MEM_TOP_TEN}
\n磁盘IO信息(统计两次)：
${DISK_IO}
\n系统磁盘列表：${DISK_LIST}
\n系统磁盘分区存储使用情况：
${DISK_STATUS}
\n系统磁盘分区inode使用情况：
${DISK_INODE_STATUS}
\n系统当前进程数：$CPU_PROCESSORS
系统当前进程运行数：$CPU_RUN_PROCESSORS
系统当前休眠进程数：$CPU_SL_PROCESSORS
系统当前停止进程数：$CPU_STOP_PROCESSORS
系统当前僵尸进程数：$CPU_ZOM_PROCESSORS
\n系统当前允许最大文件句柄数量：${OS_FDS}
系统当前已使用的文件句柄数量：${OS_FD}
系统单个进程运行打开文件句柄限制：${OS_FD_LIMIT}
\n系统当前socket连接数：${OS_SOCKET:-"net-tools 未安装,获取信息失败"}
系统 established socket数量: ${OS_ES_SOCKET:-"net-tools 未安装,获取信息失败"}
系统 sync socket数量：${OS_SYNC_SOCKET:-"net-tools 未安装,获取信息失败"}
"
}
   
OS_SECURITY(){
# 系统所有能登录的用户
local OS_USER=(`cat /etc/passwd | awk -F':' '$NF !~/nologin|sync|shutdown|halt/ {print $1}'`)
# 可登录用户数
local OS_USERS=$(cat /etc/passwd | awk -F':' '$NF !~/nologin|sync|shutdown|halt/ {print $1}' | wc -l)
# 系统当前登陆用户
local OS_LOGIN_USER=$(who | sed 's#[()]##g' | awk '{printf "   用户: %10s 终端: %7s 登录时间: %7s %7s 登录IP: %7s\n",$1,$2,$3,$4,$5}')
# 当前用户计划任务列表
local CRONTAB_LIST=$(crontab -l)
# Selinux
local OS_SELINUX=$(getenforce)
# 防火墙状态
local OS_FIREWALLD=$(service firewalld status &> /dev/null && echo on || echo off)
echo -e "
防火墙状态: $OS_FIREWALLD
Selinux状态：${OS_SELINUX}
系统可登录用户数：${OS_USERS}
系统可登录用户：${OS_USER[@]}
用户登陆记录：
--------------------------
$(for i in ${OS_USER[@]};
do
echo "用户 $i 最后1次登录信息: $(lastlog -u $i | awk 'NR==2')"
done)
\n系统当前登录用户：
${OS_LOGIN_USER}
\n当前用户计划任务列表：
${CRONTAB_LIST}
"
}
   
   
   
# 准备操作
   
CHECK() {
    # root账号执行权限
    if [ $(id -u) -ne 0 ]; then
        echo "Please execute this script as root!"
        exit 1
    fi
    # yum install -y  bc iotop
}
   
IP_INFO() {
    PWDDIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" &>/dev/null && pwd -P)
    if [ -f ${PWDDIR}/IP.tmp ];then
        IP=$(cat ${PWDDIR}/IP.tmp)
        echo "使用历史ip地址[$IP],如果跟当前真实地址不一致,请删除当前目录下的[IP.tmp]文件后重新执行该脚本."
    else
        read -p "请输入当前主机的ip地址,(用作输出文件名): " IP
        [[ ${IP} =~ $IPV4_REGEX ]] || {
            echo "请输出正确的ip格式."
            exit 1
        }
        echo ${IP} > ${PWDDIR}/IP.tmp
    fi
}
   
# 生成HTML文件
   
CREATE_HTML_HEAD() {
    echo -e "
<html>
<HEAD>
<title>系统巡检报告</title>
<style type=text/css>
    h2, h3, h4 {
        margin: 5px;
    }
    pre {
        margin: 5px;
        padding: 5px;
        border: 1px solid gray;
        background-color: #eeeeee;
    }
    #index {
        position: fixed;
        top: 50%;
        right: 10px;
        transform: translateY(-50%);
        background-color: #eeeeee;
        padding: 10px;
        border: 2px solid blue;
    }
    #index ul {
        list-style-type: none;
        padding: 0;
    }
    #index ul li {
        margin-bottom: 5px;
    }
</style>
</HEAD>
<body>"
}
   
CREATE_HTML_DIV_START(){
    echo -e "
    <div id="index">
    <h3>目录</h3>
    <ul>"
}
   
CREATE_HTML_DIV_END(){
    echo -e "
    </ul>
    </div>"
}
   
CREATE_HTML_LI(){
    echo -e "<li><a href="#${1}">${1}</a></li>"
}
   
# 索引目录
   
CREATE_HTML_LI_LIST(){
    CREATE_HTML_LI 用户安全审计
    CREATE_HTML_LI 登陆失败记录
    CREATE_HTML_LI 系统信息
    CREATE_HTML_LI 配置信息
    CREATE_HTML_LI 系统资源巡检区
    CREATE_HTML_LI 系统安全审计
}
   
CREATE_HTML_BODY() {
    echo -e "<h2 id="${1}">${1}</h2><pre>${2}</pre>"
}
   
# 巡检项列表
   
CREATE_HTML_BODY_LIST(){
    CREATE_HTML_BODY 用户安全审计 "$(USER_INFO)"
    CREATE_HTML_BODY 登陆失败记录 "$(LOGIN_SAFE)"
    CREATE_HTML_BODY 系统信息 "$(OS_INFO)"
    CREATE_HTML_BODY 配置信息 "$(OS_HDWARE)"
    CREATE_HTML_BODY 系统资源巡检区 "$(OS_RESOURCE)"
    CREATE_HTML_BODY 系统安全审计 "$(OS_SECURITY)"
}
   
   
CREATE_HTML_END() {
    echo -e "</BODY></html>"
}
   
# 输出html文档
CREATE_HTML() {
    CREATE_HTML_HEAD
    CREATE_HTML_DIV_START
    CREATE_HTML_LI_LIST
    CREATE_HTML_DIV_END
    CREATE_HTML_BODY_LIST
    CREATE_HTML_END
}
   
MAIN() {
    CHECK
    IP_INFO
    CREATE_HTML > ${PWDDIR}/${IP}_$(date +"%Y%m%d").html
    echo "巡检结束,html报告已生成:${PWDDIR}/${IP}_$(date +"%Y%m%d").html"
}
   
MAIN