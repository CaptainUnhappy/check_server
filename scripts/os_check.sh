#!/usr/bin/env bash
# Linux read-only resource collection. Invoke with an anonymous alias and output path.
set -euo pipefail
export LC_ALL=C
umask 077

alias_name=${1:?host alias required}
output=${2:?output HTML path required}
[[ $alias_name =~ ^[A-Za-z][A-Za-z0-9_-]{0,63}$ ]] || exit 2

escape_html() {
    sed -e 's/\&/\&amp;/g' -e 's/</\&lt;/g' -e 's/>/\&gt;/g'
}

cpu_snapshot() {
    # Ignore guest/guest_nice, already counted in user/nice.
    awk '/^cpu / {total=0; for(i=2;i<=9;i++) total+=$i; print total, $5+$6; exit}' /proc/stat
}

cpu=UNKNOWN
if before=$(cpu_snapshot) && sleep 1 && after=$(cpu_snapshot); then
    cpu=$(awk -v before="$before" -v after="$after" 'BEGIN {
        split(before,a); split(after,b); total=b[1]-a[1]; idle=b[2]-a[2];
        if(total>0 && idle>=0 && idle<=total) printf "%.1f",100*(total-idle)/total;
        else printf "UNKNOWN"
    }')
fi
memory=$(awk '/^MemTotal:/ {total=$2} /^MemAvailable:/ {available=$2; found=1}
    END {if(total>0 && found) printf "%.1f",100*(total-available)/total; else printf "UNKNOWN"}' /proc/meminfo) || memory=UNKNOWN
disks=$(df -Pk 2>/dev/null) || disks=UNKNOWN
zombies=$(ps -eo stat= 2>/dev/null | awk '$1 ~ /^Z/ {count++} END {print count+0}') || zombies=UNKNOWN
connections=UNKNOWN
if command -v ss >/dev/null 2>&1; then
    connections=$(ss -Htan state established 2>/dev/null | awk 'END {print NR}') || connections=UNKNOWN
fi

{
    printf '<!doctype html>\n<html lang="zh-CN"><head><meta charset="utf-8"><title>系统巡检报告</title></head><body>\n'
    printf '<h1>系统巡检报告</h1>\n<h2>系统信息</h2><pre>主机标识：%s\n巡检时间：%s\n数据来源：authorized</pre>\n' "$alias_name" "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
    printf '<h2>配置信息</h2><pre>内存使用率：%s%%</pre>\n' "$memory"
    printf '<h2>系统资源巡检区</h2><pre>CPU使用率：%s%%\n系统当前僵尸进程数：%s\n系统 established socket数量：%s\n' "$cpu" "$zombies" "$connections"
    printf '系统磁盘分区存储使用情况：\n'
    printf '%s\n' "$disks" | escape_html
    printf '系统磁盘分区结束</pre>\n'
    printf '<h2>人工复核</h2><pre>账户、登录记录、计划任务、进程明细、防火墙、时间同步与业务可用性需人工核对。</pre>\n'
    printf '</body></html>\n'
} > "$output"
