# coding: utf-8
from curl_cffi.requests import AsyncSession
from quart import Request
import json
import re
import time
import random
import asyncio


# https://api.weixin.qq.com/cgi-bin/token?grant_type=client_credential&appId=APPID&secret=APPSECRET


class WeQrcodeAPI:
    # https://www.cnblogs.com/1zero1/p/13470610.html
    # url = 'https://open.weixin.qq.com/connect/qrconnect?appid=wxde40e023744664cb&redirect_uri=https%3a%2f%2fmp.weixin.qq.com%2fdebug%2fcgi-bin%2fwebdebugger%2fqrcode&scope=snsapi_login&state=login'
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.114 Safari/537.36",
        "Content-Type": "text/plain;charset=UTF-8"
    }
    clientversion = '1062412040'
    
    
    async def get_qrcode(self) -> dict[str, str]:
        '''
        获取二维码链接 
        '''
        url = f'https://open.weixin.qq.com/connect/qrconnect?appid=wxde40e023744664cb&redirect_uri=https%3a%2f%2fmp.weixin.qq.com%2fdebug%2fcgi-bin%2fwebdebugger%2fqrcode&scope=snsapi_login&state=login&f=xml&{int(time.time())}&_={int(time.time())}'
        try:
            # https://open.weixin.qq.com/connect/qrcode/051rwuoN1YfJkl2D
            async with AsyncSession(headers=self.headers, impersonate='safari_ios',timeout=10) as session:
                res = await session.get(url)
                uuid = ''.join(re.findall(r'<uuid><!\[CDATA\[(.*?)\]\]></uuid>', res.text))
                return {
                    "uuid": uuid,
                    "qrcode": f"https://open.weixin.qq.com/connect/qrcode/{uuid}"
                }
        except Exception:
            return {
                "errcode": -1,
                "errmsg": "获取二维码链接失败",
            }
    
    async def fetch_newticket(self, wx_code:str) -> dict[str, str]:
        '''
        获取微信登录链接
        '''
        try:
            async with AsyncSession(headers=self.headers, impersonate='safari_ios',timeout=15) as session:
                url = f'https://mp.weixin.qq.com/debug/cgi-bin/webdebugger/qrcode?code={wx_code}&state=login'
                res = await session.get(url)
                ticket = res.headers.get('debugger-ticket')
                newticket = res.headers.get('debugger-newticket')
                signature = res.headers.get('debugger-signature')
                data = res.json()
                del data["baseresponse"]
                data |= {"ticket": ticket, "newticket": newticket, "signature": signature}
                return data
        except Exception as e:
            return {
                "errcode": -1,
                "errmsg": str(e),
            }
            
    async def refreshticket(self, signature:str,openid:str) -> dict[str, str]:
        url = f"https://mp.weixin.qq.com/debug/cgi-bin/webdebugger/refreshticket?os=win&clientversion={self.clientversion}"
        payload = {
            "signature": signature,
            "openid": openid
        }
        try:
            async with AsyncSession(headers=self.headers, impersonate='safari_ios',timeout=10) as session:
                res = await session.post(url, json=payload)
                print(res.headers)
                newticket = res.headers.get('debugger-newticket')
                data = res.json()
                data |= {"newticket": newticket}
                return data
        except Exception as e:
            return {
                "errcode": -1,
                "errmsg": str(e),
            }
        

async def verify_plugin(newticket:str, appid:str = "wx21ccd3e4154404f5") -> bool:
    url = "https://servicewechat.com/wxa-dev-logic/verifyplugin"
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.114 Safari/537.36",
        "Content-Type": "text/plain;charset=UTF-8"
    }
    params = {
        "_r": round(random.random(), 16),
        "newticket": newticket,
        "appid": appid,
        "platform": "0",
        "ext_appid": "",
        "deployAppid": "",
        "os": "darwin",
        "clientversion": "1062412040",
    }
    info = {"plugins": [{"provider": "wx1fe8d9a3cb067a75", "inner_version": 3}]}
    ext_info = json.dumps(info, ensure_ascii=False, separators=(",", ":"))
    data = {"ext_info": ext_info}
    try:
        async with AsyncSession(headers=headers, impersonate='safari_ios',timeout=10) as session:
            res = await session.post(url, params=params, json=data)
            data = res.json()
            # print(data)
            [result] = data.get("list", [])
            *_, signature, noncestr, timestamp, _ = result.values()
            return {
                "signature": signature,
                "noncestr": noncestr,
                "timestamp": timestamp,
            }
    except Exception as e:
        return {"errcode": -1, "errmsg": str(e)}
    
async def captcha_client(
    request: Request, hostsign: dict = None, timeout: int = 10
) -> dict:
    base_url = "https://turing.captcha.qcloud.com"
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.114 Safari/537.36",
        "Accept-Encoding": "gzip,compress,br,deflate",
        "charset": "utf-8",
        # "Referer": "https://servicewechat.com/wxe65090bdafbc19cf/50/page-frame.html",
        "referer": "https://servicewechat.com/wx21ccd3e4154404f5/devtools/page-frame.html",
        "X-WECHAT-HOSTSIGN": json.dumps(hostsign),
    }
    params = {
        "lang": "zh-cn",
        "userLanguage": "zh-cn",
        "customize_aid": "194237199",
        "aid": "194237199",
        "aidEncrypted": "",
    }
    try:
        async with AsyncSession(
            headers=headers,
            impersonate="safari_ios",
            base_url=base_url,
            timeout=timeout,
        ) as session:
            if request.method == "POST":
                session.headers.update(
                    {"Content-Type": "application/x-www-form-urlencoded"}
                )
                # print(payload)
                data = await request.json
                res = await session.post(url=request.path, data=data)
                return res.json()
            res = await session.get(url=request.path, params=params)
            return json.loads(res.text[1:-1])
    except Exception as e:
        return {"error": str(e)}


async def main():
    newticket = "hsaVzxhz3v4EQyBN5Htje1WtfYSIfX-XTSS0Sb2D-ho"
    # res = await verify_plugin(newticket)
    # print(res)
    wxapi = WeQrcodeAPI()
    res = await wxapi.refreshticket("7XvbJ1XURx-6EGA_J5QgFeYbTB8849SCmE5N-nymwlY","o6zAJs0KYe6mn6S8-0z2uIUDGd3k")
    print(res)



if __name__ == "__main__":
    asyncio.run(main())
