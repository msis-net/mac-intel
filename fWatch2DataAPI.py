#(C)Msis,Inc.
#modifyはsleep(1)毎に発生してしまうので使えない。
#createは１回だけ発火するので、そのまま実行プロセス（マルチスレッド※マルチプロセスの場合はCPU負荷の懸念）を実行
#本プロセス内checksumを確認しファイル書き込みが完了したらDataAPIへのリクエストを処理する

import sys
import time
import os
import json
import logging
import logging.handlers
import datetime
import base64
import threading
import traceback
import shutil
import glob
from pathlib import Path
from requests import Session, request 
from requests_pkcs12 import Pkcs12Adapter 
from watchdog.observers.polling import PollingObserver
from watchdog.events import LoggingEventHandler



#LoggingEvenHandlerを上書きして動作を変更
class LoggingEventHandler2(LoggingEventHandler):    
    def on_created(self, event): 
        
        os.chmod(event.src_path,0o777)
        filename = os.path.basename(event.src_path)
        logger.info("[Created]"+event.src_path)
        #ファイルである事の確認
        if(not os.path.isfile(event.src_path)):
            logger.info("[Is not File]" + event.src_path) 
            return

        #隠しファイルの判定
        if(filename.startswith('.')):
            logger.info("[Is hidden File]" + event.src_path) 
            return

        tmpPath = CheckPath+filename
        if(not os.path.exists(tmpPath)):
            logger.info("[Is not exixits CheckPath]" + event.src_path) 
            return
       
        
        #書込み中を回避するため、openで読込ができるようになるまで待機させる
        while True:
            time.sleep(1)  
            try:
                f=open(event.src_path,'r')
                #data=f.read()
                f.close()
                break    
            except Exception as e:
                logger.info("[Exception(53)]" + repr(e)+":"+event.src_path)
                break 
        
        try:
            #execAPIを実行#Threadで並列処理
            if(os.path.isfile(event.src_path) == True):
                thread_1 = threading.Thread(target=execAPI(filename,event.src_path))
                thread_1.start()
            else:
                return
            

        except Exception as e:
            logger.info("[Exception(70)]" + repr(e)+":"+event.src_path) 
        

    def on_deleted(self, event):
        try:
            logger.info("[Deleted]" + event.src_path) 
        except Exception as e:
            logger.info("[Exception(79)]" + repr(e)+":"+event.src_path) 
        

    def on_modified(self, event):
        #observer = PollingObserver()では、slee(1)毎にこのイベントが発生するので書込み完了は検知できず。よってスルーさせる。
        if(os.path.isfile(event.src_path) == True):
            filename = os.path.basename(event.src_path)
            
            
    

def execAPI(filename,fipepath):
    logger.info("[DataAPI:start]" + fipepath) 
    try:
        os.chmod(fipepath,0o777)
    except Exception as e:
       logger.info("[Exception(95)]" + repr(e)+":"+fipepath)  
    #DataAPI実行
    param = '{"path":"'+Watchpath+'","filename":"'+filename+'",\"script\":"'+fm_script+'"}'
    logger.info("[DataAPI:param]" + param)   
    
    #DataAPIの実行
    try:
        #ログイン
        url_1 = fm_host+'/fmi/data/vLatest/databases/'+fm_database+'/sessions'
        #print("url_1:"+url_1)
        # アカウント：Basic認証用の文字列を作成.
        basic_user_and_pasword = base64.b64encode('{}:{}'.format(fm_user, fm_password).encode('utf-8'))
        #ヘッダ
        headers_1 = {
            'content-type': 'application/json',
            'Authorization': 'Basic ' + basic_user_and_pasword.decode("utf-8")
            }
        
        #クライアント証明書認証が必要な場合はSessionに証明書ファイルと証明書パスフェーズをマウントする
        ssl= False 
        with Session() as s:
            if len(fm_pkcs12)>0:
                s.mount(fm_host, Pkcs12Adapter(pkcs12_filename=fm_pkcs12, pkcs12_password=fm_pkcs12_password))
                #fm_pkcs12nに設定がある場合はクライアント証明書認証が必要
                ssl=True
            
            response = s.post(url_1,headers=headers_1,verify = ssl)
            result = response.json()
            #print("response:",response,result)
        token = result["response"]["token"]
        logger.info("[DataAPI:token]" + token) 
        
        #スクリプトを実行
        url_2 = fm_host+'/fmi/data/vLatest/databases/'+fm_database+'/layouts/'+fm_layout+'/script/apiDataCatch?script.param='+param
        #print("url_2:"+url_2)
        headers_2 = {
            'content-type': 'application/json',
            'Authorization': 'Bearer ' + token
            }
        response = s.get(url_2,verify = ssl,headers=headers_2)
        #print(response.text)
        logger.info("[DataAPI:request]" + response.text) 
        #ログアウト
        url_3 = url_1+'/'+token
        print("url_3:"+url_3)
        headers_3 = {
            'content-type': 'application/json'
        }
        response = s.delete(url_3,verify = ssl,headers=headers_3)
        #print(response.text)
        
    except Exception as e:
        t = traceback.format_exc()
        logger.info("[Exception(148)]" + str(t)+":"+param )

    logger.info("[DataAPI:result]" + response.text) 
    return


