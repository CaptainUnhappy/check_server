#!/bin/bash

# su - oracle
# lsnrctl status
# SELECT UPPER(F.TABLESPACE_NAME) "表空间名", D.TOT_GROOTTE_MB "表空间大小(M)", D.TOT_GROOTTE_MB - F.TOTAL_BYTES "已使用空间(M)", TO_CHAR(ROUND((D.TOT_GROOTTE_MB - F.TOTAL_BYTES) / D.TOT_GROOTTE_MB * 100, 2), '990.99') || '%' "使用比", F.TOTAL_BYTES "空闲空间(M)", F.MAX_BYTES "最大块(M)" FROM (SELECT TABLESPACE_NAME, ROUND(SUM(BYTES) / (1024 * 1024), 2) TOTAL_BYTES, ROUND(MAX(BYTES) / (1024 * 1024), 2) MAX_BYTES FROM SYS.DBA_FREE_SPACE GROUP BY TABLESPACE_NAME) F, (SELECT DD.TABLESPACE_NAME, ROUND(SUM(DD.BYTES) / (1024 * 1024), 2) TOT_GROOTTE_MB FROM SYS.DBA_DATA_FILES DD GROUP BY DD.TABLESPACE_NAME) D WHERE D.TABLESPACE_NAME = F.TABLESPACE_NAME ORDER BY 1;
# select tablespace_name, count(*) as extends, round(sum(bytes) / 1024 / 1024, 2) as MB, sum(blocks) as block from dba_free_space group by tablespace_name;
# select sum(t.NUM_ROWS) FROM USER_TABLES T;

CONFIG_FILE="/root/.oracle.cnf"

# 删除/root/.oracle.cnf文件以确保安全
if [ -f "$CONFIG_FILE" ]; then
    rm -f "$CONFIG_FILE"
    echo "已删除/root/.oracle.cnf文件"
else
    # 提示输入 Oracle 用户名/密码
    read -p "请输入 Oracle 用户名/密码 (格式: 用户名/密码): " CREDENTIALS
    
    # 解析用户名和密码
    ORACLE_USER=$(echo $CREDENTIALS | awk -F'/' '{print $1}')
    ORACLE_PASSWORD=$(echo $CREDENTIALS | awk -F'/' '{print $2}')
    
    # 检查是否输入了正确的格式
    if [[ -z "$ORACLE_USER" || -z "$ORACLE_PASSWORD" ]]; then
        echo "输入格式有误，请确保格式为 用户名/密码。"
        exit 1
    fi
    
    # 创建/root/.oracle.cnf文件并写入Oracle用户和密码
    cat > $CONFIG_FILE << EOF
[client]
user=$ORACLE_USER
password='$ORACLE_PASSWORD'
EOF
fi

# 定义 SERVICE_NAME 为 VOFP
SERVICE_NAME="VOFP"

# 测试 Oracle 连接是否成功
su - oracle -c "sqlplus -s \"$ORACLE_USER/$ORACLE_PASSWORD@(DESCRIPTION=(ADDRESS_LIST=(ADDRESS=(PROTOCOL=TCP)(HOST=WeiXin03.njou.cloud)(PORT=1521)))(CONNECT_DATA=(SERVICE_NAME=$SERVICE_NAME)))\" <<EOF
exit
EOF"

if [ $? -ne 0 ]; then
    # 如果Oracle登录失败，删除配置文件并提示错误
    rm -f "$CONFIG_FILE"
    echo "Oracle 登录失败，请检查用户名和密码。"
    exit 1
fi

# 3.1 检查数据库状态
su - oracle -c "service oracle status | grep -q 'running'"
if [ $? -eq 0 ]; then
    echo "    √ 数据库运行正常"
else
    echo "× 数据库未运行"
fi

# 3.2 检查表空间大小与使用率
echo "3.2 检查表空间大小与使用率："
su - oracle -c "sqlplus -s \"$ORACLE_USER/$ORACLE_PASSWORD@(DESCRIPTION=(ADDRESS_LIST=(ADDRESS=(PROTOCOL=TCP)(HOST=WeiXin03.njou.cloud)(PORT=1521)))(CONNECT_DATA=(SERVICE_NAME=$SERVICE_NAME)))\" <<EOF
SET PAGESIZE 500
SET LINESIZE 200
COLUMN \"表空间名\" FORMAT A20
COLUMN \"表空间大小(M)\" FORMAT A15
COLUMN \"已使用空间(M)\" FORMAT A15
COLUMN \"使用比\" FORMAT A10
COLUMN \"空闲空间(M)\" FORMAT A15

