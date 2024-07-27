import queue
import numpy as np
import sqlite3
from flask import Flask, render_template
from flask_socketio import SocketIO, emit
from UpdateThread import UpdateThread

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key'  # 设置 Flask 应用程序的密钥
socketio = SocketIO(app)

# 创建数据队列
data_queue = queue.Queue()
# 创建列表名队列
list_name_queue=queue.Queue()
# 创建时延队列
delay_queue = queue.Queue()
delay_t_queue = queue.Queue()
update_thread = UpdateThread(data_queue,list_name_queue,delay_queue,delay_t_queue)
update_thread.running.set()
update_thread.start()

@app.route('/')
def index():
    return render_template('MainView.html')

# 当服务器与前端连接成功时，执行handle_connect函数
@socketio.on('connect',namespace='/chart')
def handle_connect():
    global main_value
    print('Client connected successfully')
    # 设置x的值0~1023
    x_data = list(range(1024))
    # 获取更新数据线程中的新数据
    y_data = data_queue.get()
    # 获取时延
    delay = delay_queue.get()

    delay_t = delay_t_queue.get()
    # 将list转换为numpy，进行傅里叶变换
    y_fft = np.fft.fft(y_data)
    #对傅里叶变换后的复数进行取绝对值
    y_abs = np.abs(y_fft)
    # 将数据进行处理变成[[0,0,y_data],[]]的格式以便绘制2D图
    data_2D = []
    count = 0
    for x in range(32):
        for y in range(32):
            data_2D.append([x, y, y_data[count]])
            count += 1
    # 将傅里叶变换后的numpy转换为list，以便发送给前端
    data_Y = y_abs.tolist()
    # 将傅里叶变换后的numpy转换为list，以便发送给前端
    data_Y = y_abs.tolist()
    y_max = max(y_data)
    y_min = min(y_data)
    # 将x_test[0]的1024个点发送给前端
    emit('update_data',{'x_data': x_data, 'y_data': y_data,'data_Y':data_Y,'data_2D':data_2D,'max_hot':y_max,'min_hot':y_min,'data_delay':delay_t})

@socketio.on('request_update', namespace='/chart')
def request_update():
    # 生成x轴的数据
    x_data = list(range(1024))
    # 获取更新数据线程中的新数据
    y_data = data_queue.get()
    # 获取时延
    delay = delay_queue.get()
    delay_t = delay_t_queue.get()
    # time.sleep(1)
    # 将list转换为numpy，进行傅里叶变换
    y_fft = np.fft.fft(y_data)
    #对傅里叶变换后的复数进行取绝对值
    y_abs = np.abs(y_fft)
    # 将数据进行处理变成[[0,0,y_data],[]]的格式以便绘制2D图
    data_2D = []
    count = 0
    for x in range(32):
        for y in range(32):
            data_2D.append([x, y, y_data[count]])
            count += 1
    # 将傅里叶变换后的numpy转换为list，以便发送给前端
    data_Y = y_abs.tolist()
    y_max = max(y_data)
    y_min = min(y_data)
    emit('update_data', {'x_data': x_data, 'y_data': y_data,'data_Y':data_Y,'data_2D':data_2D,'max_hot':y_max,'min_hot':y_min,'data_delay':delay,'data_t_delay':delay_t}, broadcast=True)

@socketio.on('getListUpdate',namespace='/chart')
def getListUpdate():
    #获取列表名
    list_name=list_name_queue.get()
    emit('update_list',{'list_name':list_name},broadcast=True)

@socketio.on('getSqliteData',namespace='/chart')
def getSqliteData(data):
    con=sqlite3.connect('database.db')
    cur=con.cursor()
    # 读取数据库的data1D列数据
    cur.execute(f"SELECT data1D FROM {data}")
    # table_data 为列表嵌套元组
    table_data=cur.fetchall()
    # 将list里的元组拆开
    table_data = [i[0] for i in table_data]
    table_data_FFT=np.fft.fft(table_data)
    table_data_abs=np.abs(table_data_FFT)
    list_Y_data=table_data_abs.tolist()
    x_data = list(range(1024))
    # 读取数据库的时延数据
    cur.execute(f"SELECT delay FROM {data} WHERE delay IS NOT NULL")
    delay_data=cur.fetchall()
    # 拆list套元组
    delay_data=delay_data[0][0]
    data_2D = []
    count = 0
    for x in range(32):
        for y in range(32):
            data_2D.append([x, y, table_data[count]])
            count += 1
    y_max = max(table_data)
    y_min = min(table_data)
    emit('sqlite_data',{'list_Y_data':table_data,'list_Y_FFT_data':list_Y_data,'x_list':x_data,"data_2D_history":data_2D,'y_max_history':y_max,'y_min_history':y_min,'delay_history':delay_data},broadcast=True)

if __name__ == '__main__':
    socketio.run(app,debug=True)
