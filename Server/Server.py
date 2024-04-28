import socket
import yaml
import threading
from time import sleep
from time import time
import binascii
import re
import msvcrt
from sys import exit
import random

# 设置窗口大小和超时时间
SWSize = 4
TIMEOUT = 2  # 1 second timeout
acked = {}
sleep_time = 0
offLine = False
mode = 0
DataSize = 1024
ErrorRate = 10
LostRate = 10
lost, err, correct = 0,0,0

def Send(packet):
    global lost,err,correct
    if mode == 0:
        s.sendto(packet, (target_host, target_port))
        return
    if 1.0/LostRate > random.random():
        print(f"模拟丢失")
        lost = lost + 1
        return
    header = packet[:23]
    data = packet[24:]
    if 1.0/ErrorRate > random.random():
        data = b'this is a wrong messages'
        packet = header + data
        print(f"模拟错误")
        err = err + 1
        s.sendto(packet,(target_host,target_port))
        return
    else:
        s.sendto(packet, (target_host, target_port))
        correct = correct + 1
        print(f"正确发送")

def Debugging_Print(str):
    # print(str)
    return

def send_file():
    global lost,err,correct
    file_path = input('请输入你要传输的文件：')
    # file_path = "1.jpg"
    file_name = file_path.split('/')[-1]  # 获取文件名
    if file_name == '':
        print("文件名为空，请重新输入")
        return
    try:
        f = open(file_path,'r')
    except  FileNotFoundError:
        print("文件不存在，请确认后重新输入文件名")
        return
    lost, err, correct = 0, 0, 0
    send_log_file = open(f"{file_name}_send_log.txt",'w')
    send_log_file.write(f"SEND_FILE_NAME:{file_name}\n")
    begin_send_time = time()
    send_log_file.write(f"begin_send_time={begin_send_time}\n")
    print(f"开始发送文件{file_name}")
    s.sendto(f"filename:{file_name}".encode(), (target_host, target_port))
    sleep(sleep_time)

    base = 0
    next_seq_num = 0
    send_num = 0
    window = {}
    acked.clear()

    with open(file_path, 'rb') as file:
        while True:
            # Send all packets in the window
            while next_seq_num < base + SWSize and (data := file.read(1024)):
                crc = binascii.crc_hqx(data, 0xffff)  # Calculate CRC-16/CCITT-FALSE
                header = f"{next_seq_num:016d}:{crc:05d}:".encode()
                packet = header + data
                Send(packet)
                send_num = send_num + 1
                send_log_file.write(f"{send_num},pdu_to_send={next_seq_num},status=New,ackedNo={base}\n")
                sleep(sleep_time)
                window[next_seq_num] = (packet, time())  # Store packet and timestamp
                next_seq_num += 1

            # Check for timeouts
            current_time = time()
            for seq_num in list(window):
                packet_data, timestamp = window[seq_num]
                if current_time - timestamp > TIMEOUT:
                    if offLine:
                        print(f"按任意键退出")
                        msvcrt.getch()
                        print(f"已退出")
                        exit(0)
                    print(f"Timeout, resending: {seq_num}")
                    Send(packet_data)
                    send_num = send_num + 1
                    send_log_file.write(f"{send_num},pdu_to_send={next_seq_num},status=TO,ackedNo={base}\n")
                    sleep(sleep_time)
                    window[seq_num] = (packet_data, current_time)  # Update timestamp

            # Move the base up if packets are acknowledged
            while base in acked:
                del window[base]
                Debugging_Print(f"删除window[{base}]")
                base += 1

            if base == next_seq_num and not data:
                break  # All packets sent and acknowledged

    s.sendto(b"EOFEOFEOFEOFEOFEOFEOFEOF", (target_host, target_port))

    # Ensure that the EOF packet is acknowledged
    while True:
        if base in acked:
            break
        sleep(sleep_time)
    print(f"发送文件结束")
    send_log_file.write(f"finish_send_time={time()}\n")
    send_log_file.close()
    if mode == 1:
        print(f"发送丢失:{lost},发送错误{err},正确发送{correct}")


