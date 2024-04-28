def read_send_log(file_path):
    with open(file_path, 'r') as file:
        print(file)
        lines = file.readlines()
    send_file_name = lines[0].split(':')[1].strip()
    begin_time = float(lines[1].split('=')[1])
    finish_time = float(lines[-1].split('=')[1])
    total_duration = finish_time - begin_time

    pdus = []
    for line in lines[2:-1]:
        parts = line.strip().split(',')
        if len(parts) > 1:
            pdu_info = {
                'pdu_to_send': int(parts[1].split('=')[1]),
                'status': parts[2].split('=')[1],
                'ackedNo': int(parts[3].split('=')[1])
            }
            pdus.append(pdu_info)
    return pdus,total_duration, send_file_name


def analyze_send_pdus(pdus):
    total_pdus = int(pdus[-1]['pdu_to_send'])
    total_transmissions = 0
    total_timeouts = 0


    for pdu in pdus:
        total_transmissions += 1
        if pdu['status'] == 'TO':
            total_timeouts += 1


    return {
        '总帧数': total_pdus,
        '总传输次数': total_transmissions,
        '总超时数': total_timeouts,
        '帧有效率' : total_pdus/total_transmissions
    }


def read_receive_log(file_path):
    with open(file_path, 'r') as file:
        lines = file.readlines()

    # 解析接收文件名和时间
    receive_file_name = lines[0].split(':')[1].strip()
    begin_time = float(lines[1].split('=')[1])
    end_time = float(lines[-1].split('=')[1])
    total_duration = end_time - begin_time

    pdus = []
    for line in lines[2:-1]:  # 排除前两行和最后一行
        parts = line.strip().split(',')
        if len(parts) > 2:
            pdu_info = {
                'pdu_exp': int(parts[1].split('=')[1]),
                'pdu_recv': int(parts[2].split('=')[1]),
                'status': parts[3].split('=')[1]
            }
            pdus.append(pdu_info)
    return pdus, total_duration, receive_file_name


def analyze_received_pdus(pdus):
    total_pdus = int(pdus[-1]['pdu_exp'])
    total_transmissions = 0
    errors = 0
    out_of_order = 0
    last_received = -1

    for pdu in pdus:
        total_transmissions += 1
        if pdu['status'] != 'OK':
            errors += 1
        if pdu['pdu_recv'] <= last_received:
            out_of_order += 1
        last_received = pdu['pdu_recv']

    efficiency = (total_pdus+1) / total_transmissions if total_pdus > 0 else 0

    return {
        'Total PDUs Received': total_pdus,
        '错误总数': errors,
        '错误的帧总数': out_of_order,
        '帧有效率': efficiency
    }

def main():
    log_path = input(f"请输入要查看的文件日志名称")
    #log_path = './Client/1.jpg_send_log.txt'
    if 'send_log' in log_path:
        pdus, total_duration, send_file_name = read_send_log(log_path)
        analysis = analyze_send_pdus(pdus)
        analysis['发送时间 (秒)'] = total_duration
        analysis['文件名'] = send_file_name
        print("你要查看的是发送日志")
        for key in analysis:
            print(key,":",analysis[key])
    elif 'receive_log' in log_path:
        pdus, total_duration, receive_file_name = read_receive_log(log_path)
        analysis = analyze_received_pdus(pdus)
        analysis['发送时间 (秒)'] = total_duration
        analysis['文件名'] = receive_file_name
        print("你要查看的是接收日志")
        for key in analysis:
            print(key,":",analysis[key])




if __name__ == "__main__":
    main()
