#!/usr/bin/env python
# -*- coding: utf-8 -*-
import time
import re
import os
import requests
from comm.comm import *
from selenium import webdriver
from selenium.webdriver.firefox.firefox_binary import FirefoxBinary
import threading
from modsys4.databaseapi import test_power
from modsys4.databaseapi import updatatable_powertest

def start_firefox(html):
    capabilities = webdriver.DesiredCapabilities().FIREFOX
    capabilities["marionette"] = False
    binary = FirefoxBinary(r'/usr/bin/firefox')
    bow = webdriver.Firefox(firefox_binary=binary, capabilities=capabilities)
    bow.get("file:///home/pi/python-controler/view/"+html+".html")
    bow.maximize_window()
    return bow


## 重新开始
def begin_again(bow):
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
#将“E4:95:6E:4E:35:25'的字符串转换为251330451879205的十进制数
def mac_handle(mac1):
    mac=mac1.upper()
    mac_int=0
    #幂次方
    ex=11
    macaddress=mac.replace(':','')
    print(macaddress)
    d1 = {'0': 0, '1': 1, '2': 2, '3': 3, '4':4, '5': 5, '6': 6, '7': 7, '8': 8, '9': 9,
            'A': 10, 'B': 11, 'C': 12, 'D': 13, 'E': 14, 'F': 15}
    for i in macaddress:
        mac_int=mac_int+d1[i]*(16**ex)
        ex=ex-1
    return mac_int

#将251330451879205的十进制数转换为的“E4:95:6E:4E:35:25'字符串
def mac_handle_str(mac):
    mac_hex=str(hex(mac))[2:].upper()
    mac_hex_str=mac_hex[0:2]+":"+mac_hex[2:4]+":"+mac_hex[4:6]+":"+mac_hex[6:8]+":"+mac_hex[8:10]+":"+mac_hex[10:12]
    return mac_hex_str

#将E4:95:6E:4E:35:25加1变为E4:95:6E:4E:35:26的字符串
def mac_add(mac):
    mac_int=mac_handle(mac)
    mac_add=mac_int+1
    mac_add1=mac_handle_str(mac_add)
    return mac_add1
#获取2G的ssid
def ssid_2G(mac1,bow):
    if code:
        device_type=get_test_device_type(bow)
        mac=(mac1[-4]+mac1[-2:]).lower()
        ssid_info=device_type+"-"+mac
        if "GL-CORE"==device_type:
            ssid_info = "Domino-"+mac
        elif "GL-MT300N-V3"==device_type:
            ssid_info = "VIXMINI-"+mac
        elif "GL-AR300M-double-flash" == device_type:
            ssid_info = "GL-AR300M-"+mac
        return ssid_info

#获取5G的ssid
def ssid_5G(mac1,bow):
    if code:
        device_type=get_test_device_type(bow)
        mac=(mac1[-4]+mac1[-2:]).lower()
        ssid_info=device_type+"-"+mac+"-5G"
        if "GL-CORE"==device_type:
            ssid_info = "Domino-"+mac+'-5G'
        elif "GL-MT300N-V3"==device_type:
            ssid_info = "VIXMINI-"+mac+'-5G'
        elif "GL-AR300M-double-flash" == device_type:
            ssid_info = "GL-AR300M-"+mac+'-5G'
        return ssid_info


 # 对比mac和ssid
def ssid_mac_cmp(s,mac,ssid):
    mac=mac.lower()
    if mac in s:
        if ssid in s:
            return True
        else:
            return False
    else:
        return False

#获取信息
def get_info_b1300():
    try:
        mac_ssid_2G=requests.get("http://192.168.3.1/2g_b1300",verify=False,timeout=8)
    except:
        return False
    mac_ssid_2G.encoding = "utf-8"
    mac_ssid_2G = mac_ssid_2G.text
    try:
        mac_ssid_5G = requests.get("http://192.168.3.1/5g_b1300", verify=False,timeout=8)
    except:
        return False
    mac_ssid_5G.encoding = "utf-8"
    mac_ssid_5G = mac_ssid_5G.text
    return mac_ssid_2G + mac_ssid_5G