def receive_file():
    global offLine, receive_log_file
    expected_seq_num = 0
    receive_num = 0
    begin_receice_time = 0
    file = None

    def is_utf8(data):
        try:
            # 尝试解码为UTF-8，如果成功则返回True
            data.decode('utf-8')
            return True
        except UnicodeDecodeError:
            # 解码失败则不是UTF-8编码
            return False

    while True:
        try:
            packet, addr = s.recvfrom(4096)
        except ConnectionResetError:
            print(f"对方不在线，请检查对方在线后再进行尝试")
            offLine = True
            exit(0)



        payload = 0
        received_crc = 0
        seq_num = 0
        last_ack_sent = -1


        if(is_utf8(packet) == False):
            test1 = packet[:16]
            test2 = packet[17:22]
            test3 = packet[23:]
            seq_num = int(test1.decode())
            received_crc = int(test2.decode())
            payload = test3

        else:
            data = packet.decode()

            if "ACK:" in data:
                ack_num = int(data.split(':')[1])
                acked[ack_num] = True
                Debugging_Print(f"ACK:{ack_num},我方发送的包收到了对方的ACK回复")
                continue

            Debugging_Print(packet)
            Debugging_Print(data)

            if data.startswith('filename:'):
                expected_seq_num = 0
                receive_num = 0
                filename = data.split(':')[1]
                #filename = filename.split('.')[0] + "-copy." + filename.split('.')[1]
                file = open(filename, 'wb')
                receive_log_file = open(f"{filename}_receive_log.txt",'w')
                receive_log_file.write(f"RECEIVE_FILE_NAME:{filename}\n")
                begin_receice_time = time()
                receive_log_file.write(f"begin_receive_time={begin_receice_time}\n")
                print(f"\n正在接收对方文件{filename}")
                continue

            if data == "EOFEOFEOFEOFEOFEOFEOFEOF":
                if file:
                    file.close()
                if receive_log_file:
                    end_receive_time = time()
                    receive_log_file.write(f"end_receive_time={end_receive_time}\n")
                    receive_log_file.close()
                s.sendto(f"ACK:{expected_seq_num}".encode(), addr)
                print(f"\n接收完毕对方发送来的{file.name}")
                continue
            first_double_colon_index = packet.find(b":")
            second_double_colon_index = packet.find(b":", first_double_colon_index + 1)
            seq_num = packet[:first_double_colon_index]
            received_crc = packet[first_double_colon_index+1:second_double_colon_index].decode()
            payload = packet[second_double_colon_index+1:]
            seq_num = int(seq_num)
            received_crc = int(received_crc)
            Debugging_Print(seq_num)
            Debugging_Print(received_crc)
        # Calculate CRC of the received data to check integrity
        receive_num = receive_num + 1
        calculated_crc = binascii.crc_hqx(payload, 0xffff)
        last_ack_time = 0
        if calculated_crc != received_crc:
            receive_log_file.write(f"{receive_num},pdu_exp={expected_seq_num},pdu_recv={seq_num},status=DataErr\n")
        if seq_num != expected_seq_num:
            receive_log_file.write(f"{receive_num},pdu_exp={expected_seq_num},pdu_recv={seq_num},status=NoErr\n")
        if calculated_crc == received_crc and seq_num == expected_seq_num:
            if file:
                file.write(payload)
                receive_log_file.write(f"{receive_num},pdu_exp={expected_seq_num},pdu_recv={seq_num},status=OK\n")
            expected_seq_num += 1
            if expected_seq_num > last_ack_sent:
                s.sendto(f"ACK:{seq_num}".encode(), addr)
                last_ack_sent = seq_num
                last_ack_time = time()
            # print(f"packet {expected_seq_num} has been received")
            # print(f'payload:{payload}')
        elif time() - last_ack_time > TIMEOUT:
            # 如果超过了超时时间还没有收到新的数据包，重新发送上一个ACK
            s.sendto(f"ACK:{last_ack_sent}".encode(), addr)
            last_ack_time = time()
        else:
            Debugging_Print("transmission fault")
            Debugging_Print(f"seq_num:{seq_num}")
            Debugging_Print(f"expected_seq_num:{expected_seq_num}")
            Debugging_Print(f"received_crc:{received_crc}")
            Debugging_Print(f"calculated_crc:{calculated_crc}")
            Debugging_Print(f'payload:{payload}')
            # Send ACK for the last received in-order packet
            s.sendto(f"ACK:{expected_seq_num - 1}".encode(), addr)



