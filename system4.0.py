#!/usr/bin/env python
#encoding: utf-8
import requests
import logging
import time
import webbrowser
import comm.config as config
import demjson
import threading
import os

from modsys4.gliot import KiraClient, Action
from modsys4.sys4 import SystemF
from modsys4.databaseapi import updatatable,updatatable1

logging.basicConfig(level=logging.DEBUG,
    format = '[%(asctime)s] %(levelname)s %(message)s',
    datefmt = '%Y-%m-%d %H:%M:%S')
root = logging.getLogger()
root.setLevel(logging.NOTSET)

#用来上传/home/pi/artbin目录的art文件,程序结束，此线程也结束，
def art_up():
    path='/home/pi/artbin'
    while 1:
        time.sleep(5)
        files=os.listdir(path)
        if files:
            for filename in files:
                if "E4:" in filename[0:4]:
                    print(filename)
                    filepath=path+'/'+filename
                    mac=filename[0:17]
                    print(mac)
                    f = open(filepath, 'rb')
                    artdata=f.read()
                    try:
                        print('updatatable')
                        updatatable(artdata,mac)
                        print('updatatablesucced')
                        f.close()
                        os.remove(filepath)
                    except:
                        print('error database')
                        pass
                elif 'A8:' in filename[0:4]:
                    filepath = path + '/' + filename
                    mac = filename[0:17]
                    print(mac)
                    f = open(filepath, 'rb')
                    artdata = f.read()
                    try:
                        sql = "update customer_avira set art=(%s) where mac_address=(%s)"
                        print('updatatable')
                        updatatable1(sql,artdata, mac)
                        print('updatatablesucced')
                        f.close()
                        os.remove(filepath)
                    except:
                        print('error database')
                        pass



