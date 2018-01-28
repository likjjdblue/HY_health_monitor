#-*- encoding:utf-8 -*-
#!/usr/bin/env python
Version='1.0'

import nodeinfo
from socket import socket,AF_INET,SOCK_STREAM
from os import geteuid,path,walk
from os import path,makedirs
import subprocess
import httplib
import json
import codecs
import re
from copy import deepcopy

TextColorRed='\x1b[31m'
TextColorGreen='\x1b[32m'
TextColorWhite='\x1b[0m'

def getSelfVersion():
    print (Version)
    return Version

def checkRemotePort(ip,port):
    ###  检查参数是否有异常 ###
    if (isinstance(ip,str) or (isinstance(ip,unicode))) and (isinstance(port,int)):
        port=int(port)
    else:
        return {'RetCode':2,
                'FeedBack':u'调用checkRemotePort 参数异常:'+str(ip)+' '+str(port)}
    try:
        s=socket(AF_INET,SOCK_STREAM)
        s.settimeout(1)
        s.connect((ip,port))
        s.close()
        return {'RetCode':0,
                'FeedBack':u'正常访问 '+str(ip)+':'+str(port)}
    except:
        return {'RetCode':1,
                'FeedBack':u'无法访问 '+str(ip)+':'+str(port)}
    finally:
        del s



def checkRootPrivilege():
###  检查脚本的当前运行用户是否是 ROOT ###
  RootUID=subprocess.Popen(['id','-u','root'],stdout=subprocess.PIPE).communicate()[0]
  RootUID=RootUID.strip()
  CurrentUID=geteuid()
  return str(RootUID)==str(CurrentUID)


def extractLocalIP():
    ###   提取本机IP 地址   ###
    return subprocess.Popen("ip addr|grep 'state UP' -A2|tail -n1|awk '{print $2}'|cut -f 1 -d '/'",
                            shell=True,stdout=subprocess.PIPE).communicate()[0].strip()

def compareVersionString(strA,strB):
    ####  对两个版本号进行比较，并返回比较结果;  版本号以'.'分割;
    ####  0:版本号相同；1：strA是最新的版本；2：strB是最新的版本

    strA=strA.strip()
    strB=strB.strip()

    TmpListA=strA.split('.')
    TmpListB=strB.split('.')
    TmpListLengthA=len(TmpListA)
    TmpListLengthB=len(TmpListB)

    for index in range(min(TmpListLengthA,TmpListLengthB)):
        if int(TmpListA[index])>int(TmpListB[index]):
           return 1
        elif int(TmpListA[index])<int(TmpListB[index]):
           return 2
        else:
           continue

    if TmpListLengthA>TmpListLengthB:
        return 1
    elif TmpListLengthA<TmpListLengthB:
        return 2
    else:
        return 0
     
 


def sendHttpRequest(host='127.0.0.1',port=80,url='/',method='GET',body={},header={},timeout=1):
#### 调用特定的 web API,并获取结果 ###
### 函数返回Dict 类型，其中'RetCode'，标识是否异常 0:正常，非0：异常
### 'Result'是具体结果

     try:
        tmpBody=json.dumps(body)
        HttpObj=httplib.HTTPConnection(host,port,timeout=timeout)
        HttpObj.request(url=url,method=method,body=tmpBody,headers=header)
        ResponseObj=HttpObj.getresponse()
        tmpDict={'HttpContent':ResponseObj.read(),
                 'HttpStatus':ResponseObj.status,
                 'HttpReason':ResponseObj.reason,
                 }
        return {'RetCode':0,
                 'FeedBack':tmpDict}
     except Exception as e:
        return {'RetCode':1,
               'FeedBack':TextColorRed+str(e)+TextColorWhite}


class IGICheck:
    ###  对“问政互动”进行健康度检查 ####
    def __init__(self,projectpath):
        projectpath=str(projectpath)
        if not path.isdir(projectpath):
            raise Exception(projectpath+' 不是有效的目录路径')

        self.ProjectPath=projectpath


    def checkHealth(self):
        print (u'即将对"问政互动-政务外网 服务进行自检，请稍后......."')
        BaseDirectory=path.dirname(path.abspath(__file__))
        TmpHiddenPath=path.join(BaseDirectory,r'.tmp/IGI')

        if not path.isdir(TmpHiddenPath):
           makedirs(TmpHiddenPath)

        ### 检查IGI config-1.0-SNAPSHOT.jar  是否存在；####
        TargetIGIJarFile=path.join(self.ProjectPath,r'webapps/IGI/WEB-INF/lib/config-1.0-SNAPSHOT.jar')
        if not path.isfile(TargetIGIJarFile):
            print (TextColorRed+'IGI 目标jar包不存在，无法检查"问政互动"'+TextColorWhite)
            return 1

       
        cmdline='cd %s;cp %s %s;'%(TmpHiddenPath,TargetIGIJarFile,TmpHiddenPath)
        subprocess.call('cd %s;cp %s %s;'%(TmpHiddenPath,TargetIGIJarFile,TmpHiddenPath),shell=True)
        subprocess.call('cd %s;unzip -o %s >/dev/null'%(TmpHiddenPath,'config-1.0-SNAPSHOT.jar'),shell=True)
        subprocess.call('cd %s;rm -f config-1.0-SNAPSHOT.jar'%(TmpHiddenPath,),shell=True)

    
        #### 解析配置文件  application.properties ###
        with codecs.open(path.join(TmpHiddenPath,'application.properties'),'r','utf-8') as f:
             TmpFileContent=f.read()

        #### 版本号 ###
        ReObj=re.search(r'^\s*build.version.number\s*=(.*?)\s*\n',TmpFileContent,flags=re.UNICODE|re.MULTILINE)
        if ReObj:
             print (TextColorGreen+u'问政互动当前版本号：'+ReObj.group(1).strip()+TextColorWhite)
        else:
             print (u'无法检查到版本信息\n')

        #### Mysql 相关  ###
        ReObjA=re.search(r'^\s*spring\.datasource\.url=jdbc:mysql://(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}):(\d{1,5})/(.*?)\?',TmpFileContent,flags=re.UNICODE|re.MULTILINE)
        ReObjB=re.search(r'^\s*spring\.datasource\.username=(.*?)\n',TmpFileContent,flags=re.UNICODE|re.MULTILINE)
        ReObjC=re.search(r'^\s*spring\.datasource\.password=(.*?)\n',TmpFileContent,flags=re.UNICODE|re.MULTILINE)

        if ReObjA and ReObjB and ReObjC:
           TmpIGIDBNode=deepcopy(nodeinfo.igiDBInfo)

           TmpIGIDBNode['igidb']['host']=ReObjA.group(1).strip()
           TmpIGIDBNode['igidb']['port']=int(ReObjA.group(2).strip())
           TmpIGIDBNode['igidb']['database']=ReObjA.group(3).strip()
           TmpIGIDBNode['igidb']['user']=ReObjB.group(1).strip()
           TmpIGIDBNode['igidb']['password']=ReObjC.group(1).strip()

           print (u'检测MYSQL 连接情况.........')
           TmpDatabaseState=checkRemotePort(TmpIGIDBNode['igidb']['host'],TmpIGIDBNode['igidb']['port'])
           if TmpDatabaseState['RetCode']==0:
              print (TextColorGreen+TmpDatabaseState['FeedBack']+TextColorWhite)
           else:
              print (TextColorRed+TmpDatabaseState['FeedBack']+TextColorWhite)
              print ('请检查MYSQL  是否正常运行，以及端口是否开放')
        else:
            print (TextColorRed+'无法获取MYSQL 配置信息,跳过MYSQL 检查'+TextColorWhite)    


        #####  与IDS 交互相关 ####
        print (u'正在测试 "问政互动-政务外网"与IDS的连通性........')
        ReObj=re.search(r'^\s*ids\.service\.url=http://(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})(:\d{1,5})?(.*?)\n',TmpFileContent,flags=re.UNICODE|re.MULTILINE)
        if ReObj:
           TmpPort=int(ReObj.group(2).strip(':').strip()) if ReObj.group(2) else 80      ###如果指定了端口，就使用配置文件里面的端口，否则默认为80  ##
           TmpHost=ReObj.group(1).strip()
           TmpURL=ReObj.group(3).strip()

           TmpHttpResponse=sendHttpRequest(host=TmpHost,port=TmpPort,url=TmpURL)
