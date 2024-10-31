import paramiko
import os
import logging
from datetime import datetime
import time

# 账户列表，每个服务器的IP地址、用户名、密码
account_list = {
    '10.2.14.89':'root/n9pmlXmu26GBSXovAO5Y',
    '10.2.14.90':'root/R8KpnPThIjQYNSdZueMf',
    '10.2.14.91':'root/5mv1n18vh3LR5ORwie7q',
    '10.2.14.92':'root/wYucBE5ntVVj3iv3OQNy',
    '10.2.14.93':'root/VSgDLV8qSW3BK75takhq',
    '10.2.14.170':'root/EDW0f0u5n0oQtsAi7rfv',
    '10.2.14.157':'root/OFgoeUy1PLhX0qmXMFCr',
    '10.2.14.158':'root/LT14j8k6BaB6Kk4H15r8',
    '10.2.14.171':'root/FPfH9NOGVIlHP1vgoyhB',
    '10.2.14.172':'root/6DJNXfdz8d2bN8SJmbfV',
    '10.2.14.173':'root/0kfH5Jna1FuaPFqBXLlH',
    # '10.2.14.238':'root/jaTOZVO9dr4KoLN3',
    # '202.121.96.188':'root/Zo9kBckiUIQ6Uj4bToF7',
    '10.2.15.79':'mes/0TYfZtDQwrpeQnN4hNOT',
    '10.2.15.80':'mes/0TYfZtDQwrpeQnN4hNOT',
}

# 设置paramiko的日志级别为WARNING，隐藏调试信息
paramiko_logger = logging.getLogger("paramiko")
paramiko_logger.setLevel(logging.WARNING)

# 获取当前时间并格式化为文件夹名
current_time = datetime.now().strftime("%Y%m%d_%H%M%S")

# 获取当前工作目录，并创建一个以时间命名的文件夹
current_dir = os.getcwd()
save_folder = os.path.join(current_dir, current_time)
os.makedirs(save_folder, exist_ok=True)

# 设置日志文件的路径
log_file = os.path.join(save_folder, f"{current_time}.log")

# 配置日志记录，确保日志输出到文件和控制台，且文件以UTF-8编码
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# 创建日志文件处理器，保存为UTF-8编码
file_handler = logging.FileHandler(log_file, encoding='utf-8')
file_handler.setLevel(logging.INFO)

# 创建控制台处理器
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)

# 设置日志格式
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
file_handler.setFormatter(formatter)
console_handler.setFormatter(formatter)

# 将处理器添加到logger
logger.addHandler(file_handler)
logger.addHandler(console_handler)

# 函数：使用shell会话执行sudo su切换到root用户
def execute_command_with_sudo(ssh, user_password):
    shell = ssh.invoke_shell()
    time.sleep(1)

    # 发送 sudo su 命令
    shell.send("sudo su\n")
    time.sleep(1)

    # 循环等待并读取数据，直到我们捕获到密码提示
    output = ""
    while not output.strip().endswith("password for"):
        output = shell.recv(1024).decode('utf-8')
        if "password for" in output:
            # logger.info("Password prompt detected, sending password...")
            shell.send(user_password + "\n")
            break
        time.sleep(1)

    # 等待几秒钟，确保 sudo su 已经切换到 root 用户
    time.sleep(2)
    return shell

# 循环遍历每台服务器
for index in account_list:
    account = account_list[index].split('/')
    
    # IP、用户名、密码
    ip = index
    port = 22
    if 2 < len(account):
        port = account[2]
    user = account[0]
    password = account[1]

    logger.info(f"{ip} {user}")

    # 创建SSHClient实例对象
    ssh = paramiko.SSHClient()
    # 允许连接到不在本地known_hosts文件中的服务器
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    try:
        # 连接远程服务器
        ssh.connect(ip, port, user, password, timeout=10)

        if user != 'root':
            # 切换到 root 用户
            logger.info(f"Trying to switch to root on {ip} using sudo...")
            shell = execute_command_with_sudo(ssh, password)
            time.sleep(1)
            shell.send("whoami\n")  # 检查是否已经切换到 root
            time.sleep(1)
            output = shell.recv(1024).decode('utf-8')
            # logger.info(f"User after sudo su: {output}")
            
            # 运行需要的命令
            shell.send("sh /home/check/os_check_new.sh\n")
            time.sleep(5)  # 等待命令执行完毕
            output = shell.recv(5000).decode('utf-8')
            report_path = None
            for line in output.splitlines():
                if "巡检结束,html报告已生成:" in line:
                    report_path = line.split(":")[-1].strip()
            # print(report_path)
            save_path = report_path.replace('/home/check/','')
            # print(save_path)

        else:
            # 运行远程命令，假设要获取报告路径
            command = "sh /home/check/os_check_new.sh | awk '/巡检结束,html报告已生成:/{print substr($0, index($0, \":\")+1)}' | tail -n1"
            stdin, stdout, stderr = ssh.exec_command(command)

            # 获取报告路径
            report_path = stdout.read().decode().strip()
            # print(report_path)
            save_path = report_path.replace('/home/check/','')
            # print(save_path)
        if report_path:
            # 使用SFTP下载该文件
            with ssh.open_sftp() as sftp:
                local_file_path = os.path.join(save_folder, save_path)  # 本地保存路径
                sftp.get(report_path, local_file_path)
                logger.info(f"文件已下载到: {local_file_path}")
        else:
            logger.warning(f"{ip} 上没有生成报告文件")

    except Exception as e:
        logger.error(f"在连接 {ip} 时出错: {e}")

    finally:
        ssh.close()
        logger.info(f"关闭与 {ip} 的连接\n")