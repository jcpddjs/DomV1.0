import socket
import struct
import threading
import sqlite3
from datetime import datetime
import numpy as np


class UpdateThread(threading.Thread):
    def __init__(self, data_queue,list_name_queue,delay_queue,delay_t_queue):
        threading.Thread.__init__(self)

        self.data_queue = data_queue
        self.list_name_queue = list_name_queue
        self.delay_queue = delay_queue
        self.delay_t_queue = delay_t_queue
        self.running = threading.Event()

    def run(self):
        server = socket.socket()
        client = socket.socket()
        # 与数据库建立连接
        con = sqlite3.connect("database.db")
        # 创建游标
        cur = con.cursor()
        try:
            host = '127.0.0.1'
            port = 9999
            server.bind((host, port))
            server.listen(5)
            client, addr = server.accept()

            while self.running.is_set():
                flag_is_data = int(client.recv(256).decode())
                # 接收客户端发送来的数据字节大小
                data_size = int(client.recv(1024).decode())
                # 回复客户端
                client.send('服务端开始接收'.encode('utf-8'))

                total_data = bytes()
                # 获取当前时间
                current_time = datetime.now()
                # 将当前时间作为表名+count
                table_name ="s"+current_time.strftime("%Y%m%d%H%M%S%f")[:-4]
                table_name_delay="delay"
                table_name_delay_t = "delay_t"
                cur.execute(f"CREATE TABLE IF NOT EXISTS {table_name}(id INTEGER PRIMARY KEY AUTOINCREMENT,data1D INTEGER,FFTreal REAL,FFTimag REAL,delay REAL)")
                cur.execute(f"CREATE TABLE IF NOT EXISTS {table_name_delay}(id INTEGER PRIMARY KEY AUTOINCREMENT,delay REAL)")
                cur.execute(
                    f"CREATE TABLE IF NOT EXISTS {table_name_delay_t}(id INTEGER PRIMARY KEY AUTOINCREMENT,delay REAL)")
                while True:
                    # 将收到的数据拼接起来    data_size
                    total_data += client.recv(data_size)

                    if len(total_data) == data_size:
                        # 获取接收完毕时间
                        # 创建时间对象`
                        nowtime = datetime.now()
                        break

                # 获取当前时间的小时
                hours = nowtime.hour
                # 获取分钟
                min = nowtime.minute
                # 获取秒数
                s = nowtime.second
                # 秒数的微秒部分，取值范围为 0 到 999999。
                us = nowtime.microsecond
                # 将所有时间转为ms级
                time_recv = hours * 60 * 60 * 1000 + min * 60 * 1000 + s * 1000 + us / 1000
                # 将bytes转为numpy
                arr = np.frombuffer(total_data, dtype=np.float64)
                arr_fft = np.fft.fft(arr)
                new_list = arr.tolist()

                # 数据接收完毕后，回复发送端，准备接收时间
                client.send('接收完毕'.encode('utf-8'))

                time_send_bytes=client.recv(1024)
                # 将发送时间的bytes转为float
                time_send = struct.unpack('d', time_send_bytes)[0]
                # 时延=time_send-time_rev
                delay=time_recv-time_send
                # 保留两位小数
                delay=round(delay,2)
                # print(delay)
                # 将数据入队
                self.data_queue.put(new_list)
                # 将时延入队
                self.delay_queue.put(delay)
                if flag_is_data == 0:
                    self.delay_t_queue.put(0.00)
                    cur.execute(f"INSERT INTO {table_name_delay_t} (delay) VALUES (0.00)")
                if flag_is_data == 1:
                    self.delay_t_queue.put(delay)
                    cur.execute(f"INSERT INTO {table_name_delay_t} (delay) VALUES ({delay})")
                # 将接收到的数据放入数据库,包含1d数据fft数据
                for i in range(1024):
                    cur.execute(f"INSERT INTO {table_name} (id,data1D,FFTreal,FFTimag) VALUES ({i},{arr[i]},{arr_fft[i].real},{arr_fft[i].imag})")
                # 将当前时延放入数据库
                cur.execute(f"UPDATE {table_name} SET delay={delay} WHERE id=0;")
                cur.execute(f"INSERT INTO {table_name_delay} (delay) VALUES ({delay})")

                con.commit()
                self.list_name_queue.put(table_name)
            # time.sleep(1)
        except sqlite3.Error :
            print("数据库异常，断开连接!!!!!!")
            cur.close()
            con.close()
        except Exception as e:
            print("接收数据异常，即将关闭连接!!!!!!!")
            cur.close()
            con.close()
            client.close()
            server.close()