if __name__ == '__main__':
    t = threading.Thread(target=art_up)
    t.start()
    #使用默认浏览器打开系统所在的地址。
    box = webbrowser.get('chromium-browser')
    # 打开服务器的地址
    box.open("http://192.168.16.17/dist")
    client = KiraClient(("192.168.16.17", 1883), 'gliot')
    client.start()


    # 接受控制端上报在线通知
    @client.route("onlive")                            # 将onlive这个名字和这里的action这个动作一一匹配。
    def handleOnLiveAction(client, action):             # 这里action是一个前端传过来的包含有很多信息的对象
        logging.info("handleOneLiveAction()")
        data = demjson.encode({'status': 1})           # 这个就是将字典打包为json格式的字符串
        actionReply = Action.buildReplyAction(action, "onlive", data)         # 获得了重构后的action实例对象，因为这个实例对象现在需要反向发送了，所以发送与接受方需要对换，同时增加data状态信息
        client.sendAction(actionReply)                                         # 这个就是物联网的通信协议

    # 接受控制端连接设备的命令
    @client.route("onconnect")
    def handleOnConnectAction(client, action):
        config.device = SystemF(action)   # 根据前端传递过来的action对象来创建实例化对象，
        if config.device.ping_start is False:  # 判断是否ping通，并将结果传递给前端
            data = demjson.encode({'status': 0})
        else:
            data = demjson.encode({'status': 1})
        actionReply = Action.buildReplyAction(action, "onconnect", data)
        client.sendAction(actionReply)

    # 接受控制端的测试重置按钮的命令
    @client.route("onreset")
    def handleOnResetAction(client, action):    # 流程是测试员按下了按钮，就会像后端发送这个action对象，后端来检验这个路由器是否做出了相应的响应
        if config.device.reset() is False:      # 调用reset、check_exp、connect_device、connect_telnet_host一共需要四个函数。
            """
            1.connect_telnet_host 这个函数是是用来远程登陆路由器的，一旦登陆就意味着监听路
                由器的reset按钮的状态，这个函数是来返回tn对象的。
            2.connect_device 这个函数是用来获取tn对象的
            3.check_exp 这个函数一是调用上面的函数来获取tn对象的，二是监听路由器是否
                被人按下，发出一个字符串的信号，同时根据是否监听到想要的内容，来响应相应的Bool值
            4.reset函数根据上一个函数的响应结果来返回相应的值来传给这里来。
            """
            data = demjson.encode({'status': 0, 'index': action.index})
        else:
            data = demjson.encode({'status': 1, 'index': action.index})
        actionReply = Action.buildReplyAction(action, "onreset",data)
        client.sendAction(actionReply)

    # 接受控制端的测试gpio的命令
    @client.route("ongpio")
    def handleOnResetAction(client, action):
        if config.device.gpio() is False:          # gpio、check_cmd、do_telnet、command
            """
            1.command 这个函数是使用subprocess多进程来远程登陆路由器，并且执行shell脚本命令。
            2.do_telnet 这个函数是来执行提供shell脚本语句
            3.check_cmd 是用来直接调用do_telnet函数的
            4.gpio 这个函数是用来传递需要执行的语句的
            """
            data = demjson.encode({'status': 0, 'index': action.index})
        else:
            data = demjson.encode({'status': 1, 'index': action.index})
        actionReply = Action.buildReplyAction(action, "ongpio",data)
        client.sendAction(actionReply)

    # 接受控制端的测试mesh按钮的命令
    @client.route("onmeshset")
    def handleOnMeshsetAction(client, action):
        if config.device.meshset() is False:      # 调用 meshset、check_exp、connect_device、connect_telnet_host
            data = demjson.encode({'status': 0, 'index': action.index})
        else:
            data = demjson.encode({'status': 1, 'index': action.index})
        actionReply = Action.buildReplyAction(action, "onmeshset",data)
        client.sendAction(actionReply)

    # 接受控制端的测试led的命令
    @client.route("onled")
    def handleOnLedAction(client, action):
        if config.device.testled() is False:     # testled、check_cmd、do_telnet、command
            data = demjson.encode({'status': 0, 'index': action.index})
        else:
            data = demjson.encode({'status': 1, 'index': action.index})
        actionReply = Action.buildReplyAction(action, "onled",data)
        client.sendAction(actionReply)

    # 接受控制端的测试校验状态命令
    @client.route("oncalibration")
    def handleOnCalibrationAction(client, action):
        if config.device.calibration() is False:   # calibration、check_cmd_exp、do_telnet、command
            data = demjson.encode({'status': 0, 'index': action.index})
        else:
            data = demjson.encode({'status': 1, 'index': action.index})
        actionReply = Action.buildReplyAction(action, "oncalibration",data)
        client.sendAction(actionReply)

    # 接受控制端的测试拨动开关的命令
    @client.route("ontestswitch")
    def handleOnTestSwitchAction(client, action):
        if config.device.testswitch() is False:    # testswitch、check_exp、connect_device、connect_telnet_host
            data = demjson.encode({'status': 0, 'index': action.index})
        else:
            data = demjson.encode({'status': 1, 'index': action.index})
        actionReply = Action.buildReplyAction(action, "ontestswitch",data)
        client.sendAction(actionReply)

    # 接受控制端的测试usb的命令
    @client.route("ontestusb")
    def handleOnTestUsbAction(client, action):
        if config.device.testusb() is False:    # testusb、check_exp、connect_device、connect_telnet_host
            data = demjson.encode({'status': 0, 'index': action.index})
        else:
            data = demjson.encode({'status': 1, 'index': action.index})
        actionReply = Action.buildReplyAction(action, "ontestusb",data)
        client.sendAction(actionReply)

    # 接受控制端的测试sd卡的命令
    @client.route("ontestsd")
    def handleOnTestSd(client, action):
        if config.device.testsd() is False:     # testsd、check_cmd_exp、do_telnet、command
            data = demjson.encode({'status': 0, 'index': action.index})
        else:
            data = demjson.encode({'status': 1, 'index': action.index})
        actionReply = Action.buildReplyAction(action, "ontestsd",data)
        client.sendAction(actionReply)

    # 接受控制端的测试内存的命令
    @client.route("ontestddr")
    def handleOnTestSd(client, action):
        if config.device.checkMem() is False:    # checkMem、do_telnet、command
            data = demjson.encode({'status': 0, 'index': action.index})
        else:
            data = demjson.encode({'status': 1, 'index': action.index})
        actionReply = Action.buildReplyAction(action, "ontestddr",data)
        client.sendAction(actionReply)

    # 接受控制端的测试3g卡的命令
    @client.route("ontest3g")
    def handleOnTestSd(client, action):
        if config.device.test3g() is False:    # test3g、check_cmd_exp、do_telnet、command
            data = demjson.encode({'status': 0, 'index': action.index})
        else:
            data = demjson.encode({'status': 1, 'index': action.index})
        actionReply = Action.buildReplyAction(action, "ontest3g",data)
        client.sendAction(actionReply)

    # 接受控制端的完成pcba测试的命令
    @client.route("onfirstok")
    def handleOnFirstOkAction(client, action):  # 只能同时只能打开一个终端
        if config.device.firstok() is False:    # firstok、check_cmd_exp、do_telnet、command
            data = demjson.encode({'status': 0, 'index': action.index})
        else:
            data = demjson.encode({'status': 1, 'index': action.index})
        actionReply = Action.buildReplyAction(action, "onfirstok",data)
        client.sendAction(actionReply)

    # 接受控制端的完成core版的pcba测试的命令
    @client.route("oncoreok")
    def handleOnFirstOkAction(client, action):
        if config.device.coreok() is False:
            """
            1、coreok、check_cmd_exp、do_telnet、command
            2、coreok、check_cmd、do_telnet、command
            """
            data = demjson.encode({'status': 0, 'index': action.index})
        else:
            data = demjson.encode({'status': 1, 'index': action.index})
        actionReply = Action.buildReplyAction(action, "oncoreok",data)
        client.sendAction(actionReply)

    # 接受控制端的完成product测试的命令
    @client.route("onsecondok")
    def handleOnSecondOkAction(client, action):
        if config.device.secondok() is False:
            """
            1、secondok、setinfo、check_cmd_exp、do_telnet、command
            2、secondok、check_cmd_exp、do_telnet、command
            3、secondok、check_cmd、do_telnet、command
            """
            data = demjson.encode({'status': 0, 'index': action.index})
        else:
            data = demjson.encode({'status': 1, 'index': action.index})
        actionReply = Action.buildReplyAction(action, "onsecondok",data)
        client.sendAction(actionReply)

    # 接受控制端的检测pcba测试完成标志的命令
    @client.route("oncheckfirst")
    def handleOnCheckFirstAction(client, action):
        if config.device.checkfirst() is False:     # checkfirst、check_cmd_exp、do_telnet、command
            data = demjson.encode({'status': 0, 'index': action.index})
        else:
            data = demjson.encode({'status': 1, 'index': action.index})
        actionReply = Action.buildReplyAction(action, "oncheckfirst",data)
        client.sendAction(actionReply)


    # 接受控制端的吞吐量测试前设备的预处理「即设置ssid和连接wifi的测试前的处理功过」命令
    @client.route("onpretreat")
    def handleOnPreTreatAction(client, action):
        if config.device.pretreat(action.mac_address) is False:
            """
            1、pretreat、set_ssid、set_ssid_of_name
               pretreat、set_ssid、joinwifi、
            2、pretreat、wait_ping_ip_start
            3、pretreat、check_resp、do_ssh、command
               pretreat、check_resp、do_telnet、command
            4、pretreat、wait_ping_ssh
               pretreat、connect_device_tel、
            """
            data = demjson.encode({'status': 0, 'index': action.index})
        else:
            data = demjson.encode({'status': 1, 'index': action.index})
        actionReply = Action.buildReplyAction(action, "onpretreat",data)
        client.sendAction(actionReply)


    # 接受控制端的mac地址比较「数据库mac地址和自己真实mac地址」的命令
    @client.route("onmacpare")
    def handleOnMacCompareAction(client, action):
        if config.device.maccompare() is False:
            """
            maccompare、check_resp、do_ssh、command、computmac
            maccompare、check_resp、do_telnet、command、computmac
            """
            data = demjson.encode({'status': 0, 'index': action.index})
        else:
            data = demjson.encode({'status': 1, 'index': action.index})
        actionReply = Action.buildReplyAction(action, "onmacpare",data)
        client.sendAction(actionReply)


    # 接受控制端的控制电源控制板的命令
    @client.route("onpower")
    def handleOnPowerAction(client, action):
        if config.device.control_power(action.count) is False:   # 这个只需要调用这个函数
            data = demjson.encode({'status': 0, 'index': action.index})
        else:
            data = demjson.encode({'status': 1, 'index': action.index})
        actionReply = Action.buildReplyAction(action, "onpower",data)
        client.sendAction(actionReply)



    # 接受控制端测试吞吐量值的rx值的命令
    @client.route("onspeedrx")
    def handleOnSpeedRxAction(client, action):
        speed = config.device.speed_rx()
        """
        1、speed_rx、wait_wget_success、check_resp、do_ssh、command
           speed_rx、wait_wget_success、check_resp、do_telnet、command
        2、speed_rx、check_resp、do_ssh、command
           speed_rx、check_resp、do_telnet、command
        """
        if speed is False:
            data = demjson.encode({'status': 0, 'index': action.index})
        else:
            data = demjson.encode({'status': 1, 'speed_rx': speed, 'index': action.index})
        actionReply = Action.buildReplyAction(action, "onspeedrx",data)
        client.sendAction(actionReply)




    # 接受控制端测试吞吐量值的tx值的命令
    @client.route("onspeedtx")
    def handleOnSpeedTxAction(client, action):
        speed = config.device.speed_tx()
        """
        1、speed_tx、wait_wget_success、check_resp、do_ssh、command
           speed_tx、wait_wget_success、check_resp、do_telnet、command
        """
        if speed is False:
            data = demjson.encode({'status': 0, 'index': action.index})
        else:
            data = demjson.encode({'status': 1, 'speed_tx': speed, 'index': action.index})
        actionReply = Action.buildReplyAction(action, "onspeedtx",data)
        client.sendAction(actionReply)

    # 接受控制端离线的命令
    @client.route("ondie")
    def handleOnDieAction(client, action):
        if config.device.offline() is False:     # 这个函数未定义
            data = demjson.encode({'status': 0, 'index': action.index})
        else:
            data = demjson.encode({'status': 1, 'index': action.index})
        actionReply = Action.buildReplyAction(action, "ondie",data)
        client.sendAction(actionReply)

    # onfivegpio()
    @client.route("ongpiofive")
    def handleOnGpioFiveAction(client, action):
        if config.device.testfivegpio() is False:
            data = demjson.encode({'status': 0, 'index': action.index})
        else:
            data = demjson.encode({'status': 1, 'index': action.index})
        actionReply = Action.buildReplyAction(action, "ongpiofive",data)
        client.sendAction(actionReply)

    # onsecondpower()
    @client.route("onsecondpower")
    def handleOnSecondPowerAction(client, action):
        if config.device.testsecondpower() is False:
            data = demjson.encode({'status': 0, 'index': action.index})
        else:
            data = demjson.encode({'status': 1, 'index': action.index})
        actionReply = Action.buildReplyAction(action, "onsecondpower",data)
        client.sendAction(actionReply)

    # testswitchleft()
    @client.route("ontestswitchleft")
    def handleOnSwitchLeftAction(client, action):
        if config.device.testswitchleft() is False:
            data = demjson.encode({'status': 0, 'index': action.index})
        else:
            data = demjson.encode({'status': 1, 'index': action.index})
        actionReply = Action.buildReplyAction(action, "ontestswitchleft",data)
        client.sendAction(actionReply)


    # onswitchmiddle()
    @client.route("ontestswitchmiddle")
    def handleTestSwitchMiddleAction(client, action):
        if config.device.testswitchmiddle() is False:
            data = demjson.encode({'status': 0, 'index': action.index})
        else:
            data = demjson.encode({'status': 1, 'index': action.index})
        actionReply = Action.buildReplyAction(action, "ontestswitchmiddle",data)
        client.sendAction(actionReply)


    @client.route("onswitchleftmid")
    def handleTestSwitchLeftMidAction(client, action):
        if config.device.testswitchleftmid() is False:
            data = demjson.encode({'status': 0, 'index': action.index})
        else:
            data = demjson.encode({'status': 1, 'index': action.index})
        actionReply = Action.buildReplyAction(action, "onswitchleftmid", data)
        client.sendAction(actionReply)


    @client.route("onswitchleftmidright")
    def handleTestSwitchLeftMidRightAction(client, action):
        if config.device.testswitchleftmidright() is False:
            data = demjson.encode({'status': 0, 'index': action.index})
        else:
            data = demjson.encode({'status': 1, 'index': action.index})
        actionReply = Action.buildReplyAction(action, "onswitchleftmidright", data)
        client.sendAction(actionReply)

    @client.route("ondowntest")
    def handleTestDownTestAction(client, action):
        if config.device.testdowntest() is False:
            data = demjson.encode({'status': 0, 'index': action.index})
        else:
            data = demjson.encode({'status': 1, 'index': action.index})
        actionReply = Action.buildReplyAction(action, "ondowntest", data)
        client.sendAction(actionReply)


    @client.route("ontestmcu")
    def handleTestDownTestAction(client, action):
        if config.device.testmcu() is False:
            data = demjson.encode({'status': 0, 'index': action.index})
        else:
            data = demjson.encode({'status': 1, 'index': action.index})
        actionReply = Action.buildReplyAction(action, "ontestmcu", data)
        client.sendAction(actionReply)


    @client.route("ontestgps")
    def handleTestDownTestAction(client, action):
        if config.device.testgps() is False:
            data = demjson.encode({'status': 0, 'index': action.index})
        else:
            data = demjson.encode({'status': 1, 'index': action.index})
        actionReply = Action.buildReplyAction(action, "ontestgps", data)
        client.sendAction(actionReply)


    @client.route("ontestdog")
    def handleTestDownTestAction(client, action):
        if config.device.testdog() is False:
            data = demjson.encode({'status': 0, 'index': action.index})
        else:
            data = demjson.encode({'status': 1, 'index': action.index})
        actionReply = Action.buildReplyAction(action, "ontestdog", data)
        client.sendAction(actionReply)


    @client.route("ontestemmc")
    def handleTestDownTestAction(client, action):
        if config.device.testemmc() is False:
            data = demjson.encode({'status': 0, 'index': action.index})
        else:
            data = demjson.encode({'status': 1, 'index': action.index})
        actionReply = Action.buildReplyAction(action, "ontestemmc", data)
        client.sendAction(actionReply)


    @client.route("onzigbee")
    def handleTestDownTestAction(client, action):
        if config.device.zigbeetest() is False:
            data = demjson.encode({'status': 0, 'index': action.index})
        else:
            data = demjson.encode({'status': 1, 'index': action.index})
        actionReply = Action.buildReplyAction(action, "onzigbee", data)
        client.sendAction(actionReply)


    @client.route("onbluetooth")
    def handleTestDownTestAction(client, action):
        if config.device.buletoothtest() is False:
            data = demjson.encode({'status': 0, 'index': action.index})
        else:
            data = demjson.encode({'status': 1, 'index': action.index})
        actionReply = Action.buildReplyAction(action, "onbluetooth", data)
        client.sendAction(actionReply)
    while True:
         time.sleep(1)