#           print (TmpHttpResponse)
           if TmpHttpResponse['RetCode']==1:
              print (TextColorRed+'测试与IDS 连接过程中发生错误,HTTP 请求失败: '+'http://'+str(TmpHost)+':'+str(TmpPort)+str(TmpURL)+TextColorWhite)
              print ("该问题可能是IDS 停止服务，或者NGINX代理异常!\n")
           elif TmpHttpResponse['RetCode']==0:
                TmpHttpStatusCode=int(TmpHttpResponse['FeedBack']['HttpStatus'])
#                print (str(TmpHttpStatusCode))
                if TmpHttpStatusCode>=200 and TmpHttpStatusCode<=399:
                   print (TextColorGreen+'可以正常访问 IDS'+TextColorWhite)
                else:
                   print (TextColorRed+'测试与IDS 连接过程中发生错误,HTTP 请求失败: '+'http://'+str(TmpHost)+':'+str(TmpPort)+str(TmpURL)+TextColorWhite)
                   print ("该问题可能是IDS 停止服务，或者NGINX代理异常!\n")


        ####  与rabbitmq 的连通性    ###
        print (u'即将测试与Rabbitmq 的连通性......')
        ReObjA=re.search(r'^\s*MQ_HOSTS\s*=\s*(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})\s*\n',TmpFileContent,flags=re.UNICODE|re.MULTILINE)
        ReObjB=re.search(r'^\s*MQ_PORT\s*=\s*(\d{1,5})\s*\n',TmpFileContent,flags=re.MULTILINE|re.UNICODE)
        ReObjC=re.search(r'^\s*MQ_USERNAME\s*=\s*(.*?)\s*\n',TmpFileContent,flags=re.MULTILINE|re.UNICODE)
        ReObjD=re.search(r'^\s*MQ_PASSWORD\s*=\s*(.*?)\s*\n',TmpFileContent,flags=re.UNICODE|re.MULTILINE)

        if ReObjA and ReObjB and ReObjC and ReObjD:
            TmpRabbitmqNode=deepcopy(nodeinfo.rabbitmqNodeInfo) 

            TmpRabbitmqNode['rabbitmq']['host']=ReObjA.group(1).strip()
            TmpRabbitmqNode['rabbitmq']['port']=int(ReObjB.group(1).strip())
            TmpRabbitmqNode['rabbitmq']['user']=ReObjC.group(1).strip()
            TmpRabbitmqNode['rabbitmq']['password']=ReObjD.group(1).strip()              
            
            TmpResult=checkRemotePort(TmpRabbitmqNode['rabbitmq']['host'],TmpRabbitmqNode['rabbitmq']['port'])
            if TmpResult['RetCode']==0:
               print (TextColorGreen+TmpResult['FeedBack']+u'\n与Rabbitmq 连接正常'+TextColorWhite)
            elif TmpResult['RetCode']==1:
               print (TextColorRed+TmpResult['FeedBack']+TextColorWhite)
               print (u'请检查rabbitmq是否启动，并且端口是否开放。\n')

        ###  清理临时文件   ###
        subprocess.call('cd %s && rm -f -r %s/**'%(TmpHiddenPath,TmpHiddenPath),shell=True)

       