if __name__ == "__main__":
    def is_valid_ipv4(ip) -> bool:
        pattern = r'^((25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$'
        if re.match(pattern, ip):
            return True
        return False
    def change_host(host,strs) -> str:
        choice = input(f"你是否要更改绑定的{strs}host:[y/n(default)]")
        if choice == 'y' or choice == 'Y':
            host_ = input(f"请输入{strs}host:")
            if(is_valid_ipv4(host_)):
                return host_
            else:
                print(f"你输入的地址格式有误！")
                change_host(host,strs)
        elif choice == 'n' or choice == 'N' or choice == '':
            return host
        else:
            print(f"请输入y或n")
            change_host(host,strs)
    def change_port(port,strs) -> int:
        choice = input(f"你是否要更改绑定的{strs}port:[y/n(default)]")
        if choice == 'y' or choice == 'Y':
            port_ = int(input(f"请输入{strs}port:"))
            if 0 <= port_ <= 65535:
                return port_
            else:
                print(f"你输入的端口格式有误！")
                change_port(port,strs)
        elif choice == 'n' or choice == 'N' or choice == '':
            return port
        else:
            print(f"请输入y或n或直接回车默认n")
            change_port(port,strs)
    def change_config(host=None, port=None, target_host=None, target_port=None):
        choice = input(f"是否要修改相关配置:[y/n(default)]")
        if choice == 'y' or choice == 'Y':
            host = change_host(host,"本机")
            port = change_port(port,"本机")
            target_host = change_host(target_host,"目标")
            target_port = change_port(target_port,"目标")
            return host, port, target_host, target_port
        elif choice == 'n' or choice == 'N' or choice == '':
            return host, port, target_host, target_port
        else:
            print(f"请输入y或n或直接回车默认n")
            change_config(host,port,target_host,target_port)

    # 创建 socket 对象
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    mode_ = input(f"输入1进入测试模式，包含模拟错误、模拟丢失，其他进入正常传输模式")

    if mode_ == '1':
        print("进入测试模式，发送文件时会出现模拟错误和发包丢失问题")
        mode = 1
    # 读取配置文件
    try:
        # 读取配置文件
        with open("configuration.yaml", 'r') as config_file:
            config = yaml.safe_load(config_file)

        try:
            host = config["Server"]["Host"]
            port = config["Server"]["Port"]
            target_host = config["Client"]["Host"]
            target_port = config["Client"]["Port"]
            host, port, target_host, target_port = change_config(host, port, target_host, target_port)
            DataSize = config["DataSize"]
            if mode == 1:
                ErrorRate = config["ErrorRate"]
                LostRate = config["LostRate"]
            SWSize = config["SWSize"]
            TIMEOUT = config["Timeout"]
        except KeyError:
            print("配置文件中格式错误，请检查配置文件格式")
            exit(0)
    #如果发现没有配置文件
    except FileNotFoundError:
        print("configuration.yaml配置文件缺失\n"
              "请将该文件放入与该程序相同的文件夹中并重启程序，或者手动输入参数")
        while 1:
            host = input(f"请输入本机Host:")
            if is_valid_ipv4(host):
                break
            else:
                print(f"Host输入有误，请重新输入")
        while 1:
            port = int(input(f"请输入本机Port:"))
            if 0 <= port <= 65535:
                break
            else:
                print(f"Port输入有误，请重新输入")
        while 1:
            target_host = input(f"请输入对方Host:")
            if is_valid_ipv4(target_host):
                break
            else:
                print(f"Host输入有误，请重新输入")
        while 1:
            target_port = int(input(f"请输入对方Port:"))
            if 0 <= target_port <= 65535:
                break
            else:
                print(f"Port输入有误，请重新输入")
        while 1:
            DataSize = int(input(f"请输入DataSize:"))
            if 100<=DataSize<=2048:
                break
            else:
                print(f"DataSize应该在100到2048之间，请重新输入")
        while 1:
            SWSize = int(input(f"请输入窗口大小:"))
            if 1<=SWSize<=10:
                break
            else:
                print(f"SWSize应该在1到10之间，请重新输入")
        while 1:
            TIMEOUT = float(input(f"请输入超时重发的时间(ms):"))
            if 0<=TIMEOUT<=10000:
                break
            else:
                print(f"Timeout应该在0到10000(ms)之间，可以是小数，请重新输入")
        if mode == 1:
            while 1:
                ErrorRate = int(input(f"请输入每多少帧错误一帧（输入整数）"))
                if 1<ErrorRate:
                    break
                else:
                    print(f"输入的帧应该大于1帧")
            while 1:
                LostRate = int(input(f"请输入每多少帧丢失一帧（输入整数）"))
                if 1<LostRate:
                    break
                else:
                    print(f"输入的帧应该大于1帧")




    print(f"你绑定的host为:{host}, 绑定的port为:{port}")
    print(f"你的目标host为:{target_host}，目标的port为:{target_port}")
    print(f"你输入的DataSize为:{DataSize}")
    print(f"你输入的SWSize为:{SWSize}")
    TIMEOUT = TIMEOUT / 1000.0
    print(f"你输入的TIMEOUT为:{TIMEOUT}(s)")
    if mode == 1:
        print(f"你输入的ErrorRate为:{ErrorRate}")
        print(f"你输入的LostRate为:{LostRate}")

    port = int(port)
    target_port = int(target_port)


    # 绑定服务器端地址和端口
    s.bind((host, port))
    print(f"当前程序已上线")

    threading.Thread(target=receive_file).start()
    #threading.Thread(target=send_file).start()
    while 1:
        send_file()


