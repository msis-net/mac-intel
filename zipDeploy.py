
import sys
import time
import os
import logging
import logging.handlers
import json
import shutil
import zipfile
import codecs
import glob
from pathlib import Path
from watchdog.observers import Observer
from watchdog.events import LoggingEventHandler

#zip解凍モジュール
def unzip(compress_file, target=None):
    zipobj = zipfile.ZipFile(compress_file, 'r')
    zipobj.extractall(target)   

#LoggingEvenHandlerを上書きして動作を変更
class LoggingEventHandler2(LoggingEventHandler):
    def on_created(self, event):    
        logger.info("[Catch]" + event.src_path)
        try:
            filename = os.path.basename(event.src_path)
            tableName = Path(filename).stem
            logger.info("filename: " + filename)  
        except Exception as e:
            logger.info("Exception(30): " + repr(e))  

        #FileMakerが外部保存したファイルには_<番号>.zipのようになる場合があるので、解凍元ファイルは対象のアーカイブ名を指定する
        files = glob.glob(Dir1+"/*.zip") #zip解凍
        for zip_path in files:
            zipName = Path(zip_path).stem
            if(tableName in zipName):
                path_1=zip_path #Database以下の外部保存されたzipファイルの実名を指定

        #path_1=Dir1+'/'+filename #Database
        path_2=Dir2+'/'+filename #Documents

        #ファイル移動
        try:
            shutil.copyfile(path_1, path_2)
            logger.info("[MoveFrom]" + path_1)
            logger.info("[MoveTo]" + path_2)  
        except Exception as e:
            logger.info("Exception(41): " + repr(e))    

        try:
            unzip(path_2, Dir2) #解凍
            logger.info("[UnZip]" + path_2)
            #print(path_2+":"+Path(path_2).stem)

            #csv>mer変換
            csv_file = Dir2+'/'+Path(path_2).stem+".csv"
            csv_rows = codecs.open(csv_file, "r", "utf-8")
            mer_filepath=Dir2+'/'+Path(csv_file).stem+".mer"
            mer_file=codecs.open(mer_filepath, "w", "utf-8")
            count=-1 #１行目はレコード件数に入れない
            for row in csv_rows:
                line = row.replace(' ','') #空白除去
                mer_file.write(line)
                count += 1
            logger.info("[Merge("+str(count)+")]"+mer_filepath) 
            mer_file.close()
            csv_rows.close()
            os.remove(csv_file)
            os.chmod(mer_filepath,0o777)
            os.remove(path_2)
            logger.info("[Merge]" + mer_filepath)
        except Exception as e:
            logger.info("Exception(45): " + repr(e))    

        #トリガ登録ファイルを削除
        try:
            os.remove(event.src_path)
            logger.info("[Remove]" + event.src_path)
        except Exception as e:
            logger.info("Exception(45): " + repr(e)) 


    
    
if __name__ == "__main__":
    #path = sys.argv[1] if len(sys.argv) > 1 else '.'
    cwd = os.getcwd()
    file_name = Path(__file__).stem
    defaultjson = cwd+"/"+file_name+".json"
    
    settingFile = sys.argv[1] if len(sys.argv) > 1 else defaultjson

    #print(settingFile)

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

    logger.info("Start")
    logger.info("Prefjson:"+settingFile)
    logger.info("logfile:"+logpath+"/"+logfile+'.log')
    logger.info("WatchDir:"+WatchDir)
    logger.info("Dir1:"+Dir1)
    logger.info("Dir2:"+Dir2)

    json_file.close()
    #基本パスの確認
    if not os.path.isdir(Dir1):
        logger.info(Dir1+" is noting! Please check path!!")

    if not os.path.isdir(Dir2):
        logger.info(Dir2+" is noting! Please check path!!")

    #監視ディレクトリの初期化
    files = glob.glob(WatchDir+"/*") 
    for file in files:
        os.remove(file)
    
    #zipディレクトリの初期化
    files = glob.glob(Dir1+"/*.zip") 
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
    