class  IGSCheck:
   def __init__(self,projectpath):
      if not path.isdir(projectpath):
         raise Exception(projectpath+u'不是有效的目录路径')
      self.ProjectPath=projectpath

   def checkHealth(self):
       BaseDirectory=path.dirname(path.abspath(__file__))
       TmpHiddenPath=path.join(BaseDirectory,r'.tmp/IGS')
       if not path.isdir(TmpHiddenPath):
          makedirs(TmpHiddenPath)

       print (u'即将对"智能检索"进行自检，请稍候......')
       TargetIGSFolder=path.join(self.ProjectPath,r'webapps/igs/WEB-INF/classes')
       if not path.isdir(TargetIGSFolder):
           print (TextColorRed+u'无法获取IGS 配置文件，无法检查"智能检索"'+TextColorWhite)
           return 1
       
       subprocess.call('cp -r %s %s'%(TargetIGSFolder+r'/*',TmpHiddenPath),shell=True)
   
       ######  分析配置文件 application.properties    ###
       with codecs.open(path.join(TmpHiddenPath,'application.properties'),'r','utf-8') as f:
           TmpFileContent=f.read()
       
       #### 获取版本号   ###
       ReObj=re.search(r'\s*build.number=(.*?)\s*\n',TmpFileContent,flags=re.MULTILINE|re.UNICODE)
       if ReObj:
            print (TextColorGreen+u'检测到智能检索当前版本：'+ReObj.group(1)+TextColorWhite)

   
       #####  elasticsearch 相关  ###
       print (u'即将检查"智能检索"与elasticsearch的连通性......')
       ReObj=re.search(r'^spring.data.elasticsearch.cluster-nodes=(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}):(\d{1,5})',TmpFileContent,flags=re.UNICODE|re.MULTILINE) 
       if ReObj:
          TmpElasticsearchNode=deepcopy(nodeinfo.elasticsearchNodeInfo)
          TmpElasticsearchNode['elasticsearch']['host']=ReObj.group(1).strip()
          TmpElasticsearchNode['elasticsearch']['port']=int(ReObj.group(2).strip())
          
          TmpResult=checkRemotePort(TmpElasticsearchNode['elasticsearch']['host'],
                                    TmpElasticsearchNode['elasticsearch']['port'])
   
          if TmpResult['RetCode']==0:
             print (TextColorGreen+TmpResult['FeedBack']+TextColorWhite)
             print (TextColorGreen+u'“智能检索”连接Elasticsearch正常\n'+TextColorWhite)
          else:
             print (TextColorRed+TmpResult['FeedBack']+TextColorWhite)
             print (TextColorRed+u'“智能检索”无法连接Elasticsearch,\n请检查elasticsearch是否正常运行，以及端口是否开放。\n'+TextColorWhite)
       else:
           print (TextColorRed+u'无法获取elasticsearch信息，或elasticsearch配置信息不全；跳过检测。'+TextColorWhite)

       ####   MYSQL 相关 ####
       print (u'即将检查"智能检索"与MYSQL 的连通性......')
       ReObjA=re.search(r'^\s*spring\.datasource\.url=jdbc:mysql://(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}):(\d{1,5})/(.*?)\?',TmpFileContent,
                        flags=re.UNICODE|re.MULTILINE)
       ReObjB=re.search(r'^\s*spring\.datasource\.username=(.*?)\s*\n',TmpFileContent,flags=re.UNICODE|re.MULTILINE)
       ReObjC=re.search(r'^\s*spring\.datasource\.password=(.*?)\s*\n',TmpFileContent,flags=re.UNICODE|re.MULTILINE)


       if ReObjA and ReObjB and ReObjC:
          TmpIGSDBNode=deepcopy(nodeinfo.igsDBInfo)

          TmpIGSDBNode['igsdb']['host']=ReObjA.group(1).strip()
          TmpIGSDBNode['igsdb']['port']=int(ReObjA.group(2).strip())
          TmpIGSDBNode['igsdb']['database']=ReObjA.group(3).strip()

          TmpIGSDBNode['igsdb']['user']=ReObjB.group(1).strip()
          TmpIGSDBNode['igsdb']['password']=ReObjC.group(1).strip()

          TmpResult=checkRemotePort(TmpIGSDBNode['igsdb']['host'],TmpIGSDBNode['igsdb']['port'])

          if TmpResult['RetCode']==0:
             print (TextColorGreen+TmpResult['FeedBack']+TextColorWhite)
             print (TextColorGreen+u'“智能检索”访问 MYSQL 正常\n'+TextColorWhite)
          else:
             print (TextColorRed+TmpResult['FeedBack']+TextColorWhite)
             print (TextColorRed+u'“智能检索”无法访问MYSQL,'+TextColorWhite)
             print (TextColorRed+u'请检查Mysql是否正常运行，已经端口是否开放。\n'+TextColorWhite)
       else:
           print (TextColorRed+u'无法获取Mysql配置信息，或则Mysql配置信息不全,跳过检测.'+TextColorWhite)

       ####  Rabbimtmq 相关   ###
       print (u'即将检查"智能检索"与rabbitmq的连通性.......')

       ReObjA=re.search(r'^\s*amqp\.rabbitmq\.addresses\s*=\s*(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})\s*\n',TmpFileContent,
                        flags=re.MULTILINE|re.UNICODE)
       ReObjB=re.search(r'^\s*amqp\.rabbitmq\.port\s*=(\d{1,5})\s*\n',TmpFileContent,flags=re.MULTILINE|re.UNICODE)
       ReObjC=re.search(r'^\s*amqp\.rabbitmq\.username\s*=\s*(.*?)\s*\n',TmpFileContent,flags=re.MULTILINE|re.UNICODE)
       ReObjD=re.search(r'^\s*amqp\.rabbitmq\.password\s*=\s*(.*?)\s*\n',TmpFileContent,flags=re.MULTILINE|re.UNICODE)

       if ReObjA and ReObjB and ReObjC and ReObjD:
          TmpRabbitmqNode=deepcopy(nodeinfo.rabbitmqNodeInfo)

          TmpRabbitmqNode['rabbitmq']['host']=ReObjA.group(1).strip()
          TmpRabbitmqNode['rabbitmq']['port']=int(ReObjB.group(1).strip())
          TmpRabbitmqNode['rabbitmq']['user']=ReObjC.group(1).strip()
          TmpRabbitmqNode['rabbitmq']['password']=ReObjD.group(1).strip()
          
          TmpResult=checkRemotePort(TmpRabbitmqNode['rabbitmq']['host'],
                                    TmpRabbitmqNode['rabbitmq']['port'])

          if TmpResult['RetCode']==0:
             print (TextColorGreen+TmpResult['FeedBack']+TextColorWhite)
             print (TextColorGreen+u'"智能检索"访问Rabbitmq正常\n'+TextColorWhite)
          else:
             print (TextColorRed+TmpResult['FeedBack']+TextColorWhite)
             print (TextColorRed+u'"智能检索"无法访问Rabbitmq,\n请检查Rabbitmq是否正常运行，以及端口是否开放.\n'+TextColorWhite)
              
       else:
          print (TextColorRed+u'无法获取Rabbitmq配置信息，或者配置信息不全,跳过检测.\n'+TextColorWhite)



       ######  解析trsids-agent.properties 配置文件    ##
       with codecs.open(path.join(TmpHiddenPath,'trsids-agent.properties'),'r','utf-8') as f:
            TmpFileContent=f.read()

       print (u'即将检测“智能检索”与IDS的连通性......')
       ReObjA=re.search(r'^protocol.http.url=http://(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})(:\d{1,5})?/ids.*?',TmpFileContent,
                        flags=re.MULTILINE|re.UNICODE)

       

       if ReObjA:     
       	  TmpHost=ReObjA.group(1).strip()
       	  TmpPort=int(ReObjA.group(2).strip().strip(':')) if ReObjA.group(2) else 80
       	  TmpHttpResponse=sendHttpRequest(host=TmpHost,port=TmpPort,url='/ids')
       
       	  if TmpHttpResponse['RetCode']==0 and \
             (int(TmpHttpResponse['FeedBack']['HttpStatus'])>=200 and int(TmpHttpResponse['FeedBack']['HttpStatus'])<=399):
                print (TextColorGreen+u'“智能检索”可以正常访问IDS\n'+TextColorWhite)
       	  else:
                print (TextColorRed+u'无法通过http方式与IDS进行连通,'+'http://'+TmpHost+':'+str(TmpPort)+'/ids'+TextColorWhite)
                print (TextColorRed+u'请检查IDS是否正常运行，端口以及nginx的配置情况\n'+TextColorWhite)
       else:
            print (TextColoRed+u'无法获取IDS相关配置信息，检查跳过.\n'+TextColorWhite)

       
       ##### 与"采编"相关    ###
       print (u'即将检查与"采编"的连通性......')

       ReObj=re.search(r'^afterLoginOk.gotoUrl\s*=\s*http://(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})(:\d{1,5})?/govapp',TmpFileContent,
                       flags=re.MULTILINE|re.UNICODE)
       if ReObj:
           TmpHost=ReObj.group(1).strip()
           TmpPort=int(ReObj.group(2).strip()) if ReObj.group(2) else 80

           TmpHttpResponse=sendHttpRequest(host=TmpHost,port=TmpPort,url='/govapp')
           if TmpHttpResponse['RetCode']==0 and \
              (int(TmpHttpResponse['FeedBack']['HttpStatus'])>=200 and int(TmpHttpResponse['FeedBack']['HttpStatus'])<=399):
              print (TextColorGreen+u'“智能检索“可以正常访问”采编“\n'+TextColorWhite)
           else:
              print (TextColorRed+u'“智能检索”无法通过HTTP 连通”采编“,'+'http://'+TmpHost+':'+str(TmpPort)+'/govapp'+TextColorWhite)
              print (TextColorRed+u'请检查“采编”是否正常运行，端口是否开放，以及nginx配置。\n'+TextColorWhite)
       else:
           print (TextColorRed+u'无法获取与"采编"相关的配置情况，跳过检测.\n'+TextColorWhite)

       
       ####  清理临时文件   ###
       subprocess.call('cd %s && rm -f -r %s/*'%(TmpHiddenPath,TmpHiddenPath),shell=True)


