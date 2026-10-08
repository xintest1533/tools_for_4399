# -*- coding: utf-8 -*-
"""最终: 不跟随重定向, 从 302 Location 提取 auth_string"""
import urllib.request as u, urllib.parse, time, sys, io, re
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

COOKIE = ('UM_distinctid=1a0f779ab84c9-07ea066e254ebb-22182b6d-144000-1a0f779ab853e5; '
          '_4399stats_vid=17908583412654777; Puser=1462308186; '
          'Pnick=%E5%B0%B1ask%E7%9A%84; Qnick=; home4399=yes; _gprp_c=""; '
          'ptusertype=kabu_xy.4399_login; '
          'USESSIONID=9e444898-2ae6-4790-9410-88914d553351; '
          'Uauth=4399|1|2026103|kabu_xy.|1791019728435|00c47e5af4a4b0f0c601fd9a8ada11ae; '
          'Pauth=273622610|1462308186|t3ce7n11018fd1c4157920250671e047|1791019728|10002|66d1362efb6837aa2b83773c1f9da46c|0; '
          'ck_accname=1462308186; Xauth=de76897f11cf4a2b73b2a2abaf62acaf')

class NoRedirect(u.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None  # 不跟随

def get_auth_string(cookies=COOKIE):
    v = str(int(time.time()*1000))
    ret = urllib.parse.quote('http://news.4399.com/login/kbxy.html?reg=0&pass=1&v='+v, safe='')
    url = ('http://ptlogin.4399.com/ptlogin/checkKidLoginUserCookie.do?'
           'appId=kabu_xy&level=8&loginLevel=8&regLevel=8&bizId=1202000651&canBack=true'
           '&gameUrl=http%3A%2F%2Fenter.wanwan4399.com%2Fbin-debug%2FKBgameindex.html'
           f'&css=&onLineStart=false&retUrl={ret}')
    opener = u.build_opener(NoRedirect)
    req = u.Request(url, headers={
        'User-Agent':'Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 Chrome/101.0.9999.0 Safari/537.36',
        'Referer':'http://news.4399.com/','Cookie':cookies,
        'Accept':'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Encoding':'gzip, deflate'})
    try:
        resp = opener.open(req, timeout=15)
        print('状态:', resp.status)
        loc = resp.headers.get('Location')
        print('Location:', loc)
    except u.HTTPError as e:
        print('HTTP状态:', e.code)
        loc = e.headers.get('Location')
        print('Location:', loc)
        if loc:
            auth = loc.split('?',1)[1]
            print('\n>>> auth_string:\n', auth)
            return auth
    return None

if __name__ == '__main__':
    a = get_auth_string()
    if a:
        with open('auth_string.txt','w',encoding='utf-8') as f:
            f.write(a+'\n')
        print('已写入 auth_string.txt')
