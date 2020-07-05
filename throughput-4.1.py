#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@author: huyiyong
@file: throughput.py
@time: 2017/10/24 14:28
"""
import platform
import time
import re
import os
import comm.config as config
import requests
from modsys4.sys4 import SystemF # 4.1过度系统
from comm.head import count_to_power_port
from comm.comm import *
from selenium import webdriver
from selenium.webdriver.firefox.firefox_binary import FirefoxBinary
## 启动浏览器
def start_firefox(html,os_type):
    if "Window" in os_type:
        bow = webdriver.Firefox()
        bow.get("file:///d:~/python-controler/view/"+html+".html")
    else:
        capabilities = webdriver.DesiredCapabilities().FIREFOX
        capabilities["marionette"] = False
        binary = FirefoxBinary(r'/usr/bin/firefox')
        bow = webdriver.Firefox(firefox_binary=binary, capabilities=capabilities)
        bow.get("file:///home/pi/python-controler/view/"+html+".html")
        bow.maximize_window()
    return bow

## 计算下一个mac地址
def computmac(macaddr):
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
# 兼容统一，作为过渡系统
class Action(object):
    pass

## 检测是否开始
def check_test3_start(bow,count,device_type):
    name = bow.find_element_by_id("begin").text
    if name == u"开始测试...":
        config.startflg = False
        action = Action()
        action.device_type = device_type
        action.step = 'third'
        config.device = SystemF(action)
        config.device.control_power(1)
        if config.testMes == 'd':
            config.device.control_power(2)
        js = '$("#begin").text("正在测试中")'
        bow.execute_script(js)
        js = "document.getElementById(\"begin\").setAttribute(\"class\",\"btn btn-lg btn-success\");"
        bow.execute_script(js)
        return True
    else:
        if config.startflg:
            time.sleep(2)
            return False
        else:
            return True

## 从count获取需要标志的信息
def get_info_from_count(count):
    power_of_port = count_to_power_port[count]      # 获取到电源板的端口
    rou_info_id = "rou_info" + str(count)
    state_id = "status" + str(count)
    return power_of_port,rou_info_id,state_id      # 组织电源相应的参数

## 从扫码获取到Mac地址
def get_mac_from_code(code):
    print "the code is:",code
    print "the len of code:",len(code)
    if len(code) == 17:
        return code
    else:
        code_tuple = split_code(code)
        ddns_name = get_two_par_from_code_tuple(code_tuple)
        payload = { 'action': 'getDeviceInfo', 'ddns_name': ddns_name }
        re = requests.get("http://192.168.16.17/api.php", params=payload)           # 这里面传递过来的参数是什么
        print re.json()[0]
    return re.json()[0]['mac_address']

## 重新开始
def begin_again(bow,device_type="linux"):
    config.startflg = True
    js = '$("#begin").text("开始测试")'
    bow.execute_script(js)
    js = "document.getElementById(\"begin\").setAttribute(\"class\",\"btn btn-lg btn-danger\");"
    bow.execute_script(js)
    js = '$("#begin").attr("disabled", false)'
    bow.execute_script(js)

## 获取设备类型
def get_test_device_type(bow):
    pass_route = bow.find_element_by_id("select-route").get_attribute("value").encode('UTF-8')
    if pass_route == "":
      return False
    js = '$(\"#device_type\").text(\"%s\")'%pass_route
    bow.execute_script(js)
    return pass_route

## 获取code值
def get_code_of_rou(id,status_id,bow):
    code = bow.find_element_by_id(id).get_attribute("value")
    if len(code) != 24 and len(code) != 42 and len(code) != 17:
        js = '$("#%s").text("长度不对")' % status_id  # code  qj00001 6ae6ef0823d24925
        bow.execute_script(js)
        time.sleep(1)
        return False
    return code
## 将测试三的数据写入数据库中
def write_test3_data_to_database(speed_down_re,speed_on_re,ddns_name):
    print "begin write to database"
    payload = { 'action': 'updateThrough', 'ddns_name': ddns_name,'throughput_rx': speed_down_re,'throughput_tx': speed_on_re }
    r = requests.get("http://192.168.16.17/api.php", params=payload)
    print r.json()
    print "write to database is over"
    print "begin write to file"

## 设置错误信息
def seterr(desc,count,num=28):
    print "next while begin"
    state_id = "status" + str(count)
    if count != num:
        print "hh"
        config.count = count + 1
        if count != num-1:
            if config.testMes == 'd':
                config.device.control_power(config.count+1)
            else:
                config.device.control_power(config.count)
            js = '$("#begin").text("正在测试中")'
            bow.execute_script(js)
            js = "document.getElementById('begin').setAttribute('class','btn btn-lg btn-success');"
            bow.execute_script(js)
            js = '$("#{}").text("{}")'.format(state_id,desc)
            bow.execute_script(js)
    else:
        print "while down"
        js = "document.getElementById('begin').setAttribute('class','btn btn-lg btn-success');"
        bow.execute_script(js)
        js = '$("#{}").text("{}")'.format(state_id,desc)
        bow.execute_script(js)
        config.count = 1
        config.device.control_power(1)
        if config.testMes == 'd':
            config.device.control_power(2)
        print "next while begin"
        begin_again(bow)

## 比较speed值,并进行下一次的更新
def setcomp(desc,speed,count):
    rout = "{}_pass-route".format(desc)
    if "5G" in config.device_type:
        if config.device_type ==  'GL-AR750-5G':
            int_speed_success = 185
        elif config.device_type == 'GL-B1300-5G':
            int_speed_success = 260
	elif config.device_type == 'GL-AR750S-5G':
            int_speed_success = 200
    else:
        speed_success = bow.find_element_by_id(rout).get_attribute("value")
        int_speed_success = float(re.findall("(.*)\s", speed_success)[0])
    txid = desc + str(config.count)
    if speed < int_speed_success:
        js = 'document.getElementById("%s").setAttribute("class","btn btn-lg btn-danger");' % txid
        bow.execute_script(js)
        js = '$("#{}").text("{}|{}")'.format(txid, speed,config.device_type)
        bow.execute_script(js)
        return False
    else:
        js = 'document.getElementById("%s").setAttribute("class","btn btn-lg btn-success");' % txid
        bow.execute_script(js)
        js = '$("#{}").text("{}|{}")'.format(txid, speed,config.device_type)
        bow.execute_script(js)
        return True

os_type = platform.platform()
bow = start_firefox('throughput', os_type)                      # 这个就是建立一个打开这个设备的浏览器对象
filename = __file__
num = 28


while True:
    try:
        print "start"
        count = config.count                                                    # 这个count就是板子的端口
        if "5G" not in config.device_type:                                     # 以目前的情况来看，全都不是5G
            print "不是5G"
            device_type = get_test_device_type(bow)                             # 这个代码就是用来接收是哪个设备
            if device_type:
                config.device_type = device_type                                # 到这里是确定这个设备的类型
        if config.device_type == "GL":                                         # 相当于没有获取设备就直接结束本次循环
            continue
        if check_test3_start(bow,count,config.device_type) is False:           # 检测是否开始测试
            continue
        power_of_port,rou_info_id,state_id = get_info_from_count(count)        # 获取到相应电源端口的信息
        print "rou_info_id:", rou_info_id
        code = get_code_of_rou(rou_info_id,state_id,bow)                       # 获取到code值
        print code
        if code is False:
            pre_power_of_port,pre_rou_info_id,pre_state_id = get_info_from_count(count-1)
            pre_code = get_code_of_rou(pre_rou_info_id,pre_state_id,bow)
            if pre_code is False:
                seterr("长度不对",count,count)
            else:
                seterr("长度不对",count)
            continue
        mac = get_mac_from_code(code)                                         # 获取到mac值
	print mac
        if mac is False:
            seterr("mac地址不存在",count)
            continue
        t1 = time.time()
        if config.device.pretreat(mac) is False:                            # 连接wifi
            seterr('连接失败', count)
            continue
        js = "document.getElementById('{}').setAttribute('class','btn btn-lg btn-success');".format(state_id)
        bow.execute_script(js)
        js = '$("#{}").text("{}")'.format(state_id,"正在测试中")
        bow.execute_script(js)
        if config.device_type == 'GL-CORE':
            speed_rx = 0
            speed_tx = 0
        else:
            speed_rx = float(config.device.speed_r())                            # 测试接受的吞吐量
            if speed_rx is False:
                seterr('speed_rx测试失败',count)
                continue
            else:
                config.rx = setcomp('rx',speed_rx,count)
            speed_tx = float(config.device.speed_t())                            # 测试发出的吞吐量
            if speed_tx is False:
                seterr("speed_tx测试失败",count)
                continue
            else:
                config.tx = setcomp('tx',speed_tx,count)

        if "5G" in config.device_type:
            macd = computmac(mac)
            print macd
            code = get_ddns_code_from_mac(macd)
            print code
        else:
            code = get_ddns_code_from_mac(mac)
        print code
        write_test3_data_to_database(speed_rx,speed_tx,code)
        if config.device_type in ["GL-AR750","GL-B1300"]:
            print "开始切换"
            if config.rx and config.tx:
                if get_test_device_type(bow) == "GL-AR750":
                    config.device_type = "GL-AR750-5G"
                    action = Action()
                    action.device_type = "GL-AR750-5G"
                    action.step = 'third'
                    config.device = SystemF(action)
                    continue
                elif get_test_device_type(bow) == "GL-B1300":
                    config.device_type = "GL-B1300-5G"
                    action = Action()
                    action.device_type = "GL-B1300-5G"
                    action.step = 'third'
                    config.device = SystemF(action)
                    continue
        t2 = time.time()
        print "&"*80
        print "&          测试时间为: {}                  &".format(int(t2-t1))
        print "&"*80
        if "5G" not in config.device_type:
            if config.device.maccompare() is False:
                seterr('mac地址比较失败',count)
                continue
        if "5G" in config.device_type:
            if get_test_device_type(bow) == "GL-AR750":
                config.device_type = "GL-AR750"
                action = Action()
                action.device_type = "GL-AR750"
                action.step = 'third'
                config.device = SystemF(action)
            elif get_test_device_type(bow) == "GL-B1300":
                config.device_type = "GL-B1300"
                action = Action()
                action.device_type = "GL-B1300"
                action.step = 'third'
                config.device = SystemF(action)
        seterr('测试成功',count)
    except Exception,e:
        print e
        seterr('发生异常',count)
        continue
