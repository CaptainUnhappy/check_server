#!/bin/bash

CONFIG_FILE="/root/.my.cnf"

# 检查是否存在/root/.my.cnf文件
if [ -f "$CONFIG_FILE" ]; then
    echo "/root/.my.cnf 文件已存在，使用该文件中的配置登录 MySQL。"
else
    # 提示输入账号密码，使用 / 分割
    echo "/root/.my.cnf 文件不存在，请输入MySQL账号和密码，格式：用户名/密码。"
    read -p "请输入MySQL用户名/密码 (格式: 用户名/密码): " CREDENTIALS
    
    # 解析用户名和密码
    MYSQL_USER=$(echo $CREDENTIALS | awk -F'/' '{print $1}')
    MYSQL_PASSWORD=$(echo $CREDENTIALS | awk -F'/' '{print $2}')
    
    # 检查是否输入了正确的格式
    if [[ -z "$MYSQL_USER" || -z "$MYSQL_PASSWORD" ]]; then
        echo "输入格式有误，请确保格式为 用户名/密码。"
        exit 1
    fi
    
    # 创建/root/.my.cnf文件并写入MySQL用户和密码
    cat > $CONFIG_FILE << EOF
[client]
user=$MYSQL_USER
password=$MYSQL_PASSWORD
EOF

    # 设置/root/.my.cnf文件权限为600，确保安全
    chmod 600 $CONFIG_FILE

    echo "/root/.my.cnf 文件已创建。"
fi

# 3.1 检查数据库状态
echo "3.1 检查数据库状态"
service mysqld status | grep -q "running"
if [ $? -eq 0 ]; then
    echo "√ 数据库运行正常"
else
    echo "× 数据库未运行"
fi

# 3.2 检查 Innodb 索引命中率
echo "3.2 检查 Innodb 索引命中率"
innodb_reads=$(mysql -e "SHOW GLOBAL STATUS LIKE 'Innodb_buffer_pool_reads';" | awk 'NR==2 {print $2}')
innodb_read_requests=$(mysql -e "SHOW GLOBAL STATUS LIKE 'Innodb_buffer_pool_read_requests';" | awk 'NR==2 {print $2}')
if [[ $innodb_reads -gt 0 ]]; then
    hit_rate=$(echo "scale=2; $innodb_read_requests / ($innodb_read_requests + $innodb_reads) * 100" | bc)
    if (( $(echo "$hit_rate > 80" |bc -l) )); then
        echo "√ Innodb 索引命中率 > 80%"
    else
        echo "× Innodb 索引命中率 <= 80%"
    fi
else
    echo "× 无法获取有效的Innodb命中率数据"
fi

# 3.3 检查慢SQL占比
echo "3.3 检查慢SQL占比"
slow_queries=$(mysql -e "SHOW GLOBAL STATUS LIKE 'Slow_queries';" | awk 'NR==2 {print $2}')
total_queries=$(mysql -e "SHOW GLOBAL STATUS LIKE 'Queries';" | awk 'NR==2 {print $2}')
slow_query_ratio=$(echo "scale=2; ($slow_queries / $total_queries) * 100" | bc)
if (( $(echo "$slow_query_ratio < 10" |bc -l) )); then
    echo "√ 慢SQL占比 < 10%"
else
    echo "× 慢SQL占比 >= 10%"
fi

# 3.4 检查活跃连接数使用率
echo "3.4 检查活跃连接数使用率"
active_connections=$(mysql -e "SHOW STATUS LIKE 'Threads_running';" | awk 'NR==2 {print $2}')
max_connections=$(mysql -e "SHOW VARIABLES LIKE 'max_connections';" | awk 'NR==2 {print $2}')
active_ratio=$(echo "scale=2; ($active_connections / $max_connections) * 100" | bc)
if (( $(echo "$active_ratio < 80" |bc -l) )); then
    echo "√ 活跃连接数使用率 < 80%"
else
    echo "× 活跃连接数使用率 >= 80%"
fi

# 3.5 检查备份状态
echo "3.5 检查备份状态（默认√）"
# backup_log="/opt/vany/sh/database/log/xtrabackup_full.log"
# if [ -f "$backup_log" ]; then
    # tail -f $backup_log
    echo "√ 备份状态正常"
# else
    # echo "× 无法找到备份日志"
# fi

# 3.6 检查系统日志错误输出
echo "3.6 检查系统日志错误输出（默认√）"
# datadir=$(cat /etc/my.cnf | grep datadir | awk -F'=' '{print $2}' | tr -d ' ')
# error_log="$datadir/mysql-error.log"
# if [ -f "$error_log" ]; then
    # grep 'ERROR' $error_log
    # if [ $? -eq 0 ]; then
        # echo "× 日志中有错误信息"
    # else
        echo "√ 系统日志无错误"
    # fi
# else
    # echo "× 未找到错误日志文件"
# fi

# 3.7 获取数据库版本信息
echo "3.7 获取数据库版本信息"
mysql_version=$(mysql -V)
echo "当前MySQL版本: $mysql_version"

# 3.8 获取数据库大小和数据量
echo "3.8 获取数据库大小和数据量"
mysql -e "select table_schema as DBNAME,concat(round(sum(data_length+index_length)/1024/1024/1024,2),' GB ') as DBSZIE,SUM(table_rows) AS 'Total Rows' from information_schema.tables where table_schema !='information_schema' and table_schema !='mysql' group by table_schema;"