class IPMCheck:
    def __init__(self,projectpath):
       projectpath=str(projectpath)
       if not path.isdir(projectpath):
           raise Exception(projectpath+u'不是有效的目录')
       self.ProjectPath=projectpath

   
    def  checkHealth(self):
         BaseDirectory=path.dirname(path.abspath(__file__))
         TmpHiddenPath=path.join(BaseDirectory,r'.tmp/IPM')
         
         if not path.isdir(TmpHiddenPath):
             makedirs(TmpHiddenPath)

         ### 过滤出目标  JAR 包   ###
         for item in walk(self.ProjectPath):
             if item[0]==self.ProjectPath:
                TmpFileList=list(filter(lambda x:re.search(r'^ipm[-_\.\s]*([\d\.]+)\.jar$',x,flags=re.IGNORECASE),item[2]))

         if len(TmpFileList)==0:
             print (TextColorRed+u'无法找到匹配的jar包，跳过对“绩效考核”的检测.....'+TextColorWhite)
             return 1

         ### 找到版本最新的 IPM JAR 包   ###
         TmpLatestVersionString='0'
         TmpIndex=-1      ### 最新的JAR包在LIST 中的索引位置 ###
         
         for index in range(len(TmpFileList)):
             ReObj=re.search(r'^ipm[-_\.\s]*([\d\.]+)\.jar',TmpFileList[index],flags=re.IGNORECASE)
             if ReObj:
                if compareVersionString(ReObj.group(1),TmpLatestVersionString)==1:
                   TmpLatestVersionString=ReObj.group(1)
                   TmpIndex=index
                   continue

         TmpTargetJARPath=path.join(self.ProjectPath,TmpFileList[TmpIndex])   ###目标JAR包的绝对文件路径  ##
                
         #### 解析 ipmXXXX.jar包
         subprocess.call('cp %s %s'%(TmpTargetJARPath,TmpHiddenPath),shell=True)      
         subprocess.call('cd %s && unzip %s >/dev/null'%(TmpHiddenPath,TmpFileList[TmpIndex]),shell=True)               
         
         #### 解析 application.properties   ####
         with codecs.open(path.join(TmpHiddenPath,'BOOT-INF/classes/application.properties'),'r','utf-8') as f:
              TmpFileContent=f.read()

         #####  版本号相关   ###
         ReObj=re.search(r'^\s*spring.application.version=(.*?)\s*\n',TmpFileContent,flags=re.MULTILINE|re.UNICODE)
         
         if ReObj:
              print (TextColorGreen+u'“绩效考核”当前版本：'+ReObj.group(1)+TextColorWhite) 
         else:
              print (TextColorRed+u'无法获取“绩效考核”版本号'+TextColorWhite)

      
         print (u"即将对“绩效考核”进行自检，请稍后.....")
    
         #### Mysql 相关   ####
         print (u'即将检查“绩效考核”与Mysql的连通性......')
   
         ReObjA=re.search(r'^\s*spring\.datasource\.url=jdbc:mysql://(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}):(\d{1,5})/(.*?)\?',TmpFileContent,
                         flags=re.UNICODE|re.MULTILINE)

         ReObjB=re.search(r'^\s*spring\.datasource\.username\s*=\s*(.*?)\s*\n',TmpFileContent,flags=re.UNICODE|re.MULTILINE)
         ReObjC=re.search(r'^\s*spring\.datasource\.password\s*=\s*(.*?)\s*\n',TmpFileContent,flags=re.UNICODE|re.MULTILINE)

         if ReObj and ReObjB and ReObjC:
            TmpIPMDBNode=deepcopy(nodeinfo.ipmDBInfo)

            TmpIPMDBNode['ipmdb']['host']=ReObjA.group(1).strip()
            TmpIPMDBNode['ipmdb']['port']=int(ReObjA.group(2))
            TmpIPMDBNode['ipmdb']['database']=ReObjA.group(3).strip()
            TmpIPMDBNode['ipmdb']['user']=ReObjB.group(1).strip()
            TmpIPMDBNode['ipmdb']['password']=ReObjC.group(1).strip()


            TmpResult=checkRemotePort(TmpIPMDBNode['ipmdb']['host'],TmpIPMDBNode['ipmdb']['port'])
            if TmpResult['RetCode']==0:
               print (TextColorGreen+TmpResult['FeedBack']+TextColorWhite)
               print (TextColorGreen+u'"绩效考核"可以正常访问Mysql.\n'+TextColorWhite)
            else:
               print (TextColorRed+TmpResult['FeedBack']+TextColorWhite)
               print (TextColorRed+u'“绩效考核”无法访问Mysql.\n请检查Mysql是否正常运行，端口是否开放.\n'+TextColorWhite)
         else:
            print (TextColorRed+u'无法获取Mysql信息，或者信息不全，跳过检测Mysql。\n'+TextColorWhite)


         #####   Redis 相关   ###
         print (u'即将检查“绩效考核”与Redis的连通性.....')
         
         ReObjA=re.search(r'^\s*spring\.redis\.host\s*=\s*(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})\s*\n',TmpFileContent,
                          flags=re.MULTILINE|re.UNICODE)
         ReObjB=re.search(r'\s*spring\.redis\.port\s*=\s*(\d{1,5})\s*\n',TmpFileContent,
                          flags=re.MULTILINE|re.UNICODE)
         ReObjC=re.search(r'^\s*spring\.redis\.password\s*=\s*(.*?)\s*\n',TmpFileContent,
                          flags=re.MULTILINE|re.UNICODE)
         ReObjD=re.search(r'^\s*spring\.redis\.database\s*=\s*(\d+)\s*\n',TmpFileContent,
                          flags=re.UNICODE|re.MULTILINE)


         if ReObjA and ReObjB and ReObjC and ReObjD:
            TmpRedisNode=deepcopy(nodeinfo.redisNodeInfo)

            TmpRedisNode['redis']['host']=ReObjA.group(1).strip()
            TmpRedisNode['redis']['port']=int(ReObjB.group(1).strip())
            TmpRedisNode['redis']['password']=ReObjC.group(1).strip()
            TmpRedisNode['redis']['database']=ReObjD.group(1).strip()
            
            TmpResult=checkRemotePort(TmpRedisNode['redis']['host'],TmpRedisNode['redis']['port'])
            
            if TmpResult['RetCode']==0:
               print (TextColorGreen+TmpResult['FeedBack']+TextColorWhite)
               print (TextColorGreen+u'“绩效考核“访问Redis正常.\n'+TextColorWhite)
            else:
               print (TextColorRed+TmpResult['FeedBack']+TextColorWhite)
               print (TextColorRed+u'"绩效考核“无法访问Redis'+TextColorWhite)
               print (TextColorRed+u'请检查Redis是否运行，端口是否开放.\n'+TextColorWhite)
         else:
             print (TextColorRed+u'无法获取Redis配置信息，或者配置信息不全；跳过对Redis的检测.\n'+TextColorWhite)


         #####  “问政互动”相关    ###
         print (u'即将测试与“问政互动”的连同性.....')
         ReObj=re.search(r'^\s*service\.outer\.nbhd\.url\s*=\s*http://(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})(:\d{1,5})?/IGI/?\s*\n',
                        TmpFileContent,flags=re.MULTILINE|re.UNICODE)

         if ReObj:
            TmpHost=ReObj.group(1).strip()
            TmpPort=int(ReObj.group(2).strip()) if ReObj.group(2) else 80
            TmpURL='/IGI'

            TmpHttpResponse=sendHttpRequest(TmpHost,TmpPort,TmpURL)
   
            if TmpHttpResponse['RetCode']==0:
               TmpHttpStatus=int(TmpHttpResponse['FeedBack']['HttpStatus'])
               if TmpHttpStatus>=200 and TmpHttpStatus<=399:
                  print (TextColorGreen+u'"绩效考核"可以正常访问“问政互动”'+TextColorWhite)
               else:
                  print (TextColorRed+u'“绩效考核”无法通过HTTP访问“问政互动”: http://'+TmpHost+':'+str(TmpPort)+'/IGI'+TextColorWhite)
                  print (TextColorRed+u'请检查“问政互动”是否运行正常，端口是否开放，以及Nginx配置\n'+TextColorWhite)
            else:
                print (TextColorRed+u'“绩效考核”无法通过HTTP访问“问政互动”: http://'+TmpHost+':'+str(TmpPort)+'/IGI'+TextColorWhite)
                print (TextColorRed+u'请检查“问政互动”是否运行正常，端口是否开放，以及Nginx配置\n'+TextColorWhite)   
            
         else:
            print (TextColorRed+u'无法获取“问政互动”相关信息，或者信息不完整，跳过与“问政互动”的检查.\n'+TextColorWhite)


         ##### “统计报表” 相关   ####
         print (u'即将测试与“统计报表”的连同性.....')
         ReObj=re.search(r'^\s*service\.outer\.report\.url\s*=\s*http://(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})(:\d{1,5})?/gov/report/?\s*\n',
                        TmpFileContent,flags=re.MULTILINE|re.UNICODE)

         if ReObj:
            TmpHost=ReObj.group(1).strip()
            TmpPort=int(ReObj.group(2).strip()) if ReObj.group(2) else 80
            TmpURL='/gov/report'

            TmpHttpResponse=sendHttpRequest(TmpHost,TmpPort,TmpURL)

            if TmpHttpResponse['RetCode']==0:
               TmpHttpStatus=int(TmpHttpResponse['FeedBack']['HttpStatus'])
               if TmpHttpStatus>=200 and TmpHttpStatus<=399:
                  print (TextColorGreen+u'"绩效考核"可以正常访问“统计报表”'+TextColorWhite)
               else:
                  print (TextColorRed+u'“绩效考核”无法通过HTTP访问“统计报表”: http://'+TmpHost+':'+str(TmpPort)+'/gov/report'+TextColorWhite)
                  print (TextColorRed+u'请检查“统计报表”是否运行正常，端口是否开放，以及Nginx配置\n'+TextColorWhite)
            else:
                print (TextColorRed+u'“绩效考核”无法通过HTTP访问“统计报表”: http://'+TmpHost+':'+str(TmpPort)+'/gov/report'+TextColorWhite)
                print (TextColorRed+u'请检查“统计报表”是否运行正常，端口是否开放，以及Nginx配置\n'+TextColorWhite)

         else:
            print (TextColorRed+u'无法获取“统计报表”相关信息，或者信息不完整，跳过与“统计报表”的检查.\n'+TextColorWhite)


         ####   Rabbitmq  相关  ###
         print (u'即将测试“Rabbitmq”的连通性.....')
         ReObjA=re.search(r'^\s*rabbitmq\.hosts\s*=\s*(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})\s*\n',TmpFileContent,
                          flags=re.MULTILINE|re.UNICODE) 
         ReObjB=re.search(r'^\s*rabbitmq\.port\s*=\s*(\d{1,5})\s*\n',TmpFileContent,flags=re.MULTILINE|re.UNICODE) 
         ReObjC=re.search(r'^\s*rabbitmq\.username\s*=\s*(.*?)\s*\n',TmpFileContent,flags=re.MULTILINE|re.UNICODE)
         ReObjD=re.search(r'^\s*rabbitmq\.password\s*=\s*(.*?)\s*\n',TmpFileContent,flags=re.MULTILINE|re.UNICODE)

         if ReObjA and ReObjB and ReObjC and ReObjD:
            TmpHost=ReObjA.group(1).strip()
            TmpPort=int(ReObjB.group(1).strip())

            TmpResult=checkRemotePort(TmpHost,TmpPort)
            if TmpResult['RetCode']==0:
               print (TextColorGreen+u'“绩效考核”访问Rabbitmq正常.\n'+TextColorWhite)
            else:
               print (TextColorRed+TmpResult['FeedBack']+TextColorWhite)
               print (TextColorRed+u'"绩效考核"无法访问Rabbitmq'+TextColorWhite)
               print (TextColorRed+u'请检查Rabbitmq是否正常运行，端口是否开放.\n'+TextColorWhite)
         else:
            print (TextColorRed+u'无法获取Rabbitmq相关信息，或信息不全，跳过与"Rabbitmq"的测试.\n'+TextColorWhite)

         ### 清理临时文件  ##
         subprocess.call('cd %s && rm -f -r %s/*'%(TmpHiddenPath,TmpHiddenPath),shell=True)