SELECT UPPER(F.TABLESPACE_NAME) AS \"表空间名\",
       D.TOT_GROOTTE_MB AS \"表空间大小(M)\",
       D.TOT_GROOTTE_MB - F.TOTAL_BYTES AS \"已使用空间(M)\",
       TO_CHAR(ROUND((D.TOT_GROOTTE_MB - F.TOTAL_BYTES) / D.TOT_GROOTTE_MB * 100, 2),'990.99') || '%' AS \"使用比\",
       F.TOTAL_BYTES AS \"空闲空间(M)\"
FROM (SELECT TABLESPACE_NAME, 
             ROUND(SUM(BYTES) / (1024 * 1024), 2) TOTAL_BYTES
      FROM DBA_FREE_SPACE
      GROUP BY TABLESPACE_NAME) F,
     (SELECT TABLESPACE_NAME, 
             ROUND(SUM(BYTES) / (1024 * 1024), 2) TOT_GROOTTE_MB
      FROM DBA_DATA_FILES
      GROUP BY TABLESPACE_NAME) D
WHERE D.TABLESPACE_NAME = F.TABLESPACE_NAME;
EXIT;
EOF"

# 3.3 检查活跃连接数使用率
echo "3.3 检查活跃连接数使用率："
su - oracle -c "sqlplus -s \"$ORACLE_USER/$ORACLE_PASSWORD@(DESCRIPTION=(ADDRESS_LIST=(ADDRESS=(PROTOCOL=TCP)(HOST=WeiXin03.njou.cloud)(PORT=1521)))(CONNECT_DATA=(SERVICE_NAME=$SERVICE_NAME)))\" <<EOF
SET PAGESIZE 500
SET LINESIZE 200
COLUMN \"活动连接\" FORMAT A15
COLUMN \"最大连接数\" FORMAT A15

SELECT VALUE AS \"活动连接\"
FROM V\$SYSSTAT
WHERE NAME = 'sessions';

SELECT VALUE AS \"最大连接数\"
FROM V\$PARAMETER
WHERE NAME = 'sessions';
EXIT;
EOF"

# 3.4 检查备份状态
echo "3.4 检查备份状态（默认√）"
# 添加你自定义的备份状态检查逻辑

# 3.5 检查系统日志错误输出
echo "3.5 检查系统日志错误输出（默认√）"
# 添加你自定义的系统日志检查逻辑

# 3.6 获取数据库版本信息
echo "3.6 获取数据库版本信息："
su - oracle -c "sqlplus -s \"$ORACLE_USER/$ORACLE_PASSWORD@(DESCRIPTION=(ADDRESS_LIST=(ADDRESS=(PROTOCOL=TCP)(HOST=WeiXin03.njou.cloud)(PORT=1521)))(CONNECT_DATA=(SERVICE_NAME=$SERVICE_NAME)))\" <<EOF
SELECT * FROM v\$version;
EXIT;
EOF"

# 3.7 获取数据库大小和数据量
echo "3.7 获取数据库大小和数据量："
su - oracle -c "sqlplus -s \"$ORACLE_USER/$ORACLE_PASSWORD@(DESCRIPTION=(ADDRESS_LIST=(ADDRESS=(PROTOCOL=TCP)(HOST=WeiXin03.njou.cloud)(PORT=1521)))(CONNECT_DATA=(SERVICE_NAME=$SERVICE_NAME)))\" <<EOF
SELECT table_name, 
       ROUND(SUM(bytes)/1024/1024,2) AS \"大小(MB)\"
FROM dba_segments
GROUP BY table_name
ORDER BY 2 DESC;
EXIT;
EOF"

# 删除/root/.oracle.cnf文件以确保安全
if [ -f "$CONFIG_FILE" ]; then
    rm -f "$CONFIG_FILE"
    echo "已删除/root/.oracle.cnf文件"
fi
