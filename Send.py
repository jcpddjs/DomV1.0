import socket
import struct
import random
import numpy as np
from threading import Thread
from datetime import datetime
import threading


# 加载数据
x_test = np.load('Datasets/testData_xyz_1024_C3_del44_n20000.npy')

class SendDataThread(Thread):
    def __init__(self):
        Thread.__init__(self)


    def run(self):
        try:
            client = socket.socket()
            host = '127.0.0.1'
            port = 8888
            client.connect((host, port))

            index = 0
            while True:
                # 每0.5秒发送一个点的数据  以此来模拟数据生成
                for a in range(20000):
                    # print('第',a,'组数据')
                    # 给服务端发送本次发送数据的字节大小
                    client.send(str(len(x_test[a].tobytes())).encode('utf-8'))
                    # print(len(x_test[index].tobytes()))
                    # 服务端接收到后，回复，若无回复就阻塞
                    be = client.recv(1024).decode()
                    index += 1
                        # print(be)
                    # print('第', a, '个数据')
                    for b in range(1024) :
                        # print('第', b, '个数据')
                        arr = x_test[a][b]
                        # print('arr.shape', arr.shape)
                        data = arr.tobytes()
                        # print(type(arr))

                        client.send(data)

                        # 休眠0.001s
                        for k in range(19800):
                            x = k
        # client.close()
        except Exception:
            client.close()


def SendSocket(flag_is_data,client, data):
    try:
        if flag_is_data == 0:

            client.send('0'.encode('utf-8'))

        else:
            client.send('1'.encode('utf-8'))
        # 先发送字节大小,等待接收端确认
        client.send(str(len(data)).encode())

        # 接收接收端的确认信息，否则阻塞
        client.recv(1024)

        # 创建时间对象
        nowtime = datetime.now()
        # 获取当前时间的小时
        hours = nowtime.hour
        # 获取分钟
        min = nowtime.minute
        # 获取秒数
        s = nowtime.second
        # 秒数的微秒部分，取值范围为 0 到 999999。
        us = nowtime.microsecond
        # 将所有时间转为ms级
        time_send = hours * 60 * 60 * 1000 + min * 60 * 1000 + s * 1000 + us / 1000
        # 取后两位小数
        # time_send=round(time_send, 2)
        # 发送接收到的数据
        client.sendall(data)

        # 接收接收端的确认信息，否则阻塞
        client.recv(1024)

        # 将时间的float数据转为bytes
        bytes_value = struct.pack('d', time_send)
        # 发送数据发送时间
        client.send(bytes_value)
    except Exception:
        print('数据发送异常')
        client.close()


class UpdateThread_send(threading.Thread):
    def __init__(self):
        threading.Thread.__init__(self)

        self.running = threading.Event()

    def run(self):
        # 创建计数器
        count = 0
        index = 0
        server = socket.socket()
        host = '127.0.0.1'
        port = 8888
        server.bind((host, port))
        server.listen(5)
        Thread1=SendDataThread()
        Thread1.start()
        client, addr = server.accept()
        # 与接收端建立连接
        send_soccket = socket.socket()
        send_soccket.connect(('127.0.0.1', 9999))
        # 创建一个大小为1024空的numpy数组，用于存储numpy.float64数据
        my_array = np.empty(1024)
        # 产生长度为100的数组内为0到1000不重复的随机数
        random_numbers = random.sample(range(1000), 100)
        # 从小到大排序
        random_numbers = sorted(random_numbers)

        while self.running.is_set():
            # 接收客户端发送来的数据字节大小
            data_size = int(client.recv(1024).decode())
            # print("data_size", data_size)
            # 回复客户端
            client.send('服务端开始接收'.encode('utf-8'))
            total_data_bytes = bytes()
            flag_is_data = 1
            while True :
                # 接收数据入队
                data=client.recv(8)
                np_data = np.frombuffer(data, dtype=np.float64)
                new_list = np_data.tolist()

                # print(type(np_data[0]))
                # my_array[count]=np_data[0]

                # count += 1
                total_data_bytes += data
                # 打包一个波形，发送给接收端
                if len(total_data_bytes)==data_size:
                    # print(my_array)
                    # total_data_bytes=my_array.tobytes()
                    # 此时为idling包
                    if random_numbers[index] == count:
                        flag_is_data = 0
                        index += 1

                    #  将接收到的数据发送给接收端
                    SendSocket(flag_is_data,send_soccket,total_data_bytes)
                    if count >= 1000:
                        count = 0
                        index = 0
                        # 产生长度为100的数组内为0到1000不重复的随机数
                        random_numbers = random.sample(range(1000), 100)
                        # 从小到大排序
                        random_numbers = sorted(random_numbers)

                    count += 1
                    break



if __name__ == '__main__':
    update_thread = UpdateThread_send()
    update_thread.running.set()
    update_thread.start()
