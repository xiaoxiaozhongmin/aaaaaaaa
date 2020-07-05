#!/usr/bin/env python
#encoding: utf-8
import MySQLdb
import datetime
import sys

def get_con(logsdbname):
    host = "192.168.16.17"
    port = 3306
    logsdb = logsdbname
    user = "root"
    password = "goodlife1"
    con = MySQLdb.connect(host=host, user=user, passwd=password, db=logsdb, port=port, charset='utf8')
    return con

def updatatable(data,macadress):
    reload(sys)
    sys.setdefaultencoding("utf-8")
    conn = get_con("testproduct")
    cursor = conn.cursor()
    sql="update art set art=(%s) where mac_address=(%s)"
    cursor.execute(sql,(data,macadress))
    conn.commit()
    cursor.close()
    conn.close()

def updatatable1(sql,data,macadress):
    reload(sys)
    sys.setdefaultencoding("utf-8")
    conn = get_con("testproduct")
    cursor = conn.cursor()
    cursor.execute(sql,(data,macadress))
    conn.commit()
    cursor.close()
    conn.close()

#将“E4:95:6E:4E:35:25'的字符串转换为251330451879205的十进制数
def mac_handle(mac):
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

#将单频后二个mac地址的used标记为1
def updatatable_used(macadress,product_type):
    product_type1=product_type+'-LAN'
    product_type2 = product_type + '-2.4G'
    mac = mac_handle(macadress)
    mac1 = mac+1
    mac2 = mac+2
    mac1 = mac_handle_str(mac1)
    mac2 = mac_handle_str(mac2)
    print mac1
    print mac2
    reload(sys)
    sys.setdefaultencoding("utf-8")
    conn = get_con("testproduct")
    cursor = conn.cursor()
    now_time = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    sql = "update device set used='2',product_type='%s',product_test_time='%s' where mac_address='%s'" % (product_type1,now_time, mac1)
    print sql
    cursor.execute(sql)
    sql = "update device set used='2',product_type='%s',product_test_time='%s' where mac_address='%s'" % (product_type2,now_time, mac2)
    print sql
    cursor.execute(sql)
    conn.commit()
    cursor.close()
    conn.close()
#将单频后二个mac地址的used标记为3
def updatat_mark3_used(macadress):
    mac = mac_handle(macadress)
    mac1 = mac+1
    mac2 = mac+2
    mac1 = mac_handle_str(mac1)
    mac2 = mac_handle_str(mac2)
    reload(sys)
    sys.setdefaultencoding("utf-8")
    conn = get_con("testproduct")
    cursor = conn.cursor()
    sql = "update device set used='3'where mac_address='%s' or mac_address='%s' or mac_address='%s'" % (macadress,mac1,mac2)
    print sql
    cursor.execute(sql)
    conn.commit()
    cursor.close()
    conn.close()

#将单频后二个mac地址的used标记为3
def updatat_mark4_used(macadress):
    mac = mac_handle(macadress)
    mac1 = mac+1
    mac2 = mac+2
    mac3=mac+3
    mac1 = mac_handle_str(mac1)
    mac2 = mac_handle_str(mac2)
    mac3 = mac_handle_str(mac3)
    reload(sys)
    sys.setdefaultencoding("utf-8")
    conn = get_con("testproduct")
    cursor = conn.cursor()
    sql = "update device set used='3' where mac_address='%s' or mac_address='%s' or mac_address='%s' or mac_address='%s'" % (macadress,mac1,mac2,mac3)
    cursor.execute(sql)
    conn.commit()
    cursor.close()
    conn.close()

#将单频后二个mac地址的used标记为1
def updatatable_used3(macadress,product_type):
    mac = mac_handle(macadress)
    product_type1=product_type+'-LAN'
    product_type2 = product_type + '-2.4G'
    product_type3 = product_type + '-5G'
    mac1 = mac+1
    mac2 = mac+2
    mac3 = mac + 3
    mac1 = mac_handle_str(mac1)
    mac2 = mac_handle_str(mac2)
    mac3 = mac_handle_str(mac3)
    print mac1
    print mac2
    reload(sys)
    sys.setdefaultencoding("utf-8")
    conn = get_con("testproduct")
    cursor = conn.cursor()
    now_time = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    sql="update device set used='2',product_type='%s',product_test_time='%s' where mac_address='%s'"%(product_type1,now_time,mac1)
    print sql
    cursor.execute(sql)
    sql = "update device set used='2',product_type='%s',product_test_time='%s' where mac_address='%s'" % (product_type2,now_time, mac2)
    print sql
    cursor.execute(sql)
    sql = "update device set used='2',product_type='%s',product_test_time='%s' where mac_address='%s'" % (product_type3,now_time, mac3)
    print sql
    cursor.execute(sql)
    conn.commit()
    cursor.close()
    conn.close()

#获取数据库功率测试是否通过
def test_power(macadress):
    print(1)
    reload(sys)
    sys.setdefaultencoding("utf-8")
    conn = get_con("testproduct")
    cursor = conn.cursor()
    sql="SELECT power_result from device WHERE mac_address='%s'"%macadress
    cursor.execute(sql)
    results = cursor.fetchall()
    conn.commit()
    cursor.close()
    conn.close()
    return results


#获取数据库功率测试2G或者5G通过的写入
def updatatable_powertest(sql):
    reload(sys)
    sys.setdefaultencoding("utf-8")
    conn = get_con("testproduct")
    cursor = conn.cursor()
    cursor.execute(sql)
    conn.commit()
    cursor.close()
    conn.close()