class IRTCheck:
    def __init__(self,projectpath):
       projectpath=projectpath.strip()
       if not path.isdir(projectpath):
          raise Exception(projectpath+u'不是有效的目录!')
       self.ProjectPath=projectpath

    def checkHealth(self):
         BaseDirectory=path.dirname(path.abspath(__file__))
         TmpHiddenPath=path.join(BaseDirectory,r'.tmp/IRT')
         if not path.isdir(TmpHiddenPath):
            makedirs(TmpHiddenPath)

         ### 过滤出目标  JAR 包   ###
         for item in walk(self.ProjectPath):
             if item[0]==self.ProjectPath:
                TmpFileList=list(filter(lambda x:re.search(r'^irt[-_\.\s]*([\d\.]+)\.jar$',x,flags=re.IGNORECASE),item[2]))

         if len(TmpFileList)==0:
             print (TextColorRed+u'无法找到匹配的jar包，跳过对“统计报表”的检测.....'+TextColorWhite)
             return 1

         ### 找到版本最新的 IPM JAR 包   ###
         TmpLatestVersionString='0'
         TmpIndex=-1      ### 最新的JAR包在LIST 中的索引位置 ###
         
         for index in range(len(TmpFileList)):
             ReObj=re.search(r'^irt[-_\.\s]*([\d\.]+)\.jar',TmpFileList[index],flags=re.IGNORECASE)
             if ReObj:
                if compareVersionString(ReObj.group(1),TmpLatestVersionString)==1:
                   TmpLatestVersionString=ReObj.group(1)
                   TmpIndex=index
                   continue

         TmpTargetJARPath=path.join(self.ProjectPath,TmpFileList[TmpIndex])   ###目标JAR包的绝对文件路径  ##
        
         #### 解析 irtXXXX.jar 包###
         subprocess.call('cp %s %s'%(TmpTargetJARPath,TmpHiddenPath),shell=True)
         subprocess.call('cd %s && unzip %s >/dev/null'%(TmpHiddenPath,TmpFileList[TmpIndex]),shell=True)         

         #### 解析  application.properties 文件 ###
         with codecs.open(path.join(TmpHiddenPath,r'BOOT-INF/classes/application.properties'),'r','utf-8') as f:
             TmpFileContent=f.read()

         ### 版本号相关  ###
         ReObj=r=re.search(r'^\s*spring\.application\.version\s*=\s*(.*?)\s*\n',TmpFileContent,flags=re.UNICODE|re.MULTILINE)
         if ReObj:
            print (TextColorGreen+u'"报表统计"当前版本号:'+ReObj.group(1).strip()+TextColorWhite)
         else:
            print (TextColorRed+u'无法获取“报表统计”版本号'+TextColorWhite)


         ###  "报表统计"Mysql相关    ##
         print (u'即将测试“统计报表”与Mysql的连通性，请稍候.....')
         ReObjA=re.search(r'^\s*datasource\.report\.url\s*=jdbc:mysql://(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}):(\d{1,5})/(.*?)\?',TmpFileContent,
                          flags=re.MULTILINE|re.UNICODE)
         ReObjB=re.search(r'^\s*datasource\.report\.username\s*=(.*?)\s*\n',TmpFileContent,flags=re.MULTILINE|re.UNICODE)
         ReObjC=re.search(r'^\s*datasource\.report\.password\s*=(.*?)\s*\n',TmpFileContent,flags=re.UNICODE|re.MULTILINE)

         if ReObjA and ReObjB and ReObjC:
            TmpIRTDBNode=deepcopy(nodeinfo.irtDBInfo)
            TmpIRTDBNode['irtdb']['host']=ReObjA.group(1).strip()
            TmpIRTDBNode['irtdb']['port']=int(ReObjA.group(2).strip())
            TmpIRTDBNode['irtdb']['database']=ReObjA.group(3).strip()
            TmpIRTDBNode['irtdb']['user']=ReObjB.group(1).strip()
            TmpIRTDBNode['irtdb']['password']=ReObjC.group(1).strip()

            TmpResult=checkRemotePort(TmpIRTDBNode['irtdb']['host'],TmpIRTDBNode['irtdb']['port'])

            if TmpResult['RetCode']==0:
               print (TextColorGreen+TmpResult['FeedBack']+TextColorWhite)
               print (TextColorGreen+u'“统计报表访问Mysql正常”\n'+TextColorWhite)
            else:
               print (TextColorRed+TmpResult['FeedBack']+TextColorWhite)
               print (TextColorRed+u'“统计报表”无法访问Mysql，\n请检查Mysql正常运行，端口开放.\n'+TextColorWhite)
               
         else:
             print (TextColorRed+u'无法获取“统计报表”Mysql配置信息，或者相关配置信息不完整，跳过对“统计报表”Mysql的检查\n'+TextColorWhite) 
         
         #### "采编数据库"相关   ##
         print (u'即将测试“统计报表”与"采编"数据库的连通性，请稍候....')
         ReObjA=re.search(r'^\s*datasource\.editcenter\.url\s*=\s*jdbc:mysql://(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}):(\d{1,5})/(.*?)\?',TmpFileContent,
                          flags=re.UNICODE|re.MULTILINE)
         ReObjB=re.search(r'^\s*datasource\.editcenter\.username\s*=\s*(.*?)\s*\n',TmpFileContent,flags=re.MULTILINE|re.UNICODE)
         ReObjC=re.search(r'^\s*datasource\.editcenter\.password\s*=\s*(.*?)\s*\n',TmpFileContent,flags=re.MULTILINE|re.UNICODE)


         if  ReObjA and ReObjB and ReObjC:
            TmpIIPDBNode=deepcopy(nodeinfo.iipDBInfo)

            TmpIIPDBNode['iipdb']['host']=ReObjA.group(1).strip()
            TmpIIPDBNode['iipdb']['port']=int(ReObjA.group(2).strip())
 	    TmpIIPDBNode['iipdb']['database']=ReObjA.group(3).strip()
            TmpIIPDBNode['iipdb']['user']=ReObjB.group(1).strip()
            TmpIIPDBNode['iipdb']['password']=ReObjC.group(1).strip()
            
            TmpResult=checkRemotePort(TmpIIPDBNode['iipdb']['host'],TmpIIPDBNode['iipdb']['port'])
            if TmpResult['RetCode']==0:
               print (TextColorGreen+TmpResult['FeedBack']+TextColorWhite)
               print (TextColorGreen+u'“统计报表”访问"采编"Mysql正常.\n'+TextColorWhite)
            else:
               print (TextColorRed+TmpResult['FeedBack']+TextColorWhite)
               print (TextColorRed+u'"统计报表"无法访问"采编"Mysql'+TextColorWhite)
               print (TextColorRed+u'请确认“采编”的mysql运行正常，端口开放.\n'+TextColorWhite)
 
         else:
            print (TextColorRed+u'无法获取与“采编”Mysql相关的信息，或信息不全，跳过对“采编”Mysql的测试.\n'+TextColorWhite)


         ###  与rabbitmq 相关 ###
         print (u'即将测试“统计报表”与rabbitmq的连通性，请稍候....')
         ReObjA=re.search(r'^\s*rabbitmq\.hosts\s*=\s*(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})\s*\n',TmpFileContent,flags=re.MULTILINE|re.UNICODE)
         ReObjB=re.search(r'^\s*rabbitmq\.port\s*=\s*(\d{1,5})\s*\n',TmpFileContent,flags=re.MULTILINE|re.UNICODE)
         ReObjC=re.search(r'^\s*rabbitmq\.username\s*=\s*(.*?)\s*\n',TmpFileContent,flags=re.UNICODE|re.MULTILINE)
         ReObjD=re.search(r'^\s*rabbitmq\.password\s*=\s*(.*?)\s*\n',TmpFileContent,flags=re.UNICODE|re.MULTILINE)

         if ReObjA  and ReObjB and ReObjC and ReObjD:
            TmpRabbitmqNode=deepcopy(nodeinfo.rabbitmqNodeInfo)

            TmpRabbitmqNode['rabbitmq']['host']=ReObjA.group(1).strip()
            TmpRabbitmqNode['rabbitmq']['port']=int(ReObjB.group(1).strip())
            TmpRabbitmqNode['rabbitmq']['user']=ReObjC.group(1).strip()
            TmpRabbitmqNode['rabbitmq']['password']=ReObjD.group(1).strip()

            TmpResult=checkRemotePort(TmpRabbitmqNode['rabbitmq']['host'],TmpRabbitmqNode['rabbitmq']['port'])
            if TmpResult['RetCode']==0:
               print (TextColorGreen+TmpResult['FeedBack']+TextColorWhite)
               print (TextColorGreen+u'“统计报表”访问Rabbitmq节点正常.\n'+TextColorWhite)
            else:
               print (TextColorRed+TmpResult['FeedBack']+TextColorWhite)
               print (TextColorRed+u'“统计报表”无法rabbitmq节点，\n请检查rabbitmq是否正常运行，端口是否开放.\n'+TextColorWhite)
         else:
            print (TextColorRed+u'无法获取Rabbitmq节点信息，或者信息不全，跳过对rabbitmq检测.\n'+TextColorWhite) 

         ### 清理临时文件   ###
         subprocess.call('cd %s && rm -f -r %s/*'%(TmpHiddenPath,TmpHiddenPath),shell=True)