def test_start(bow):
    name = bow.find_element_by_id("begin").text
    if name == u"开始测试...":
        return True
    else:
        return False

def test_fail(bow,id):
    js = 'document.getElementById("%s").setAttribute("class","btn btn-lg btn-danger");' % id
    bow.execute_script(js)
    js = '$("#%s").text("失败")'%id
    bow.execute_script(js)

def test_succeed(bow,id):
    js = 'document.getElementById("%s").setAttribute("class","btn btn-lg btn-success");' %id
    bow.execute_script(js)
    js = '$("#%s").text("成功")'%id
    bow.execute_script(js)
bow = start_firefox('mac_ssid')
while 1:
    if test_start(bow):
        time.sleep(10)
        mac_ssid_info=get_info_b1300()
        if not mac_ssid_info:
            print("抓包设备未连接,请连接设备")
            begin_again(bow)
            continue
        print(mac_ssid_info)
        code_id = 1
        device_type = get_test_device_type(bow)
        while True:
            if code_id == 29:
                begin_again(bow)
                break
            id = 'rou_info' + str(code_id)
            code = bow.find_element_by_id(id).get_attribute("value")
            if code == '':
                begin_again(bow)
                break
            status_id="status" + str(code_id)
            try:
                code = get_code_of_rou(id,status_id,bow)
            except:
                js = '$("#%s").text("数据库无此数据")' % status_id  # code  qj00001 6ae6ef0823d24925
                bow.execute_script(js)
                code_id = code_id + 1
                continue
            if not code:
                print(code)
                code_id=code_id+1
                continue
            state_id='status'+str(code_id)
            js = '$("#{}").text("{}")'.format(state_id, "正在测试中")
            bow.execute_script(js)
            mac_2G = get_mac_from_code(code)
            #检测是否通过功率测试
            try:
                print(1111111111111111111111111)
                print(mac_2G.upper())
                test_pass=test_power(mac_2G.upper())
                print(test_pass)
                print(123455667)
            except:
                print('ddsdsdsdf')
            if test_pass[0][0] != "PASS":
                print("pass")
                js = '$("#%s").text("设备未进行功率测试")' % status_id
                bow.execute_script(js)
                code_id = code_id + 1
                continue
            mac_2g_ssid= ssid_2G(mac_2G,bow)
            mac_5G= mac_add(mac_2G)
            mac_5g_ssid = ssid_5G(mac_2G, bow)
            print('mac_2G----',mac_2G)
            mac_2G = mac_2G.lower()
            mac1_2G = mac_2G.upper()
            mac_5G = mac_5G.lower()
            print(mac_2g_ssid)
            print(mac_5G)
            print(mac_5g_ssid)
            if mac_2G in mac_ssid_info and mac_2g_ssid in mac_ssid_info:
                id = 'tx'+str(code_id)
                test_succeed(bow, id)
                sql="UPDATE device SET throughput_rx='2G测试成功' WHERE mac_address='%s'"%mac1_2G
                updatatable_powertest(sql)
            else:
                id = 'tx' + str(code_id)
                test_fail(bow, id)
                sql = "UPDATE device SET throughput_rx='2G测试失败' WHERE mac_address='%s'" % mac1_2G
                updatatable_powertest(sql)
            if device_type not in ['GL-AR150']:
                if mac_5G in mac_ssid_info and mac_5g_ssid in mac_ssid_info:
                    id = 'rx'+str(code_id)
                    test_succeed(bow, id)
                    sql = "UPDATE device SET throughput_tx='5G测试成功' WHERE mac_address='%s'" % mac1_2G
                    updatatable_powertest(sql)
                else:
                    sql = "UPDATE device SET throughput_tx='5G测试失败' WHERE mac_address='%s'" % mac1_2G
                    updatatable_powertest(sql)
                    id = 'rx' + str(code_id)
                    test_fail(bow, id)
            else:
                sql = "UPDATE device SET throughput_tx='2G测试成功' WHERE mac_address='%s'" % mac1_2G
                updatatable_powertest(sql)

            state_id = 'status' + str(code_id)
            js = '$("#{}").text("{}")'.format(state_id, "测试完成")
            bow.execute_script(js)
            code_id = code_id + 1
    time.sleep(2)