if __name__ == "__main__":
    #path = sys.argv[1] if len(sys.argv) > 1 else '.'
    cwd = os.getcwd()
    file_name = Path(__file__).stem
    defaultjson = cwd+"/"+file_name+".json"
    
    settingFile = sys.argv[1] if len(sys.argv) > 1 else defaultjson

    #ログ設定（ローテート）
    formatter = '%(asctime)s:%(levelname)s:%(name)s:%(message)s'
    logging.basicConfig(level=logging.INFO,
                        format=formatter)
    # ロガーの作成
    logger = logging.getLogger(Path(settingFile).stem)
    # ログレベルをDEBUGへ変更
    logger.setLevel(logging.DEBUG)
    # ログローテーションのハンドラーを設定
    #   maxBytes: 1ログファイルの上限サイズ(byte単位)10485760=10MB
    #   backupCount: バックアップとして保持するログファイル数
    
    logpath = os.path.dirname(settingFile)
    logfile = Path(settingFile).stem
    h = logging.handlers.RotatingFileHandler(logpath+"/"+logfile+'.log',
                                            maxBytes=10485760,
                                            backupCount=5)
    # フォーマットを設定
    h.setFormatter(logging.Formatter(formatter))
    # ロガーにハンドラーを設定
    logger.addHandler(h)
    
    print(settingFile)
    json_file = open(settingFile, 'r')
    Pref = json.load(json_file)

    tmpPath1 = Pref["FMSpath"]
    FMSpath = tmpPath1.replace('\\','/')#/Data/Document/まで
    tmpPath2 = Pref["Watchpath"]
    Watchpath = tmpPath2.replace('\\','/')
    CheckPath = FMSpath+Watchpath
    CheckPathbu = FMSpath+"Bakup-"+Watchpath

    fm_host = Pref["fm_host"]
    fm_script =  Pref["fm_script"]
    fm_database = Pref["fm_database"]
    fm_layout = Pref["fm_layout"]
    fm_user = Pref["fm_user"]
    fm_password = Pref["fm_password"]
    fm_pkcs12 = Pref["fm_pkcs12"]
    fm_pkcs12_password = Pref["fm_pkcs12_password"]

    logger.info("Start fWatch2DataAPI")
    logger.info("Prefjson:"+settingFile)
    logger.info("logfile:"+logpath+"/"+logfile+'.log')
    logger.info("CheckPath:"+CheckPath)
    logger.info("fm_host:"+fm_host)
    logger.info("fm_script:"+fm_script)
    logger.info("fm_database:"+fm_database)
    logger.info("fm_layout:"+fm_layout)
    logger.info("fm_user:"+fm_user)
    logger.info("fm_password:"+fm_password)
    logger.info("fm_pkcs12:"+fm_pkcs12)
    logger.info("fm_pkcs12_password:"+fm_pkcs12_password)

    #Daemonni
    
    time.sleep(60)

    #バックアップフォルダを作成
    try:
        if not os.path.exists(CheckPathbu):
            os.makedirs(CheckPathbu)#バックアップ用フォルダを作成（階層）
    except Exception as e:
        logger.info("[Exception(219)]" + repr(e)) 

    #監視ディレクトリの初期化:既存ファイルがある場合はBackupに移動
    try:
        files = glob.glob(CheckPath+"/*")
        for file in files:
            tmpFname = os.path.basename(file)
            if(os.path.isfile(file) and not tmpFname.startswith(".")):
                mvpath = CheckPathbu+"/"+tmpFname
                shutil.move( file , mvpath )#ファイルのみバックアップに退避(同名の場合上書き)
    except Exception as e:
       logger.info("[Exception(230)]" + repr(e)) 

    event_handler = LoggingEventHandler2()
    observer = PollingObserver()
    observer.schedule(event_handler, CheckPath, recursive=True)
    observer.start()

    try:
        while True:
            time.sleep(1)
            
    except KeyboardInterrupt:
        observer.stop()
    observer.join()
    