class IIPCheck:
    def __init__(self,projectpath):
        projectpath=projectpath.strip()
        if not path.isdir(projectpath):
            raise Exception(projectpath+u'不失效的目录.')
        self.ProjectPath=projectpath

    def checkHealth(self):
        print (u'即将对“采编”系统进行自检，请稍候.....')
        BaseDirectory=path.dirname(path.abspath(__file__))
        TmpHiddenPath=path.join(BaseDirectory,r'.tmp/IIP')
   
        if not path.isdir(TmpHiddenPath):
           makedirs(TmpHiddenPath)

        TmpTargetIIPFolder=path.join(self.ProjectPath,r'webapps/gov/WEB-INF/classes')
        subprocess.call('cp -r %s/* %s >/dev/null'%(TmpTargetIIPFolder,TmpHiddenPath),shell=True)

        ### 解析 application.properties ###
        with codecs.open(path.join(TmpHiddenPath,r'application.properties'),'r','utf-8') as f:
            TmpFileContent=f.read()
    
        #### 版本号相关   ###
        ReObj=re.search(r'^\s*iip\.build\.number\s*=\s*(.*?)\s*\n',TmpFileContent,flags=re.UNICODE|re.MULTILINE)
        if ReObj:
           print (TextColorGreen+u'检测到"智能门户“当前版本号：'+ReObj.group(1).strip()+'\n'+TextColorWhite)
        else:
           print (TextColorRed+u'无法检测到“智能门户”版本号\n'+TextColorRed)


        ReObj=re.search(r'^\s*ido\.build\.number\s*=\s*(.*?)\s*\n',TmpFileContent,flags=re.UNICODE|re.MULTILINE)

        if ReObj:
           print (TextColorGreen+u'检测到“运营中心“当前版本号：'+ReObj.group(1).strip()+'\n'+TextColorWhite)
        else:
           print (TextColorRed+u'无法检测到“运营中心”版本号\n'+TextColorRed)


        #### IDS 相关  ###
        print (u'即将测试“智慧门户”与IDS的连通性，请稍候....')
        ReObj=re.search(r'^\s*ids\.server\.url\s*=\s*http://(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})(:\d{1,5})?/ids\s*\n',
                       TmpFileContent,flags=re.UNICODE|re.MULTILINE)

        if ReObj:
           TmpHost=ReObj.group(1).strip()
           TmpPort=int(ReObj.group(2).strip(':').strip()) if ReObj.group(2) else 80
   
           TmpHttpResponse=sendHttpRequest(host=TmpHost,port=TmpPort,url='/ids')
           if TmpHttpResponse['RetCode']==0:
              TmpHttpStatus=TmpHttpResponse['FeedBack']['HttpStatus']
              if TmpHttpStatus>=200 and TmpHttpStatus<=399:
                  print (TextColorGreen+u'"智慧门户"访问IDS正常.\n'+TextColorWhite)
              else:
                  print (TextColorRed+u'“智慧门户”无法通过HTTP 访问IDS,http://'+str(TmpHost)+':'+str(TmpPort)+'/ids'+TextColorWhite)
                  print (TextColorRed+u'请确认IDS运行正常，端口开放，以及Nginx配置正确.\n'+TextColorWhite)
           else:
                print (TextColorRed+u'“智慧门户”无法通过HTTP 访问IDS,http://'+str(TmpHost)+':'+str(TmpPort)+'/ids'+TextColorWhite)
                print (TextColorRed+u'请确认IDS运行正常，端口开放，以及Nginx配置正确.\n'+TextColorWhite)
                 
        else:
           print (TextColorRed+u'无法获取IDS相关配置信息,跳过对IDS的连通性测试.\n'+TextColorWhite)

        #### 解析 cache/redis.properties ####
        print (u'即将测试“智慧门户”与Redis的连通性，请稍候....')
        with codecs.open(path.join(TmpHiddenPath,r'cache/redis.properties'),'r','utf-8') as f:
             TmpFileContent=f.read()

        ReObjA=re.search(r'^\s*redis\.hostname\s*=\s*(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})\s*\n',TmpFileContent,flags=re.UNICODE|re.MULTILINE)
        ReObjB=re.search(r'^\s*redis\.port\s*=\s*(\d{1,5})\s*\n',TmpFileContent,flags=re.UNICODE|re.MULTILINE)
        ReObjC=re.search(r'^\s*redis\.password\s*=\s*(.*?)\s*\n',TmpFileContent,flags=re.UNICODE|re.MULTILINE)
        ReObjD=re.search(r'^\s*redis\.db\s*=\s*(.*?)\s*\n',TmpFileContent,flags=re.UNICODE|re.MULTILINE)



        if ReObjA and ReObjB and ReObjC and ReObjD:
           TmpRedisNode=deepcopy(nodeinfo.redisNodeInfo)
           
           TmpRedisNode['redis']['host']=ReObjA.group(1).strip()
           TmpRedisNode['redis']['port']=int(ReObjB.group(1).strip())
           TmpRedisNode['redis']['password']=ReObjC.group(1).strip()
           TmpRedisNode['redis']['database']=ReObjD.group(1).strip()
           
           TmpResult=checkRemotePort(TmpRedisNode['redis']['host'],TmpRedisNode['redis']['port'])

           if TmpResult['RetCode']==0:
              print (TextColorGreen+u'"智慧门户"访问Redis正常.\n'+TextColorWhite)
           else:
              print (TextColorRed+TmpResult['FeedBack']+TextColorWhite)
              print (TextColorRed+u'“智慧门户”无法访问Redis，\n请检查Redis运行正常，端口开放.\n'+TextColorWhite)
        else:
           print (TextColorRed+u'无法获取Redis配置信息，或配置信息不全，跳过对Redis的连通性测试.\n'+TextColorWhite)


        #### 解析 ckm.properties 文件  ###
        print ('即将测试"智慧门户"与ckm的连通性，请稍候...')
        with codecs.open(path.join(TmpHiddenPath,r'ckm.properties'),'r','utf-8') as f:
           TmpFileContent=f.read()

        ReObj=re.search(r'^\s*ckm\.url\s*=\s*http://(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})(:\d{1,5})?/ckm\s*\n',TmpFileContent,
                        flags=re.UNICODE|re.MULTILINE)

        if ReObj:
           TmpHost=ReObj.group(1).strip()
           TmpPort=int(ReObj.group(2).strip()) if ReObj.group(2) else 80

           TmpHttpResponse=sendHttpRequest(TmpHost,TmpPort,'/ckm')

           if TmpHttpResponse['RetCode']==0:
              TmpHttpStatus=TmpHttpResponse['FeedBack']['HttpStatus']
              if TmpHttpStatus>=200 and TmpHttpStatus<=399:
                 print (TextColorGreen+u'“智慧门户”访问CKM正常。\n'+TextColorWhite)
              else:
                 print (TextColorRed+u'“智慧门户”无法通过http访问ckm;http://'+TmpHost+':'+str(TmpPort)+'/ckm'+TextColorWhite)
                 print (TextColorRed+u'请检查ckm运行正常，端口开放，Nginx配置正确.\n'+TextColorWhite)
           else:
              print (TextColorRed+u'“智慧门户”无法通过http访问ckm;http://'+TmpHost+':'+str(TmpPort)+'/ckm'+TextColorWhite)
              print (TextColorRed+u'请检查ckm运行正常，端口开放，Nginx配置正确.\n'+TextColorWhite)
        else:
           print (TextColorRed+u'无法获取ckm相关配置，跳过与ckm的连通性测试.\n'+TextColorWhite)

      
        ####  解析 elasticsearch.properties文件  ##
        print ('即将测试“智慧门户”与Elasticsearch的连通性，请稍候....')
        with codecs.open(path.join(TmpHiddenPath,r'elasticsearch.properties'),'r','utf-8') as f:
             TmpFileContent=f.read()

        ReObjA=re.search(r'^\s*elasticsearch\.host\s*=\s*http://(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})\s*\n',TmpFileContent,
                        flags=re.UNICODE|re.MULTILINE)
        ReObjB=re.search(r'^\s*elasticsearch\.port\s*=\s*:(\d{1,5})\s*\n',TmpFileContent,flags=re.UNICODE|re.MULTILINE)
        ReObjC=re.search(r'^\s*elasticsearch\.index\s*=\s*/gov_log805\s*\n',TmpFileContent,flags=re.UNICODE|re.MULTILINE)

        if ReObjA and ReObjB and ReObjC:
            TmpHost=ReObjA.group(1).strip()
            TmpPort=int(ReObjB.group(1).strip(':').strip())

            TmpHttpResponse=sendHttpRequest(host=TmpHost,port=TmpPort,url='/gov_log805')
            if TmpHttpResponse['RetCode']==0:
               if TmpHttpResponse['FeedBack']['HttpStatus']==200:
                  print (TextColorGreen+u'"智慧门户"可以正常访问elasticsearch.\n'+TextColorWhite)
               else:
                  print (TextColorRed+u'"智慧门户"无法通过HTTP访问elasticsearch;http://'+TmpHost+':'+str(TmpPort)+'/gov_log805.'+TextColorWhite)
                  print (TextColorRed+u'请检查elasticsearch 运行正常，端口开放，且正确配置了index.\n'+TextColorWhite)
            else:
		print (TextColorRed+u'"智慧门户"无法通过HTTP访问elasticsearch;http://'+TmpHost+':'+str(TmpPort)+'/gov_log805.'+TextColorWhite)
		print (TextColorRed+u'请检查elasticsearch 运行正常，端口开放，且正确配置了index.\n'+TextColorWhite)
                  
        else:
            print (TextColorRed+u'无法获取elasticsearch 配置信息，或者配置信息不全，跳过对elasearch的测试.\n'+TextColorWhite)


        ### 解析 mas.properties 文件   ###
        print (u'即将解析"智慧门户"与mas的连通性，请稍候....')
        with codecs.open(path.join(TmpHiddenPath,r'mas.properties'),'r','utf-8') as f:
            TmpFileContent=f.read()

        ReObj=re.search(r'^\s*mas\.upload\.URL\s*=\s*http://(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})(:\d{1,5})?/mas',TmpFileContent,
                       flags=re.UNICODE|re.MULTILINE)
        if ReObj:
            TmpHost=ReObj.group(1).strip()
            TmpPort=int(ReObj.group(2).strip(':').strip()) if ReObj.group(2) else 80

            TmpHttpResponse=sendHttpRequest(host=TmpHost,port=TmpPort,url='/mas')

            if TmpHttpResponse['RetCode']==0:
               TmpHttpStatus=TmpHttpResponse['FeedBack']['HttpStatus']
               if TmpHttpStatus>=200 and TmpHttpStatus<=399:
                  print (TextColorGreen+u'“智慧门户”访问MAS正常。\n'+TextColorWhite)
               else:
                  print (TextColorRed+u'“智慧门户”无法通过HTTP访问mas;http://'+TmpHost+':'+str(TmpPort)+'/mas'+TextColorWhite)
                  print (TextColorRed+u'请检查MAS运行正常，端口开放，Nginx配置正常.\n'+TextColorWhite)
            else:
 		  print (TextColorRed+u'“智慧门户”无法通过HTTP访问mas;http://'+TmpHost+':'+str(TmpPort)+'/mas'+TextColorWhite)
		  print (TextColorRed+u'请检查MAS运行正常，端口开放，Nginx配置正常.\n'+TextColorWhite)
	else:
            print (TextColorRed+u'无法获取与mas相关的配置信息，跳过对mas的测试.\n'+TextColorWhite)


        #### 解析 mq.properties 文件   ####
        print (u'即将解析"智慧门户"与rabbitmq的连通性，请稍候....')
        with codecs.open(path.join(TmpHiddenPath,r'mq.properties'),'r','utf-8') as f:
            TmpFileContent=f.read()

        ReObjA=re.search(r'^\s*rabbitmq\.host\s*=\s*(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})\s*\n',TmpFileContent,
                         flags=re.MULTILINE|re.UNICODE)
        ReObjB=re.search(r'^\s*rabbitmq\.port\s*=\s*(\d{1,5}\s*\n)',TmpFileContent,flags=re.UNICODE|re.MULTILINE)
        ReObjC=re.search(r'^\s*rabbitmq\.username\s*=\s*(.*?)\s*\n',TmpFileContent,flags=re.UNICODE|re.MULTILINE)
        ReObjD=re.search(r'^\s*rabbitmq\.password\s*=\s*(.*?)\s*\n',TmpFileContent,flags=re.UNICODE|re.MULTILINE)

        if ReObjA and ReObjB and ReObjC and ReObjD:
            TmpRabbitmqNode=deepcopy(nodeinfo.rabbitmqNodeInfo)
            TmpRabbitmqNode['rabbitmq']['host']=ReObjA.group(1).strip()
            TmpRabbitmqNode['rabbitmq']['port']=int(ReObjB.group(1).strip())
            TmpRabbitmqNode['rabbitmq']['user']=ReObjC.group(1).strip()
            TmpRabbitmqNode['rabbitmq']['password']=ReObjD.group(1).strip()

            TmpResult=checkRemotePort(TmpRabbitmqNode['rabbitmq']['host'],TmpRabbitmqNode['rabbitmq']['port'])

            if TmpResult['RetCode']==0:
               print (TextColorGreen+u'"智慧门户"访问Rabbitmq正常.\n'+TextColorWhite)
            else:
               print (TextColorRed+TmpResult['FeedBack']+TextColorWhite)
               print (TextColorRed+u'“智慧门户”无法访问Rabbitmq.'+TextColorWhite)
               print (TextColorRed+u'请检查rabbitmq是否正常运行，端口是否开放.\n'+TextColorWhite)
        else:
            print (TextColorRed+u'无法获取Rabbitmq配置信息，跳过对Rabbitmq的测试.\n'+TextColorWhite)


        ####   解析 trsids-agent.properties 文件  ###
        print (u'即将解析“智慧门户”与IDS的连通性，请稍候.....')
        with codecs.open(path.join(TmpHiddenPath,r'trsids-agent.properties'),'r','utf-8') as f:
             TmpFileContent=f.read()

        ReObj=re.search(r'^\s*protocol\.http\.url\s*=\s*http://(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})(:\d{1,5})?/ids/protocol\s*\n',
                        TmpFileContent,flags=re.UNICODE|re.MULTILINE)
        if ReObj:
           TmpHost=ReObj.group(1).strip()
           TmpPort=int(ReObj.group(2).strip(':').strip()) if ReObj.group(2) else 80

           TmpHttpResponse=sendHttpRequest(host=TmpHost,port=TmpPort,url='/ids')
           if TmpHttpResponse['RetCode']==0:
              TmpHttpStatus=TmpHttpResponse['FeedBack']['HttpStatus']
              if TmpHttpStatus>=200 and TmpHttpStatus<=399:
                 print (TextColorGreen+u'“智慧门户”访问IDS正常。\n'+TextColorWhite)
              else:
                 print (TextColorRed+u'"智慧门户"无法通过HTTP 访问IDS；http://'+TmpHost+':'+str(TmpPort)+'/ids/protocol'+TextColorWhite)
                 print (TextColorRed+u'请检查IDS运行正常，端口开放，Nginx配置正确.\n'+TextColorWhite)
           else:
               print (TextColorRed+u'"智慧门户"无法通过HTTP 访问IDS；http://'+TmpHost+':'+str(TmpPort)+'/ids/protocol'+TextColorWhite)
               print (TextColorRed+u'请检查IDS运行正常，端口开放，Nginx配置正确.\n'+TextColorWhite)
        else:
            print (TextColorRed+u'无法获取IDS相关配置，跳过对IDS的连通性测试.\n'+TextColorWhite)

        ### 解析 zabbix.properties 文件   #
        print (u'即将测试"智慧门户"与zabbix的连通性，请稍候....')
        with codecs.open(path.join(TmpHiddenPath,r'zabbix.properties'),'r','utf-8') as f:
            TmpFileContent=f.read()

        ReObj=re.search(r'^\s*zabbix\.ApiUrl=\s*http://(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})(:\d{1,5})?/zabbix/api_jsonrpc.php\s*\n',
                        TmpFileContent,flags=re.UNICODE|re.MULTILINE)
        if ReObj:
            TmpHost=ReObj.group(1).strip()
            TmpPort=int(ReObj.group(2).strip(':').strip()) if ReObj.group(2) else 80
       
            TmpHttpResponse=sendHttpRequest(host=TmpHost,port=TmpPort,url='/zabbix/api_jsonrpc.php')
            if TmpHttpResponse['RetCode']==0:
               TmpHttpStatus=TmpHttpResponse['FeedBack']['HttpStatus']
               if TmpHttpStatus>=200 and TmpHttpStatus<=399:
                  print (TextColorGreen+u'"智慧门户"访问Zabbix正常。\n'+TextColorWhite)
               else:
                  print (TextColorRed+u'“智慧门户”无法通过HTTP 访问Zabbix;http://'+TmpHost+':'+str(TmpPort)+'/zabbix/api_jsonrpc.php'+TextColorWhite)
                  print (TextColorRed+u'请检查zabbix运行正常，端口开放，Nginx配置正确.\n'+TextColorWhite)
            else:
                print (TextColorRed+u'“智慧门户”无法通过HTTP 访问Zabbix;http://'+TmpHost+':'+str(TmpPort)+'/zabbix/api_jsonrpc.php'+TextColorWhite)
                print (TextColorRed+u'请检查zabbix运行正常，端口开放，Nginx配置正确.\n'+TextColorWhite) 
        else:
            print (TextColorRed+u'无法获取Zabbix配置信息，跳过对Zabbix的连通性测试.\n'+TextColorWhite)


        #### 清理临时文件   ###
        subprocess.call('cd %s && rm -f -r %s/*'%(TmpHiddenPath,TmpHiddenPath),shell=True)

#TmpObj=IGICheck(r'/TRS/HyCloud/IGI')
#TmpObj=IGSCheck(r'/TRS/HyCloud/IGS')
#TmpObj=IPMCheck(r'/TRS/HyCloud/IPM')
#TmpObj=IRTCheck(r'/TRS/HyCloud/IRT')
#TmpObj=IIPCheck(r'/TRS/HyCloud/IIP')
#TmpObj.checkHealth()





