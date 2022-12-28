
import sys
import time
import os
import logging
import logging.handlers
import json
import inspect
import glob
from pathlib import Path
from dirsync import sync
from watchdog.observers import Observer
from watchdog.events import LoggingEventHandler


#LoggingEvenHandlerを上書きして動作を変更
class LoggingEventHandler2(LoggingEventHandler):
    def on_created(self, event):    
        logger.info("[Catch]" + event.src_path)

        try:
            filename = os.path.basename(event.src_path)
            logger.info("filename: " + filename)  
        except Exception as e:
            logger.info("Exception(23): " + repr(e))  

        path_1=Dir1+'/'+filename #Database
        path_2=Dir2+'/'+filename #Documents
        path_3=Dir3+'/'+filename #HTTPdoc

        try:
            os.makedirs(path_3)
            os.chmod(path_3,0o775)
        except Exception as e:
            logger.info("Exception(34): " + repr(e))  
        
        #Database > HTTPdoc
        try:
            sync(path_1, path_3, 'sync',create = True)
            logger.info("syc: " + path_1)  
        except Exception as e:
            logger.info("Exception(41): " + repr(e))  
        #Documents > HTTPdoc
        try:
            sync(path_2, path_3, 'sync',create = True)
            logger.info("syc: " + path_2)  
        except Exception as e:
            logger.info("Exception(47): " + repr(e)) 

            

        #登録ファイルを削除
        try:
            os.remove(event.src_path)
            logger.info("[Remove]" + event.src_path)
        except Exception as e:
            logger.info("Exception(45): " + repr(e)) 

        return

def location(depth=0):
  frame = inspect.currentframe().f_back
  return os.path.basename(frame.f_code.co_filename), frame.f_code.co_name, frame.f_lineno        
    
if __name__ == "__main__":
    #path = sys.argv[1] if len(sys.argv) > 1 else '.'
    cwd = os.getcwd()
    file_name = Path(__file__).stem
    defaultjson = cwd+"/"+file_name+".json"
    
    settingFile = sys.argv[1] if len(sys.argv) > 1 else defaultjson

    print(settingFile)

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
    # ログファイルはOS毎に異なる
    logpath = os.path.dirname(settingFile)
    logfile = Path(settingFile).stem
    h = logging.handlers.RotatingFileHandler(logpath+"/"+logfile+'.log',
                                            maxBytes=10485760,
                                            backupCount=5)
    # フォーマットを設定
    h.setFormatter(logging.Formatter(formatter))
    # ロガーにハンドラーを設定
    logger.addHandler(h)
    
    json_file = open(settingFile, 'r')
    Pref = json.load(json_file)

    tmpPath = Pref["WatchDir"]
    WatchDir = tmpPath.replace('\\','/')

    CheckPath = WatchDir
    
    #print("CheckPath:"+CheckPath)

    Dir1 = Pref["Dir1"]
    Dir2 = Pref["Dir2"]
    Dir3 = Pref["Dir3"]

    logger.info("Start")
    logger.info("Prefjson:"+settingFile)
    logger.info("logfile:"+logpath+"/"+logfile+'.log')
    logger.info("WatchDir:"+WatchDir)
    logger.info("Dir1:"+Dir1)
    logger.info("Dir2:"+Dir2)
    logger.info("Dir3:"+Dir3)
    #基本パスの確認
    if not os.path.isdir(Dir1):
        logger.info(Dir1+" is noting! Please check path!!")

    if not os.path.isdir(Dir2):
        logger.info(Dir2+" is noting! Please check path!!")

    if not os.path.isdir(Dir3):
        logger.info(Dir3+" is noting! Please check path!!")

    #監視ディレクトリの初期化
    files = glob.glob(WatchDir+"/*") 
    for file in files:
        os.remove(file)

    event_handler = LoggingEventHandler2()
    observer = Observer()
    observer.schedule(event_handler, CheckPath, recursive=True)
    observer.start()
    
    try:
        while True:
            time.sleep(1)   
    except KeyboardInterrupt:
        observer.stop()
    observer.join()
    

