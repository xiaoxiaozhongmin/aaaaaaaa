#!/usr/bin/env python
#encoding: utf-8
import os
import logging
import time
import telnetlib
import socket
import fcntl, struct
import paramiko
import subprocess
import re
import config
import datetime
import requests
import databaseapi


# logging.basicConfig(level=logging.DEBUG,
#     format = '[%(asctime)s] %(levelname)s %(message)s',
#     datefmt = '%Y-%m-%d %H:%M:%S')
# root = logging.getLogger()
# root.setLevel(logging.NOTSET)
# 电源板子设计遗留问题，用整个list来进行转换
d16 = {
    1: 1,
    2: 9,
    3: 2,
    4: 10,
    5: 3,
    6: 11,
    7: 4,
    8: 12,
    9: 5,
    10: 13,
    11: 6,
    12: 14,
    13: 7,
    14: 15,
    15: 8,
    16: 16,
}
s8 = {
    1: 9,
    2: 10,
    3: 11,
    4: 12,
    5: 13,
    6: 14,
    7: 15,
    8: 16,
    9: 9,
    10: 9,
    11: 9,
    12: 9,
    13: 9,
    14: 9,
    15: 9,
    16: 9,
}
d28 = {
    1: 1,
    2: 15,
    3: 2,
    4: 16,
    5: 3,
    6: 17,
    7: 4,
    8: 18,
    9: 5,
    10: 19,
    11: 6,
    12: 20,
    13: 7,
    14: 21,
    15: 8,
    16: 22,
    17: 9,
    18: 23,
    19: 10,
    20: 24,
    21: 11,
    22: 25,
    23: 12,
    24: 26,
    25: 13,
    26: 27,
    27: 14,
    28: 28,
}


class SSHClient():
    # host='192.168.9.1', port=22, username="root", password='goodlife'
    def __init__(self, host, port=22, username="root", password='talkingdt'):
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.ssh = paramiko.SSHClient()         # 这行代码实现了ssh远程登陆服务器的执行命令和上传下载文件
        self.ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        self.recv_buff = 1024*1024*1024        # 应该是最大的返回量


    def connect(self):
        self.ssh.connect(hostname=self.host, port=self.port, username=self.username, password=self.password)
        self.chan = self.ssh.invoke_shell()       # 这个也是远程登陆服务器的一个实例方法
        time.sleep(0.1)
        self.banner = self.chan.recv(self.recv_buff)    # 这个不清楚

    def get_current_ssh_config(self):
        config = {}
        config["host"] = self.host
        config["port"] = self.port
        config["username"] = self.username
        config["password"] = self.password
        return config

    def get_banner(self):
        return self.banner

    def recv_timeout(self, size=1024*1024*1024, timeout=2):
        self.chan.setblocking(0)
        total_data = []; data = ''; begin=time.time()
        while 1:
            #if you got some data, then break after wait sec
            if total_data and time.time()-begin>timeout:
                break
            #if you got no data at all, wait a little longer
            elif time.time()-begin>timeout*2:
                break
            try:
                data=self.chan.recv(size)
                if data:
                    total_data.append(data)
                    begin=time.time()
                else:
                    time.sleep(0.1)
            except:
                pass
        return ''.join(total_data)

    def recv(self, size=1024*1024*1024):
        return self.chan.recv(size)

    def recv_expect(self, expect, timeout=5):
        buff = ""
        while expect not in buff:
            resp = ""
            try:
                resp = self.chan.recv(self.recv_buff)
            except socket.timeout, e:
                return False
            print "resp is ", str([resp])
            buff += resp
            time.sleep(0.3)
            timeout -= 1
            if timeout == 0:
                return False
        return buff

    def send(self, cmd, timeout=1):
        self.chan.send(cmd + "\n")
        time.sleep(timeout)
        return self.chan.recv(self.recv_buff)

    def send_only(self, cmd, timeout=1):
        self.chan.send(cmd + "\n")
        time.sleep(timeout)

    def close(self):
        self.ssh.close()

    def send_expect(self, cmd, expect, timeout=5):
        self.chan.send(cmd + "\n")
        buff = ""
        while expect not in buff:
            resp = ""
            try:
                resp = self.recv_timeout(self.recv_buff)
            except socket.timeout, e:
                return False
            buff += resp
            time.sleep(0.5)
            timeout -= 1
            if timeout == 0:
                return False
        return buff
    
