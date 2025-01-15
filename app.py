# coding: utf-8
from quart import Quart, render_template
from quart_cors import cors
from dotenv import load_dotenv, set_key, get_key, unset_key
from utils.api import WeQrcodeAPI, verify_plugin
import json
import time
import os


app = Quart(__name__, static_folder="static", template_folder="template")
cors(app)

timelimit = int(os.environ.get("timelimit", 600))

"""
"errorCode": "12"  # 验证码错误 请求频繁 
缺少 headers ：
X-WECHAT-HOSTSIGN: {"noncestr":"39d87ee9b1a24f14ffce6379fc180263","timestamp":1736271489,"signature":"9e2bd3136f64687a83f2cb95844b7c9aa91c53af"}
"""

wxapi = WeQrcodeAPI()

class TIMES:
    timep: int = int(time.time())

class HOSTSIGN:
    noncestr: str=None
    timestamp: str=None
    signature: str=None
    
    @classmethod
    def to_dict(cls):
        return {
            'signature': cls.signature,
            'timestamp': cls.timestamp,
            'noncestr': cls.noncestr
        }
        
    @classmethod
    def from_dict(cls, value_dict:dict):
        cls.noncestr = value_dict.get('noncestr')
        cls.signature = value_dict.get('signature')
        cls.timestamp = value_dict.get('timestamp')
    
class TICKETS:
    signature: str=None
    openid: str=None
    newticket: str=None
    
    @classmethod
    def to_dict(cls):
        return {
            'signature': cls.signature,
            'openid': cls.openid,
            'newticket': cls.newticket
        }
    
    @classmethod
    def from_dict(cls, value_dict:dict):
        cls.signature = value_dict.get('signature')
        cls.openid = value_dict.get('openid')
        cls.newticket = value_dict.get('newticket')
        
class EnvManager:
    def __init__(self, env_file='.env'):
        self.env_file = env_file
        load_dotenv(env_file)
    
    def set_dict(self, key, value_dict):
        """存储字典值"""
        json_str = json.dumps(value_dict, ensure_ascii=False)
        set_key(self.env_file, key, json_str)
        load_dotenv(self.env_file, override=True)
    
    def get_dict(self, key):
        """读取字典值"""
        value = get_key(self.env_file, key)
        return json.loads(value) if value else {}
    
    def set_str(self, key, value_str):
        """存储字符串值"""
        set_key(self.env_file, key, value_str)
        load_dotenv(self.env_file, override=True)
    
    def get_str(self, key):
        """读取字符串值"""
        return get_key(self.env_file, key)
    
    def unset_key(self, key):
        """删除键值对"""
        unset_key(self.env_file, key)
        load_dotenv(self.env_file, override=True)

Env = EnvManager('./.env')

@app.route("/")
async def index():
    TICKETS.from_dict(Env.get_dict('TICKETS'))
    return await render_template("index.html")

@app.get("/qrcode")
async def qrcode():
    res = await wxapi.get_qrcode()
    app.logger.info(res)
    return res

@app.get("/newticket/<wxcode>")
async def newticket(wxcode:str):
    res = await wxapi.fetch_newticket(wxcode)
    app.logger.info(f"res: {res}")
    if newticket:= res.get('newticket'):
        TICKETS.signature = res['signature']
        TICKETS.openid = res['openid']
        TICKETS.newticket = newticket
        Env.set_dict('TICKETS', TICKETS.to_dict())
    return res

@app.get("/gethostsign")
async def gethostsign():
    t = int(time.time())
    if t - TIMES.timep < timelimit:
        hostsign = HOSTSIGN.to_dict()
        return hostsign if all(hostsign.values()) else {'errmsg': '缺少HOSTSIGN参数'}
    TIMES.timep = t
    if not all(TICKETS.to_dict().values()):
        return {'errmsg': '缺少TICKETS参数'}
    res = await verify_plugin(TICKETS.newticket)
    if errmsg:=res.get('errmsg'):
        res = await wxapi.refreshticket(TICKETS.signature, TICKETS.openid)
        errmsg = res.get('errmsg')
        if errmsg:
            return {'errmsg': errmsg}
        TICKETS.newticket = res['newticket']
        res = await verify_plugin(TICKETS.newticket)
        if errmsg:=res.get('errmsg'):
            return {'errmsg': errmsg}
    HOSTSIGN.from_dict(res)
    return res



if __name__ == "__main__":
    port = int(os.environ.get("PORT", 1188))
    app.run(host="0.0.0.0", port=80, debug=True)
    