class SystemF(object):
    """
    设备类封装
    """
    def __init__(self, action, mode="2G"):
        # 初始化设置：必须携带device_type, ste
        if "-WAN" in action.device_type:
            action.device_type=action.device_type.replace('-WAN','')
        self.device_type = action.device_type      # device_type是一个字符串，包含有设备信息的字符串。

        """设备所包含的属性有
        1.self.device_type = action.device_type
        2.self.mode = mode|action.device_type
        3.self.step = action.step
        4.self.sendkey = 942-2bb5678e68ea85bc7dc76752cf43334a
        5.self.mem = 内存大小，依据的是action.device_type
        6.self.count_to_power_port, 测试时控制路由器的电源板的类型
        7.self.connect_type = ssh|telent, 也是根据设备的型号来区分的
        8.self.device_ip    为第三代设备添加设备IP
            self.b2b = ['GL-B1300-5G']
            self.t2g = ['GL-MT300N-V2', 'GL-MT300A', 'GL-MT300N']
            self.t2u = ['GL-AR300M-Lite', 'GL-AR150', 'GL-AR300M', 'GL-MIFI', 'GL-AR750', 'GL-AR750-5G', 'GL-B1300']
            self.device_iperf 二进制文件名，东明，这个基本不用更改。
        9.在第二步测试时，需要一些特殊的参数的参数
            self.mac_address = action.mac_address
            self.sn_now_use = action.sn_now_use
            self.sn_back_up = action.sn_back_up
            self.ddns_name = action.ddns_name
        1
        self.device_ip   为第一步，第二步设置IP
        11.self.lan_ip      获取设备的lan_ip
        12.self.ping_start  表示设备是否被ping通     
        """
        """
        1.这个device_type具体是什么东西，在产品名中叫modle
        带有5G代表双频，2G是单频路由器
        """
        if "5G" in self.device_type:
            print 6
            self.mode = "5G"
        else:
            self.mode = mode
        self.step = action.step
        """
        2.这个step应该是检测执行到了哪一步
        第一步，是pcba测试，是测试独立的板子
        第二步，是产品测试，带壳测试，检测壳是否有影响
        第三部，吞吐量，测试里面的带宽，数据转换效率。
        """
        self.sendkey = "942-2bb5678e68ea85bc7dc76752cf43334a"
        self.setMem()                           # 执行这个函数，添加相应的属性

        """
        4.设置控制电源板的类型,是什么东西
        给路由器充电的电源类型，需要清楚电源控制表的写法
        """
        #  设置控制电源板的类型
        if config.ways == 's8':
            self.count_to_power_port = s8       # 电源的端口
        if config.ways == 'd16':
            self.count_to_power_port = d16
        if config.ways == 'd28':
            self.count_to_power_port = d28

        if self.step == 'third':       # 如果是吞吐量测试，则进行这个步骤
            # 设置设备登陆的方式ssh or telnet
            self.setConnect_type()
            # 设置设备的ip地址
            self.device_ip = '192.168.8.1'        # 为其添加了很多的设备相关的信息
            # 使用b1300对跑udp
            self.b2b = ['GL-B1300-5G','GL-S1300-5G']
            # 使用tp link网卡跑tcp方式
            self.t2g = ['GL-MT300N-V2','GL-MT300N-V3', 'GL-MT300A', 'GL-MT300N', 'GL-MT300A-ssh']
            # 使用tplink网卡跑udp方式
            self.t2u = ['GL-AR300M-Lite-ssh','GL-AR300M','GL-AR300M-ssh', 'GL-AR150', 'GL-AR300M-telnet', 'GL-MIFI', 'GL-AR750', 'GL-AR750-5G', 'GL-B1300','GL-AR300M-double-flash','GL-X750',"X750",'GL-S1300','GL-X750-Transidea-SpA','GL-X750-ble']
            # 设置iperf的类型
            self.device_iperf = self.set_iperf()       # 为其添加这个属性

            if self.device_type in self.b2b:
                self.ssh = SSHClient(host='192.168.9.1', port=22, username="root", password='goodlife')
                self.ssh.connect()
                self.dssh = SSHClient(host='192.168.9.1', port=22, username="root", password='goodlife')
                self.dssh.connect()

        else:
            # 在进行第二步测试时，还需要携带mac_address, sn_now_use, sn_back_up, ddns_name
            if self.step == "second":
                self.mac_address = action.mac_address
                if self.device_type in ['GL-CORE', "GL-MT300N-V2", 'GL-MT300N-V2-xinjia', 'GL-CORE-Wiline']:
                    databaseapi.updatat_mark3_used(self.mac_address)
                if self.device_type in ['GL-X750', "GL-X1200", "GL-S1300", 'GL-AR750S', 'X750','GL-X750-Transidea-SpA','GL-X750-ble']:
                    databaseapi.updatat_mark4_used(self.mac_address)
                self.sn_now_use = action.sn_now_use
                self.sn_back_up = action.sn_back_up
                self.ddns_name = action.ddns_name
                if self.device_type=='GL-avira':
                    self.serial=action.serial
                    self.ssid1=action.ssid
                    self.key=action.key
                    print('serial is' + self.serial + 'ssid1 ' + self.ssid1 + 'key is' + self.key)
                print('mac is'+self.mac_address+'sn2 is'+self.sn_now_use+'sn1 is'+self.sn_back_up+'ddns '+self.ddns_name)
                # 用来保存第二步测试失败的log文件夹
                path = "/home/pi/log"
                isExists = os.path.exists(path)
                if not isExists:
                    os.makedirs(path)
                try:
                    self.filename=path+"/"+self.mac_address
                    self.filelog=open(self.filename,'a',buffering=0)
                except:
                    pass
            self.device_ip = self.get_ip()
            if self.wait_ping_ip_start() is False:         # 这个是树莓派直接去ping路由器设备，根据ping的结果来返回是否连接成功
                self.ping_start = False
            else:
                self.ping_start = True

    #用来将第二步测试过程执行的命令写入到文件的方法
    def log_info(self,info):
        if self.step == "second":
            try:
                print("log_info", info)
                info1=info+'\n'
                self.filelog.write(info1)
            except:
                pass

    #第二步测试成功后，删除测试log文件，失败则保留
    def rm_log(self):
        if self.step == "second":
            try:
                print('shanchu')
                self.filelog.close()
                os.remove(self.filename)
            except:
                self.log_info("删除失败")
                pass

    # 通知:可以使用wechat，进行通知
    def notify(self, text, desp):
        url = "https://pushbear.ftqq.com/sub?sendkey={}&text={}&desp={}".format(self.sendkey,text, desp)
        res = requests.get(url)
        # logging.info(res)

    # 获取不同网卡的ip信息
    # self.get_inet_ip('wlan0')
    def get_inet_ip(self, ifname):
        time_out = 5
        cmd = "ifconfig {}".format(ifname)+"|grep 192.168|awk '{print $2}'"     # 这句代码的意思是获取到ifname这个名字的ip地址
        while time_out:
            ip = os.popen(cmd).read().replace("\n", " ").strip(" ").split(" ")[0]  #
            if '192.168' not in ip:
                time_out-=1
                time.sleep(2)
            else:
                return ip
        return ip
    # 设置内存大小参数
    """
    3.这里面的设备的型号必须要弄清楚，以及赋值的意思也需要弄清楚了
    mem、磁盘大小
    """
    def setMem(self):
        if self.device_type in ['GL-AR150', 'GL-CORE', 'GL-USB150', 'GL-MIFI', 'GL-ENGEL', 'GL-MT300A','GL-CORE-Wiline']:
            self.mem = 64*1024*0.7
        elif self.device_type in ['GL-X1200','GL-AR300M', 'GL-AR300M-Lite', 'GL-AR300M-16', 'GL-AR750', 'GL-AR750S', 'GL-AR750-5G', 'GL-MT300N', 'GL-MT300N-V2','GL-MT300N-V2-xinjia', 'GL-MT300N-V3','GL-AR300M-double-flash','GL-X750',"X750",'GL-AR750S-Internet-Switch','GL-X750-Transidea-SpA','GL-X750-ble']:
            self.mem = 128*1024*0.7
        elif self.device_type in ['GL-B1300', 'GL-B1300-5G','GL-B1300']:
            self.mem = 256*1024*0.7
        elif self.device_type in ["GL-S1300",'GL-avira']:
            self.mem = 512 * 1024 * 0.7

    def command(self, cmd, timeout=60):
        self.log_info(cmd)
        """执行命令cmd，返回命令输出的内容。 
        如果超时将会抛出TimeoutError异常。 
        cmd - 要执行的命令 
        timeout - 最长等待时间，单位：秒 
        """  
        p = subprocess.Popen(cmd, stderr=subprocess.STDOUT, stdout=subprocess.PIPE, shell=True)
        """
        1.这个类用于在一个新的进程中执行一个子程序，可以方便的实现一些自己定义的方法
        2.cmd这个参数表示要执行的shell命令
        3.shell这个参数的值为True表示shell命令必须要使用字符串来书写
        4.stderr、stdout表示错误、输出句柄
        5.p.poll()这个实例方法是用来检查子进程是否已经执行完成了，没完成返回None,完成返回状态密码
        6.p.terminate()这个实例方法用来停止该子进程
        7.p.stdout这个属性里面包含有输出的内容
        """
        t_beginning = time.time()  
        seconds_passed = 0  
        while True:  
            if p.poll() is not None:      # 这个是运行的意思
                break
            seconds_passed = time.time() - t_beginning       # 这个是计算执行时间要多久
            if timeout and seconds_passed > timeout:  
                p.terminate()      # 这个是关闭进程
                return False  
            time.sleep(0.1)
        return p.stdout.read()      # 这个是用来读取最后获取到的数据
    # 使用telnet方式登录设备，并执行命令获取反馈
    # self.do_telnet('free -h|grep Mem', 0.1)
    def do_telnet(self, cmd, wait):
        self.log_info(cmd)
        res = self.command("telnet.sh {} '{}' {}".format(self.device_ip, cmd, wait), 30)
        return res

    # 使用telnet包执行命令
    def connect_telnet_host(self, host="192.168.1.1", timeout=5):
        try:
            tn = telnetlib.Telnet()          # 建立连接对象
            tn.open(host, timeout=2)         # 建立正式的连接关系
            banner = tn.read_until("/#", timeout=2)
            print("the banner is: {}".format(banner))
        except Exception:
            return False
        return tn

    # 通过telnet连接
    def connect_device(self, host="127.0.0.1"):
        try:
            self.tn = self.connect_telnet_host(host=self.device_ip)
        except Exception as e:
            print(e)
            return False
        if self.tn is False:
            return False
        print("已连接正在测试中")
        return True

    # 使用ssh的方式登录设备并执行命令获取反馈
    def do_ssh(self, cmd, wait):
        self.log_info(cmd)
        res = self.command("ssh.sh root@{} '{}'".format(self.device_ip,cmd),15)
        return res

    # 进行pcba和product测试时使用telnet方式获取终端输出信息，并检查有我们所期待的值，返回boolean
    # self.check_exp('find udisk', 4, 10):
    def check_exp(self, exp, wait=0.5, time_out=40):      # exp 这个参数的内容是希望路由器应有的反应
        self.log_info(exp)
        timeout = time_out
        self.connect_device(self.device_ip)
        res = self.tn .read_until(exp, timeout=30)       # 读取数据，
        if exp in res:          # 如果这里面含有按键已被按下，则返回成功，否则就失败
            self.tn.close()
            return True
        self.tn.close()
        self.log_info(exp)
        return False

    # 进行pcba和product测试时使用telnet方式执行命令，不需要获取反馈信息
    def check_cmd(self, cmd, wait=0.5):
        self.log_info(cmd)
        self.do_telnet(cmd, wait)

    # 进行pcba和product测试时使用telnet方式执行命令，检查我们所期待的值。返回boolean
    # self.check_cmd_exp('detect_art_state', 'device have calibrated'):
    def check_cmd_exp(self, cmd, exp, wait=1, time_out=10):
        info=cmd+"   "+exp
        self.log_info(info)
        timeout = time_out
        while timeout:
            res = self.do_telnet(cmd, wait)
            print res
            if res is False:
                return False
            if exp in res:
                return True
            timeout-=1
        return False
    # 设定使用方式
    """
    5.ssh 和 telent分别是什么？
    """
    def setConnect_type(self):
        if self.device_type in ["GL-MT300N-V2","GL-MIFI","GL-AR750","GL-AR750-5G","GL-AR300M-Lite-ssh",'GL-AR300M-double-flash',
                                "GL-AR150","GL-AR300M-16","GL-AR750S","GL-AR750S-5G","GL-MT300A-ssh","GL-MT300N","GL-B1300",
                                "GL-B1300-5G","GL-CORE","GL-USB150",'GL-MT300N-V3','GL-ENGEL','GL-X750','GL-X750-Transidea-SpA','GL-USB150',"X750",'GL-X1200','GL-AR300M-ssh','GL-X750-ble']:
            self.connect_type = "ssh"
        else:
            self.connect_type = "telnet"

    # 专门提供给进行throughput测试时，返回终端的log信息
    def check_resp(self, cmd, timeout='0.1'):
        self.setConnect_type()
        if self.connect_type == "ssh":
            res = self.do_ssh(cmd,timeout)
        else:
            res = self.do_telnet(cmd,timeout)
        return res

    # 在进行pcba和product测试时设置device_ip的值
    def get_ip(self):
        if "GL-MT300N-V2" == self.device_type or "GL-MT300N-V3" == self.device_type or "GL-MT300N-V2-xinjia" == self.device_type:
            device_ip = "10.10.10.254"
            return device_ip
        else:
            device_ip = "192.168.1.1"
            return device_ip

    # 控制电源端口
    def control_power(self, count, timeout=20):
        power_port = self.count_to_power_port[count]
        cmd = "ctl_client -h 192.168.2.1 -p 1234 -n " + str(power_port)
        while timeout:
            res = os.popen(cmd).read()
            print "ctl_client: ", res
            if "OK" in res:
                return True
            timeout -= 1
            print("control_power(self, count, timeout = 20) , remain times is {}".format(timeout))
        return False

    # 设置iperf类型
    def set_iperf(self):
        if self.device_type in ["GL-MT300N-V2",'GL-MT300N-V3']:
            device_iperf = "mt7628"
        elif self.device_type in ["GL-MT300N", 'GL-MT300A-ssh',"GL-MT300A-telnet"]:
            device_iperf = 'mt7620'
        elif self.device_type in ['GL-B1300', 'GL-B1300-5G']:
            device_iperf = 'b1300'
        elif self.device_type in ['GL-AR750', 'GL-AR750-5G', 'GL-AR150', 'GL-AR300M','GL-AR300M-ssh','GL-X750-Transidea-SpA',
                                  'GL-AR300M-Lite', 'GL-AR300M-16', 'GL-AR750S', 'GL-AR750S-5G', 'GL-CORE',
                                  'GL-USB150', 'GL-MIFI','GL-ENGEL','GL-AR300M-double-flash','GL-X750',"X750",'GL-AR300M-ssh','GL-AR300M-Lite-ssh','GL-X750-ble'
                                  ]:
            device_iperf = 'ar750'
        else:
            device_iperf = 'linux'
        return device_iperf

    # 等待设备分配上ip，并确认可以ping通
    def wait_ping_ip_start(self, timeout=15):
        print("wait_ping_ip_start()")
        res = ""
        cmd = 'ping ' + self.device_ip + " -c 2 -W 2"
        while timeout:
            print "ping ----", self.device_ip, res
            try:
                res = os.popen(cmd).read()        # 这个是树莓派来直接ping这个路由器，res就是ping通后所返回出来的数据，同普的ping通的结果是一样的
            except:
                return False

            if "TTL" in res or 'ttl' in res:
                if self.step == 'third' and self.device_type not in ["GL-CORE"]:
                    self.get_lanip()             # 运行这个函数之后就可以很确定的拿到wlan0这个网卡的IP地址
                    if '192.168.8' in self.lan_ip:    # 最终根据拿到的IP地址来确定返回的值
                        return True
                else:
                    return True
            timeout -= 1
            print("wait_ping_ip_start() , remain times is {}".format(timeout))
        return False

    # 通过主测设备ping通设备
    def wait_ping_ssh(self,timeout=25):
        print("wait_ping_ip_start()")
        res = ""
        cmd = 'ping ' + self.device_ip + " -c 2 -W 2"
        while timeout:
            print "ping ----", self.device_ip, res
            try:
                res = self.dssh.send(cmd,timeout=2)
                print res
            except:
                return False
            if "ttl" in res or "TTL" in res:
                return True
            else:
                timeout -= 1
                time.sleep(3)
        return False

    # 检测重置按钮
    def reset(self, time_out=5):
        print "reset()"
        resp = "reset key is pressed"
        if self.check_exp(resp):
            return True
        else:
            return False
    # 检测gpio状况
    def gpio(self,time_out=5):
        print "gpio()"
        self.check_cmd('kill_all_led_twinkle_process', 1)
        self.check_cmd('core_flash_led', 7)        # 这条语句是core板才会执行的版本
        return True

    # 检测mesh按钮
    def meshset(self,time_out=5):
        print "meshset()"
        resp = "mesh key is pressed"
        if self.check_exp(resp):
            return True
        else:
            return False
    # 检测led
    def testled(self, time_out=0.3):
        print "testled()"
        if self.device_type=="GL-AR300M":
            self.check_cmd('killall led_wlan_lan_blink')
            self.check_cmd('led off')
            self.check_cmd('led on')
            self.check_cmd('led off')
            self.check_cmd('led on')
            self.check_cmd('sh /usr/bin/led_wlan_lan_wan_blink &')
        else:
            self.check_cmd('kill_all_led_twinkle_process')
            self.check_cmd('all_led_control off')
            self.check_cmd('all_led_control on')
            self.check_cmd('all_led_control off')
            self.check_cmd('all_led_control on')
            self.check_cmd('detect_status')
        return True


    ## 校准检测
    def calibration(self):
        print "calibration()"
        if self.check_cmd_exp('detect_art_state', 'device have calibrated'):
            return True
        else:
            return False

    # 检测拨动开关
    def testswitch(self, time_out=5):
        print "testswitch()"
        if self.check_exp("switch moved"):
            return True
        else:
            return False

    # 测试usb设备
    def testusb(self, time_out=6):
        print "testusb()"
        if self.check_exp('find udisk', 4, 10):
            return True
        else:
            return False

    # 检测sd卡
    def testsd(self, time_out=4):
        print "testsd()"
        if self.check_cmd_exp('check_sdcard', 'find sdcard'):
            return True
        else:
            return False

    # 检测3g卡槽
    def test3g(self, time_out=4):
        print "test3g()"
        if self.check_cmd_exp('check_modem_network', 'modem network is ok', 2):
            return True
        if self.check_cmd_exp('check_modem_network', 'modem network is ok', 2):
            return True
        if self.check_cmd_exp('check_modem_network', 'modem network is ok', 2):
            return True
        if self.check_cmd_exp('check_modem_network', 'modem network is ok', 2):
            return True
        if self.check_cmd_exp('check_modem_network', 'modem network is ok', 3):
            return True
        else:
            return False

    # 检测内存大小
    def checkMem(self,time_out=2):
        print "checkMem()"
        res = self.do_telnet('free -h|grep Mem', 0.1)
        mem = re.findall("\d+",''.join(res.replace('\n',' ').replace('\r',' ').split(':')[-2:]))[0]
        print "内存大小为：{}".format(mem)
        if int(mem) > self.mem:
            return True
        else:
            return False



    # pcba测试完成
    def firstok(self, time_out=5):
        print "firstok()"
        if self.device_type == 'GL-X1200':
            return True
        if self.check_cmd_exp('first_test_ok', 'first test is done', 1, 2):
            print(self.device_type)
            if self.device_type == 'GL-X1200':
                print('xxxxxx')
                self.check_cmd("mcu_function_test watchdogtest", 4)
                cmd='timeout 1 ping 192.168.1.1'
                res=os.popen(cmd).read()
                if "TTL" in res or 'ttl' in res:
                    return False
                else:
                    return True
            elif self.device_type != 'GL-CORE' and self.device_type != 'GL-CORE-Wiline':
                self.check_cmd("reboot", 1)
            return True
        elif self.check_cmd_exp('first_test_ok', 'already', 1, 2):
            print(self.device_type)
            if self.device_type == 'GL-X1200':
                self.check_cmd("mcu_function_test watchdogtest",4)
                cmd='timeout 1 ping 192.168.1.1'
                res=os.popen(cmd).read()
                if "TTL" in res or 'ttl' in res:
                    return False
            elif self.device_type != 'GL-CORE' and self.device_type != 'GL-CORE-Wiline':
                self.check_cmd("reboot", 1)
            return True
        else:
            return False
    # core版的pcba测试完成
    def coreok(self, time_out =5):
        print "coreok()"
        if self.check_cmd_exp('core_test_ok', 'done', 1, 2):
            self.check_cmd("reboot", 1)
            return True
        elif self.check_cmd_exp('core_test_ok', 'already', 1, 2):
            self.check_cmd("reboot", 1)
            return True
        else:
            return False
    # 向设备写入信息
    def setinfo(self, time_out = 5):
        print "setinfo()"
        cmd = "setinfo {} {} {} {}".format(self.mac_address,self.ddns_name,self.sn_back_up,self.sn_now_use)
        if self.device_type=="GL-AR300M":
            now_time=datetime.datetime.now().strftime("%Y%m%d%H%M%S")
            now_time='PL'+str(now_time)
            cmd = "setinfo {} {} {} {} {} {} {}".format(self.mac_address, self.ddns_name, self.sn_back_up, self.sn_now_use,now_time,'GL-iNet','GL-iNet')
        if self.check_cmd_exp(cmd,"success",2):
            if self.device_type in ["GL-X1200",'GL-MT300N-V2-xinjia','GL-X750-Transidea-SpA','GL-X750-ble']:
                now_time = datetime.datetime.now().strftime("%Y%m%d")
                cmd1='set_addr_info 0x70 -A "%s" '%now_time
                if self.device_type in ['GL-MT300N-V2-xinjia','GL-MT300N-V2']:
                    cmd1 = 'set_addr_info 0x4070 -A "%s" ' % now_time
                print(cmd1)
                if self.check_cmd_exp(cmd1,'set info success',2):
                    return True
                else:
                    return False
            if self.device_type in ['GL-avira','GL-S1300']:
                now_time = datetime.datetime.now().strftime("%Y%m%d")
                cmd1 = 'set_addr_info 0x70 -A "%s" ' % now_time
                if self.check_cmd_exp(cmd1, 'set info ok', 2):
                    return True
                else:
                    return False
            return True
        elif self.check_cmd_exp(cmd,'fail',2):
            return False
        else:
            return False

    def setinfo1(self,cmd,exp,time_out=5):
        if self.check_cmd_exp(cmd,exp,2):
            return True
        else:
            return False

    # product测试完毕

    def art_cmd(self):
        if self.device_type in ["GL-AR150",'GL-ENGEL','GL-CORE',"GL-MIFI",'GL-MIFI-CUSTOM',"GL-USB150","GL-AR300M",'GL-AR300M-double-flash','GL-CORE-Wiline']:
            return 'dd if=/dev/mtdblock6 of=/www/art.bin bs=64k'
        if self.device_type in ["GL-MT300N-V2","GL-MT300A" ,"GL-MT300N-V3","GL-MT300A-ssh",'GL-MT300N-V2-xinjia']:
            return 'dd if=/dev/mtd3 of=/www/art.bin bs=64k'
        if self.device_type in ["GL-AR750",'GL-AR750S', "GL-AR750-5G", "GL-X750","X750",'GL-X1200','GL-X750-Transidea-SpA','GL-X750-ble']:
            return 'dd if=/dev/mtdblock2 of=/www/art.bin bs=64k'
        if self.device_type in ["GL-B1300-5G", 'GL-B1300',"S1300",'GL-avira','GL-S1300']:
            return 'dd if=/dev/mtd7 of=/www/art.bin bs=64k'
        else:
            return 'not command'

    def save_info_database(self):
        path="/home/pi/artbin"
        isExists = os.path.exists(path)
        if not isExists:
            os. makedirs(path)
        try:
            res = requests.get("http://{}/art.bin".format(self.device_ip), verify=False,timeout=5)
        except:
            return True
        if res.ok:
            pathfile="/home/pi/artbin"+"/"+self.mac_address+'.bin'
            with open(pathfile, "wb") as f:
                f.write(res.content)
        # f = open('art.bin', 'rb')
        # artdata=f.read()
        # databaseapi.updatatable(artdata,self.mac_address)
        # f.close()
        # os.remove('art.bin')

    #蓝牙测试
    def buletoothtest(self):
        if self.device_type == 'GL-MT300N-V2-xinjia':
            cmd='gl-ble-production-test /dev/ttyS0 115200 0 mt300n'
        elif self.device_type == 'GL-avira':
            cmd = 'gl-ble-production-test /dev/ttyHS0 115200 0 s1300'
        elif self.device_type == 'GL-S1300':
            cmd = 'gl-ble-production-test /dev/ttyHS0 115200 0'
        elif self.device_type in ['GL-X750-Transidea-SpA','GL-X750-ble']:
            cmd = 'gl-ble-production-test /dev/ttyS0 115200 0 x750'
        res = self.do_telnet(cmd, 10)
        print(res)
        if res is False:
            return False
        rex = 'BLE mac:.*'
        if 'test OK' in res:
            try:
                mac_b = re.findall(rex, res)[0]
            except:
                return False
            mac_b = mac_b.strip()
            mac_b1 = mac_b[-17:]
            mac_b1 = mac_b1.replace(' ', ":")
            self.avira_blueth = mac_b1
            mac_b2 = mac_b[:8]
            mac_b2 = mac_b2.replace(' ', '-')
            self.bluetoothmac = mac_b2 + mac_b1
            return True
        else:
            return False

    # zigbee测试
    def zigbeetest(self):
        print('zigbeetest')
        if self.device_type == 'GL-avira':
            cmd = 'gl-zigbee-test && killall gl_zigbee'
        res = self.do_telnet(cmd, 25)
        print(res)
        if res is False:
            return False
        rex = 'EUI:.*'
        if 'test ok' in res:
            try:
                mac_b = re.findall(rex, res)[0]
            except:
                return False
            mac_b = mac_b.strip()
            mac_b1 = mac_b[-16:]
            mac_b1 = mac_b1[0:2]+":"+mac_b1[2:4]+":"+mac_b1[4:6]+":"+mac_b1[6:8]+":"+mac_b1[8:10]+":"+mac_b1[10:12]+":"+mac_b1[12:14]+":"+mac_b1[14:]
            self.zigbeemac=mac_b1
            return True
        else:
            return False
    def get_gcom(self):
        cmd = 'gcom -s /etc/gcom/imei.gcom -d /dev/ttyUSB3'
        res=self.do_telnet(cmd,2)
        if 'OK' in res:
            self.gcom='gcom: '+res.splitlines()[-7]
            print '*************************************'
            print 111111111111111111111111
            print res.splitlines()
            print '____________________________________'
            return True
        else:
            return False


    def secondok(self, time_out=5):
        if config.mods == "product":
            if self.device_type =='GL-X750-Transidea-SpA':
                if self.get_gcom() is False:
                    return False
            if self.setinfo() is False:
                return False
            if self.device_type in ['GL-avira']:
                if self.setinfo1('set_addr_info 0x100 -H %s'%self.mac_address.replace(':',''),'ok',2) is False:
                    return False
                if self.setinfo1('set_addr_info 0x110 -A %s' % self.serial, 'ok', 2) is False:
                    return False
                if self.setinfo1('set_addr_info 0x120 -A %s' % self.ssid1, 'ok', 2) is False:
                    return False
                if self.setinfo1('set_addr_info 0x130 -A %s' % self.key, 'ok', 2) is False:
                    return False
                if self.setinfo1('set_addr_info 0x70 -A  DE', 'ok', 2) is False:
                    return False
            if self.check_cmd_exp('second_test_ok', 'second test is done', 1, 2):
                cmd = self.art_cmd()
                if cmd == 'not command1':
                    self.check_cmd("reboot", 1)
                    self.rm_log()
                    return False
                else:
                    product_type1 = self.device_type + '-WAN'
                    sql = "UPDATE device SET used='1',product_type='%s' WHERE mac_address='%s'" % (product_type1, self.mac_address)
                    if self.device_type in ['GL-MT300N-V2-xinjia','GL-S1300','GL-X750-ble']:
                        sql="UPDATE device SET used='1',Note='%s',product_type='%s' WHERE mac_address='%s'" % (self.bluetoothmac,product_type1,self.mac_address)
                    elif self.device_type in ['GL-X750-Transidea-SpA']:
                        sql = "UPDATE device SET used='1',Note='%s',product_type='%s' WHERE mac_address='%s'" % (
                            self.gcom + ' | ' + self.bluetoothmac, product_type1, self.mac_address)
                    elif self.device_type in ['GL-avira']:
                        sql = "UPDATE customer_avira SET used='1',BLE_mac='%s',zigbee='%s' WHERE mac_address='%s'" %(self.avira_blueth,self.zigbeemac,self.mac_address)
                    databaseapi.updatatable_powertest(sql)
                    if self.device_type in ['GL-CORE', "GL-MT300N-V2",'GL-MT300N-V2-xinjia','GL-CORE-Wiline']:
                        print 'mac_address地址'
                        databaseapi.updatatable_used(self.mac_address,self.device_type)
                        print('beifen')
                    elif self.device_type in ['GL-X750', "GL-X1200","GL-S1300",'GL-AR750S','X750','GL-X750-Transidea-SpA','GL-X750-ble']:
                        databaseapi.updatatable_used3(self.mac_address,self.device_type)
                        print('beifen')
                    try:
                        self.check_cmd(cmd, 2)
                        print("art dd命令数据备份")
                        self.save_info_database()
                    except:
                        print('dd命令失败')
                    self.check_cmd('reboot', 1)
                    self.rm_log()
                    return True
            elif self.check_cmd_exp('second_test_ok', 'already set', 1, 2):
                cmd = self.art_cmd()
                if cmd == 'not command1':
                    self.check_cmd("reboot", 1)
                    self.rm_log()
                    return True
                else:
                    product_type1=self.device_type+'-WAN'
                    sql = "UPDATE device SET used='1',product_type='%s' WHERE mac_address='%s'" % (product_type1,self.mac_address)
                    if self.device_type in ['GL-MT300N-V2-xinjia', "GL-S1300",'GL-X750-ble']:
                        sql = "UPDATE device SET used='1',Note='%s',product_type='%s' WHERE mac_address='%s'" % (self.bluetoothmac,product_type1, self.mac_address)
                    elif self.device_type in ['GL-avira']:
                        sql = "UPDATE customer_avira SET used='1',BLE_mac='%s',zigbee='%s' WHERE mac_address='%s'" % (
                        self.avira_blueth, self.zigbeemac, self.mac_address)
                    elif self.device_type in ['GL-X750-Transidea-SpA']:
                        sql = "UPDATE device SET used='1',Note='%s',product_type='%s' WHERE mac_address='%s'" % (
                        self.gcom +' | '+ self.bluetoothmac, product_type1, self.mac_address)
                    databaseapi.updatatable_powertest(sql)
                    if self.device_type in ['GL-CORE', "GL-MT300N-V2",'GL-MT300N-V2-xinjia','GL-CORE-Wiline']:
                        print 'mac_address地址'
                        databaseapi.updatatable_used(self.mac_address,self.device_type)
                        print('beifen')
                    elif self.device_type in ['GL-X750', "GL-X1200", "GL-S1300", 'GL-AR750S', 'X750','GL-X750-Transidea-SpA','GL-X750-ble']:
                        databaseapi.updatatable_used3(self.mac_address,self.device_type)
                        print('beifen')
                    try:
                        self.check_cmd(cmd, 2)
                        print("art dd命令数据备份")
                        self.save_info_database()
                    except:
                        print('dd命令失败')
                    self.check_cmd('reboot', 1)
                    self.rm_log()
                    return True
            else:
                return False
        else:
            self.rm_log()
            return True
    # 检测是否进行pcba测试
    def checkfirst(self):
        print "checkfirst"
        if self.device_type=="GL-AR300M":
            return True
        if self.check_cmd_exp('detect_pcba_state', 'have tested first', 0.5, 2):
            return True
        else:
            return False

    def computmac(self):
        macaddr = self.mac
        last_two = "".join(macaddr.split(":"))
        last_two_int = int(last_two,16)
        new_last_two_int = last_two_int + 1
        new_last_two = hex(new_last_two_int)
        new_last_two = new_last_two[2:-1]
        for i in range(len(new_last_two),12):
            new_last_two = '0'+str(new_last_two)
        new_addr = ""
        for item in range(1,13):
            if item % 2 == 0:
                if item == 12:
                    new_addr = new_addr + new_last_two[item-2:item]
                else:
                    new_addr =new_addr + new_last_two[item-2:item]+":"
        return new_addr.upper()



   # 根据设备的型号设置连接wifi的ssid
    def set_ssid_of_name(self):
        last_3_mac = "".join(str(self.mac).split(":"))[-3:]
        ssid_info = "GL-AR150-"
        if "GL-AR300M" in str(self.device_type).strip():
            ssid_info = "GL-AR300M-"
        elif "GL-AR300M-telnet" in str(self.device_type).strip():
            ssid_info = "GL-AR300M-"
        elif "GL-AR300M-Lite-ssh" in str(self.device_type).strip():
            ssid_info = "GL-AR300M-"
	elif "GL-AR750S-5G" == str(self.device_type).strip():
            ssid_info = "GL-AR750S-"
	elif "GL-AR750S" == str(self.device_type).strip():
            ssid_info = "GL-AR750S-"
        elif "GL-AR750" in str(self.device_type).strip():
            ssid_info = "GL-AR750-"
        elif "GL-USB150" in str(self.device_type).strip():
            ssid_info = "GL-USB150-"
        elif "GL-B1300" in str(self.device_type).strip():
            ssid_info = "GL-B1300-"
        elif "GL-MT300N-V2" == str(self.device_type).strip():
            ssid_info = "GL-MT300N-V2-"
        elif "GL-MIFI" in str(self.device_type).strip():
            ssid_info = "GL-MIFI-"
        elif "GL-MT300A-ssh" == str(self.device_type).strip():
            ssid_info = "GL-MT300A-"
        elif "GL-MT300A-telnet" == str(self.device_type).strip():
            ssid_info = "GL-MT300A-"
        elif "GL-MT300N" == str(self.device_type).strip():
            ssid_info = "GL-MT300N-"
        elif "GL-CORE" == str(self.device_type).strip():
            ssid_info = "Domino-"
        elif "GL-MT300N-V3" == str(self.device_type).strip():
            ssid_info = "VIXMINI-"
        elif "GL-ENGEL" == str(self.device_type).strip():
            ssid_info = "GL-ENGEL-"
        elif "GL-AR300M-double-flash" == str(self.device_type).strip():
            ssid_info = "GL-AR300M-"
        elif "GL-X750" == str(self.device_type).strip():
            ssid_info = "GL-X750-4G-"
        elif "X750" == str(self.device_type).strip():
            ssid_info = "GL-X750-4G-"
        elif "GL-X1200" == str(self.device_type).strip():
            ssid_info = "GL-X1200-"
        ssid = ssid_info + last_3_mac.lower()
        if "Lite" in str(self.device_type).strip():
            ssid += "-NOR"
        if "GL-AR300M-tel" in str(self.device_type).strip():
            ssid += "-NOR"
        if "16" in str(self.device_type).strip():
            ssid += "-NOR"
        if self.mode == "5G":
            ssid = ssid+"-5G"
        print("ssid is {}".format(ssid))
        return ssid



    # 增加wifi
    def joinwifi(self):
        if self.mode == "5G":
            cmd = 'joinwifi.sh 5G {} goodlife'.format(self.ssid)
        else:
            cmd = 'joinwifi.sh 2G {} goodlife'.format(self.ssid)
        print cmd
        res = self.dssh.send_expect(cmd,'root@', timeout=60)
        print res
        if res is False:
            return False
        return True


    # 根据设置好的ssid名字连接wifi，并确认连接成功。
    def set_ssid(self):
        print('setssid')
        self.ssid = self.set_ssid_of_name()
        print 19
        try:
            if self.device_type not in self.b2b:
                print 20
                connect = os.popen("ssid.sh {}".format(self.ssid))
                print 21
                result = connect.readlines()
                print 22
                print("connect result is: %s" % result[-1])
                if "connected" in result[-1]:
                    print('连接成功')
                else:
                    return False
            else:
                self.joinwifi()
                return True
        except Exception,e:
            print(e)
            return False
        return True


    def connect_device_tel(self,time_out=5):
        cmd = "rm -rf /root/.ssh/known_hosts"
        self.dssh.send_only(cmd)
        print('connect_device_tel')
        if self.connect_type == 'telnet':
            cmd = 'telnet 192.168.8.1'
        else:
            cmd = 'ssh -o StrictHostKeyChecking=no root@192.168.8.1'
        while time_out:
            if self.connect_type == 'telnet':
                res = self.dssh.send_expect(cmd, 'root@', timeout=5)
            else:
                res = self.dssh.send(cmd,timeout=5)
                if "y/n" in res:
                    cmd = 'y'
                    res = self.dssh.send_expect(cmd, 'root@', timeout=5)
                elif "root@" in res:
                    cmd = 'ifconfig'
                    res = self.dssh.send_expect(cmd, '192.168.8.3', timeout=1)
            print res
            if res is False:
                time_out -= 1
            else:
                cmd = 'ifconfig'
                res = self.dssh.send_expect(cmd, '192.168.8.3', timeout=1)
                if res is True:
                    time_out -= 1
                else:
                    return True
        return False

    # 进行预处理，设置好初始化信息，连接wifi
    def pretreat(self, mac):
        print 18
        self.mac = mac
        if self.set_ssid() is False:                # 确定wifi的连接名字
            return False
	print 221
        if self.device_type not in self.b2b:
            time_out = 5
            while time_out:
		print 222
                if self.wait_ping_ip_start() is False:
		    print 229
                    os.popen("sudo /etc/init.d/dhcpcd restart")
                    time.sleep(5)
                    time_out -= 1
                else:
		    print 2210
                    cmd = "ifconfig eth0|grep eth0"
                    res = self.check_resp(cmd, 1)
		    print 2211
                    print res
                    if "E4:95:6E" in res:
                        return True
                    if "98:02:D8" in res:
                        return  True
                    else:
                        time.sleep(5)
                        time_out -= 1
            return False
        else:
            if self.wait_ping_ssh() is False:
                return False
            else:
                return self.connect_device_tel()

    # 获取设备的lanip
    def get_lanip(self):
        self.lan_ip = self.get_inet_ip('wlan0')            # 获取设备的lan_ip

    # 进行Mac 地址比较
    def maccompare(self,time_out=5):
        while time_out:
            if self.device_type not in self.b2b:
		print 11
		print self.device_type
		print 12
		if 'GL-MT300N-V3' == self.device_type:
		    print 13
                    cmd = "ifconfig eth0|grep eth0"
		else:
		    cmd = "ifconfig eth0|grep eth0"
                res = self.check_resp(cmd, 1)
            else:
                cmd = "iwconfig |grep 'Access Point'"
                res = self.ssh.send(cmd, timeout=5)
            print res
            if res is False:
                time_out -= 1
                time.sleep(6)
            if '5G' in self.device_type and self.device_type in self.b2b:
                mac = self.computmac()
                if mac in res:
                    return True
                else:
                    time_out -= 1
                    time.sleep(6)
            else:
		print 14
		print res
		print 15
                if self.mac in res:
                    return True
                else:
                    time_out -= 1
                    time.sleep(6)
        return False

    # 向树莓派获取需要的iperf文件
    def wait_wget_success(self):
        print 27
        cmd = "ls -l /tmp|grep iperf"
        res = self.check_resp(cmd)
	print 271
        print res
	print 2711
        if res is False:
            return False
        if self.device_iperf in res and "-xr-x" in res:
	    print 2712
            return True
	print 2713
        cmd = "wget http://{}/iperf_{} -O /tmp/iperf_{} -T 2".format(self.lan_ip, self.device_iperf, self.device_iperf)
	print 2714
        print cmd
	print 272
        res = self.check_resp(cmd, 3)
        if res is False:
            return False
        print res
	print 273
        cmd = "chmod +x /tmp/iperf_{}".format(self.device_iperf)
        res = self.check_resp(cmd, 0.5)
        if res is False:
            return False
	print 274
        return True

    def speed_rx(self):
        print 26
        if self.wait_wget_success() is False:
            return False
	print 28
        cmd = "/tmp/iperf_{} -s -D".format(self.device_iperf)
        res = self.check_resp(cmd, 1.5)
	print 29
        if res is False:
            return False
        print res
	print 30
        if self.device_type in self.t2u:
	    print 31
            res1 = os.popen('iperf3 -u -b 0 -c {} -t 5'.format(self.device_ip))
        else:
	    print 32
            res1 = os.popen('iperf3 -c {} -P 10 -t 5'.format(self.device_ip))
	    print res1
	    print 33
        try:
	    print 34
            speed_down = res1.read().replace('\n',' ').split('MBytes')[-1].split('/')[0].strip(' ').split(' ')[0].strip(' ')
	    print 35
        except:
            speed_down = '0'
	print 36
        print speed_down
	print 37
        self.speed_rx_re = speed_down
	print 38
        return speed_down

    # 测试吞吐量的tx值
    def speed_tx(self):
        if self.wait_wget_success() is False:
            return False
        print "run speed_tx"
        if self.device_type in self.t2u:
            res = os.popen('iperf3 -u -b 0 -c {} -t 5 -R'.format(self.device_ip))
        else:
            res = os.popen('iperf3 -c {} -P 10 -t 5 -R'.format(self.device_ip))
        if res is False:
            return False
        print res
        try:
            speed_on=res.read().replace('\n', ' ').split('MBytes')[-1].split('/')[0].strip(' ').split(' ')[0].strip(' ')
        except:
            speed_on = '0'
        os.system('killall -9 iperf3')
        print speed_on
        self.speed_tx_re = speed_on
        return speed_on

    def speed_b_r(self):
        print('speed_b_r')
        cmd = "killall -9 iperf_{}".format(self.device_iperf)
        res = self.dssh.send_expect(cmd,'root@',timeout=5)
        print res
        cmd = "ls -l /tmp|grep iperf"
        res = self.dssh.send_expect(cmd,'root@',timeout=5)
        if self.device_iperf not in res:
            cmd = "wget http://192.168.8.3/iperf_{} -O /tmp/iperf_{} -T 2".format(self.device_iperf,self.device_iperf)
            res = self.dssh.send_expect(cmd,"root@",timeout=30)
            print res
        cmd = "chmod +x /tmp/iperf_{}".format(self.device_iperf)
        res = self.dssh.send_expect(cmd,"root@",timeout=30)
        print res
        cmd =  "/tmp/iperf_{} -s -D".format(self.device_iperf)
        res = self.dssh.send_expect(cmd,"root@",timeout=30)
        print res
        cmd = "iperf3 -u -b 0 -c 192.168.8.1 -t 5"
        res = self.ssh.send(cmd,timeout=10)
        print res
        speed_down = res.replace('\n', '').split('MBytes')[-1].split('/')[0].strip(' ').split(' ')[0].strip(' ')
        cmd = "killall -9 iperf3"
        res = self.ssh.send_expect(cmd,'root@',timeout=5)
        print speed_down
        return speed_down

    def speed_b_t(self):
        print('speed_b_t')
        cmd = "iperf3 -u -b 0 -c 192.168.8.1 -t 5 -R"
        res = self.ssh.send_expect(cmd,"root@",timeout=30)
        print res
        speed_on = res.replace('\n', '').split('MBytes')[-1].split('/')[0].strip(' ').split(' ')[0].strip(' ')
        cmd = "killall -9 iperf_{}".format(self.device_iperf)
        res = self.dssh.send_expect(cmd,'root@',timeout=5)
        print speed_on
        return speed_on

    def speed_r(self):
        if self.device_type in self.b2b:
            return self.speed_b_r()
        else:
            return self.speed_rx()

    def speed_t(self):
        if self.device_type in self.b2b:
            return self.speed_b_t()
        else:
            return self.speed_tx()

    def offline(self):
        pass

    # 检测fivegpio
    def testfivegpio(self, time_out=0.3):
        print "testfivegpio()"
        self.check_cmd('echo 22 > /sys/class/gpio/export')
        self.check_cmd('echo out > /sys/class/gpio/gpio22/direction')
        self.check_cmd('echo 1 > /sys/class/gpio/gpio22/value')
        self.check_cmd('echo 0 > /sys/class/gpio/gpio22/value')

        self.check_cmd('echo 21 > /sys/class/gpio/export')
        self.check_cmd('echo out > /sys/class/gpio/gpio21/direction')
        self.check_cmd('echo 1 > /sys/class/gpio/gpio21/value')
        self.check_cmd('echo 0 > /sys/class/gpio/gpio21/value')

        self.check_cmd('echo 20 > /sys/class/gpio/export')
        self.check_cmd('echo out > /sys/class/gpio/gpio20/direction')
        self.check_cmd('echo 1 > /sys/class/gpio/gpio20/value')
        self.check_cmd('echo 0 > /sys/class/gpio/gpio20/value')

        self.check_cmd('echo 19 > /sys/class/gpio/export')
        self.check_cmd('echo out > /sys/class/gpio/gpio19/direction')
        self.check_cmd('echo 1 > /sys/class/gpio/gpio19/value')
        self.check_cmd('echo 0 > /sys/class/gpio/gpio19/value')

        self.check_cmd('echo 18 > /sys/class/gpio/export')
        self.check_cmd('echo out > /sys/class/gpio/gpio18/direction')
        self.check_cmd('echo 1 > /sys/class/gpio/gpio18/value')
        self.check_cmd('echo 0 > /sys/class/gpio/gpio18/value')
        return True

    # onsecondpower
    def testsecondpower(self, time_out=5):
        print "testsecondpower()"
        self.check_cmd('echo 28 > /sys/class/gpio/export')
        self.check_cmd('echo in > /sys/class/gpio/gpio28/direction')
        if self.check_cmd_exp('cat /sys/kernel/debug/gpio', 'gpio-28  (sysfs               ) in  hi', 1, 10):
            if self.check_cmd_exp('cat /sys/kernel/debug/gpio', 'gpio-28  (sysfs               ) in  lo', 1, 20):
                return True
            else:
                return False
        else:
            return False

    # 检测向左波动开关
    def testswitchleft(self, time_out=5):
        print "testswitchleft()"
        if self.check_exp("switch moved to right"):
            return True
        else:
            return False

    # 检测中间波动开关
    def testswitchmiddle(self, time_out=5):
        print "testswitchmiddle()"
        if self.check_exp("switch moved to middle"):
            return True
        else:
            return False

    # 检测中间和左边波动开关
    def testswitchleftmid(self, time_out=5):
        print "testswitchmiddle()"
        if self.check_exp("switch moved to middle"):
            if self.check_exp("switch moved to left"):
                return True
        if self.check_exp("switch moved to left"):
            if self.check_exp("switch moved to middle"):
                return True
        else:
            return False


    # 检测中间和左边波动开关
    def testswitchleftmidright(self, time_out=5):
        print "onswitchleftmidright"
        if self.check_exp("switch moved to middle"):
            if self.check_exp("switch moved to left"):
                if self.check_exp("switch moved to middle"):
                    if self.check_exp("switch moved to right"):
                        return True
        if self.check_exp("switch moved to right"):
            if self.check_exp("switch moved to middle"):
                if self.check_exp("switch moved to left"):
                    return True
        if self.check_exp("switch moved to left"):
            if self.check_exp("switch moved to middle"):
                if self.check_exp("switch moved to right"):
                    return True
        if self.check_exp("switch moved to left"):
            if self.check_exp("switch moved to middle"):
                if self.check_exp("switch moved to right"):
                    return True
        else:
            return False

    ##下载测试脚本
    def testdowntest(self):
        print("testdowntest()")
        if self.device_type=='GL-X750-Transidea-SpA' or self.device_type=='GL-X750-ble':
            if self.check_cmd_exp('get_files http SpA', 'OK', wait=5):
                return True
            else:
                return False
        elif self.device_type in ['GL-S1300','GL-avira']:
            if self.check_cmd_exp('get_files', 'OK', wait=5):
                return True
            else:
                return False
        elif self.device_type in ['GL-MT300N-V2-xinjia']:
            if self.check_cmd_exp('get_files http xinjia', 'OK',wait=5):
                return True
            else:
                return False

        else:
            return False



    ##测试单片机
    def testmcu(self):
        print("testmcu()")
        if self.check_cmd_exp('mcu_function_test mcutest', 'MCU Test OK', wait=2):
            return True
        else:
            return False

    ##测试GPS
    def testgps(self):
        print("testgps()")
        if self.check_cmd_exp('gps_function_test', 'GPS Test OK', wait=4):
            return True
        else:
            return False

    # 测试看门狗
    def testdog(self, time_out=5):
        print "testdog()"
        if self.check_cmd_exp('first_test_ok', 'first test is done', 1, 2):
            print(self.device_type)
            if self.device_type == 'GL-X1200':
                print('xxxxxx')
                self.check_cmd("mcu_function_test watchdogtest", 4)
                cmd='timeout 1 ping 192.168.1.1'
                res=os.popen(cmd).read()
                if "TTL" in res or 'ttl' in res:
                    return False
                else:
                    return True
            return True
        elif self.check_cmd_exp('first_test_ok', 'already', 1, 2):
            print(self.device_type)
            if self.device_type == 'GL-X1200':
                self.check_cmd("mcu_function_test watchdogtest",4)
                cmd='timeout 1 ping 192.168.1.1'
                res=os.popen(cmd).read()
                if "TTL" in res or 'ttl' in res:
                    return False
            return True
        else:
            return False

    ##测试emmc
    def testemmc(self):
        print("testemmc()")
        if self.check_cmd_exp('check_emmc', 'ok', wait=2):
            return True
        else:
            return False
















