#! /usr/bin/env python
# -*- coding: utf-8 -*-
#======================================================================
#
# translator.py - 命令行翻译（谷歌，百度）
#
# Created by skywind on 2019/06/14
# Version: 1.0.2, Last Modified: 2019/06/18 18:40
# ------------
# Modified by twinblade on 2024/08/07
#
#======================================================================
import sys
import time
import os
import random
import copy
import json
import codecs
import pprint
import socket
import string

#----------------------------------------------------------------------
# 语言的别名
#----------------------------------------------------------------------
langmap = {
    "arabic": "ar",
    "bulgarian": "bg",
    "catalan": "ca",
    "chinese": "zh-CN",
    "chinese simplified": "zh-CHS",
    "chinese traditional": "zh-CHT",
    "czech": "cs",
    "danish": "da",	
    "dutch": "nl",
    "english": "en",
    "estonian": "et",
    "finnish": "fi",
    "french": "fr",
    "german": "de",
    "greek": "el",
    "haitian creole": "ht",
    "hebrew": "he",
    "hindi": "hi",
    "hmong daw": "mww",
    "hungarian": "hu",
    "indonesian": "id",
    "italian": "it",
    "japanese": "ja",
    "klingon": "tlh",
    "klingon (piqad)":"tlh-Qaak",
    "korean": "ko",
    "latvian": "lv",
    "lithuanian": "lt",
    "malay": "ms",
    "maltese": "mt",
    "norwegian": "no",
    "persian": "fa",
    "polish": "pl",
    "portuguese": "pt",
    "romanian": "ro",
    "russian": "ru",
    "slovak": "sk",
    "slovenian": "sl",
    "spanish": "es",
    "swedish": "sv",
    "thai": "th",
    "turkish": "tr",
    "ukrainian": "uk",
    "urdu": "ur",
    "vietnamese": "vi",
    "welsh": "cy"
}

#----------------------------------------------------------------------
# BasicTranslator
#----------------------------------------------------------------------
class BasicTranslator(object):

    def __init__ (self, name, **argv):
        self._name = name
        self._config = {}  
        self._options = argv
        self._session = None
        self._agent = None

    def request (self, url, config, data = None, post = False, header = None):
        import requests
        if not self._session:
            self._session = requests.Session()
        argv = {}
        if header is not None:
            header = copy.deepcopy(header)
        else:
            header = {}
        if self._agent:
            header['User-Agent'] = self._agent
        argv['headers'] = header
        timeout = config.get('connection_timeout', 7)
        if config.get('proxy-enabled', False):
            argv['proxies'] = {
                'http': 'http://'+config.get('proxy')+'/',
                'https': 'http://'+config.get('proxy')+'/'
            }
        if timeout:
            argv['timeout'] = float(timeout)
        if not post:
            if data is not None:
                argv['params'] = data
        else:
            if data is not None:
                argv['data'] = data
        if not post:
            r = self._session.get(url, **argv)
        else:
            r = self._session.post(url, **argv)
        return r

    def http_get (self, url, config, data = None, header = None):
        return self.request(url, config, data, False, header)

    def http_post (self, url, config, data = None, header = None):
        return self.request(url, config, data, True, header)

    def url_unquote (self, text, plus = True):
        import urllib.parse
        if plus:
            return urllib.parse.unquote_plus(text)
        return urllib.parse.unquote(text)

    def url_quote (self, text, plus = True):
        import urllib.parse
        if plus:
            return urllib.parse.quote_plus(text)
        return urllib.parse.quote(text)

    def create_translation (self, sl = None, tl = None, text = None):
        res = {}
        res['engine'] = self._name
        res['sl'] = sl              # 来源语言
        res['tl'] = tl              # 目标语言
        res['text'] = text          # 需要翻译的文本
        res['phonetic'] = None      # 音标
        res['definition'] = None    # 简单释义
        res['explain'] = None       # 分行解释
        return res

    # 翻译结果：需要填充如下字段
    def translate (self, sl, tl, text):
        return self.create_translation(sl, tl, text)

    # 识别中英文文本
    def check_en_or_zh(self, text, threshold):
        english_count = 0
        chinese_count = 0
        other_count = 0

        for char in text:
            if char in string.whitespace + string.punctuation:
                continue
            if '\u4e00' <= char <= '\u9fff':
                chinese_count += 1
            elif char in string.ascii_letters:
                english_count += 1
            else:
                other_count += 1
        
        total = english_count + chinese_count + other_count
        if total == 0:
            return 'Unknown'
        
        chinese_ratio = chinese_count / total
        english_ratio = english_count / total

        if english_ratio >= threshold:
            return 'English'
        if chinese_ratio >= threshold:
            return 'Chinese'
        return 'Mixed or Unknown'

    # 设置源/目标语言
    def set_st_language (self, sl, tl, text, threshold = 0.5):
        if ((not sl) or sl == 'auto') and ((not tl) or tl == 'auto'):
            if self.check_en_or_zh(text, threshold) == 'English':
                sl, tl = ('en-US', 'zh-CN')
            else:
                sl, tl = ('zh-CN', 'en-US')
        if sl.lower() in langmap:
            sl = langmap[sl.lower()]
        if tl.lower() in langmap:
            tl = langmap[tl.lower()]
        return sl, tl
    
    def md5sum (self, text):
        import hashlib
        m = hashlib.md5()
        if sys.version_info[0] < 3:
            if isinstance(text, unicode):   # noqa: F821
                text = text.encode('utf-8')
        else:
            if isinstance(text, str):
                text = text.encode('utf-8')
        m.update(text)
        return m.hexdigest()

#----------------------------------------------------------------------
# Google Translator
#----------------------------------------------------------------------
class GoogleTranslator (BasicTranslator):

    def __init__ (self, **argv):
        super(GoogleTranslator, self).__init__('google', **argv)
        self._agent = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:59.0)'
        self._agent += ' Gecko/20100101 Firefox/59.0'

    def get_url (self, config, sl, tl, qry):
        http_host = config.get('host', 'translate.google.com')
        qry = self.url_quote(qry)
        url = 'https://{}/translate_a/single?client=gtx&sl={}&tl={}&dt=at&dt=bd&dt=ex&' \
              'dt=ld&dt=md&dt=qca&dt=rw&dt=rm&dt=ss&dt=t&q={}'.format(
                      http_host, sl, tl, qry)    # noqa: E216
        return url

    def translate (self, config, sl, tl, text):
        sl, tl = self.set_st_language(sl, tl, text, float(config.get('main_language_threshold', 0.5)))
        self.text = text
        url = self.get_url(config, sl, tl, text)
        r = self.http_get(url, config)
        if not r:
            return None
        try:
            obj = r.json()
        except:
            return None
        # pprint.pprint(obj)
        res = self.create_translation(sl, tl, text)
        res['phonetic'] = self.get_phonetic(obj)
        res['definition'] = self.get_definition(obj)
        res['explain'] = self.get_explain(obj)
        res['detail'] = self.get_detail(obj)
        res['alternative'] = self.get_alternative(obj)
        return res

    def get_phonetic (self, obj):
        for x in obj[0]:
            if len(x) == 4:
                return x[3]
        return None

    def get_definition (self, obj):
        paraphrase = ''
        for x in obj[0]:
            if x[0]:
                paraphrase += x[0]
        return paraphrase

    def get_explain (self, obj):
        explain = []
        if obj[1]:
            for x in obj[1]:
                expl = '[{}] '.format(x[0][0])
                for i in x[2]:
                    expl += i[0] + ';'
                explain.append(expl)
        return explain

    def get_detail (self, resp):
        result = []
        if len(resp) < 13:
            return None
        for x in resp[12]:
            result.append('[{}]'.format(x[0]))
            for y in x[1]:
                result.append('- {}'.format(y[0]))
                if len(y) >= 3:
                    result.append('  * {}'.format(y[2]))
        return result

    def get_alternative (self, resp):
        definition = self.get_definition(resp)
        result = []
        if len(resp) < 6:
            return None
        for x in resp[5]:
            # result.append('- {}'.format(x[0]))
            for i in x[2]:
                if i[0] != definition:
                    result.append(' * {}'.format(i[0]))
        return result

#----------------------------------------------------------------------
# Baidu Translator
#----------------------------------------------------------------------
class BaiduTranslator (BasicTranslator):

    def __init__ (self, **argv):
        super(BaiduTranslator, self).__init__('baidu', **argv)
        langmap = {
            'zh-cn': 'zh',
            'zh-chs': 'zh',
            'zh-cht': 'cht',
            'en-us': 'en', 
            'en-gb': 'en',
            'ja': 'jp',
        }
        self.langmap = langmap

    def convert_lang (self, lang):
        t = lang.lower()
        if t in self.langmap:
            return self.langmap[t]
        return lang

    def translate (self, config, sl, tl, text):
        if 'appid' not in config:
            sys.stderr.write('error: missing appid in [baidu] section\n')
            sys.exit()
        if 'key' not in config:
            sys.stderr.write('error: missing key in [baidu] section\n')
            sys.exit()
        self.appid = config['appid']
        self.key = config['key']
        
        sl, tl = self.set_st_language(sl, tl, text, float(config.get('main_language_threshold', 0.5)))
        req = {}
        req['q'] = text
        req['from'] = self.convert_lang(sl)
        req['to'] = self.convert_lang(tl)
        req['appid'] = self.appid
        req['salt'] = str(int(time.time() * 1000) + random.randint(0, 10))
        req['sign'] = self.sign(text, req['salt'])
        url = "https://fanyi-api.baidu.com/api/trans/vip/translate"
        r = self.http_post(url, config, req)
        resp = r.json()
        res = {}
        res['text'] = text
        res['sl'] = sl
        res['tl'] = tl
        res['info'] = resp
        res['translation'] = self.render(resp)
        res['html'] = None
        res['xterm'] = None
        return res

    def sign (self, text, salt):
        t = self.appid + text + salt + self.key
        return self.md5sum(t)

    def render (self, resp):
        output = ''
        result = resp['trans_result']
        for item in result:
            output += '' + item['src'] + '\n'
            output += ' * ' + item['dst'] + '\n'
        return output

#----------------------------------------------------------------------
# 加载配置文件
#----------------------------------------------------------------------
def loadConfig ():
    ininame = os.path.expanduser('~/.config/translator/config.ini')
    config = loadIni(ininame)
    if not config:
        return False, config
    return True, config

def loadIni (ininame, codec = None):
    config = {}
    if not ininame:
        return None
    elif not os.path.exists(ininame):
        return None
    try:
        content = open(ininame, 'rb').read()
    except IOError:
        content = b''
    if content[:3] == b'\xef\xbb\xbf':
        text = content[3:].decode('utf-8')
    elif codec is not None:
        text = content.decode(codec, 'ignore')
    else:
        codec = sys.getdefaultencoding()
        text = None
        for name in [codec, 'gbk', 'utf-8']:
            try:
                text = content.decode(name)
                break
            except:
                pass
        if text is None:
            text = content.decode('utf-8', 'ignore')
    import configparser
    cp = configparser.ConfigParser(interpolation = None)
    cp.read_string(text)
    for sect in cp.sections():
        for key, val in cp.items(sect):
            lowsect, lowkey = sect.lower(), key.lower()
            config.setdefault(lowsect, {})[lowkey] = val
    if 'default' not in config:
        config['default'] = {}
    return config

#----------------------------------------------------------------------
# 分析命令行参数
#----------------------------------------------------------------------
def getopt (argv):
    args = []
    options = {}
    if argv is None:
        argv = sys.argv[1:]
    index = 0
    count = len(argv)
    while index < count:
        arg = argv[index]
        if arg != '':
            head = arg[:1]
            if head != '-':
                break
            if arg == '-':
                break
            name = arg.lstrip('-')
            key, _, val = name.partition('=')
            options[key.strip()] = val.strip()
        index += 1
    while index < count:
        args.append(argv[index])
        index += 1
    return options, args

#----------------------------------------------------------------------
# 分析是否正在使用代理
#----------------------------------------------------------------------
def checkProxyUsing (proxy):
    if proxy == None:
        return False
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            if s.connect_ex((proxy[0], int(proxy[1]))) == 0:
                return True
    return False

#----------------------------------------------------------------------
# 引擎注册
#----------------------------------------------------------------------
ENGINES = {
    'google': GoogleTranslator,
    'baidu': BaiduTranslator,
}

#----------------------------------------------------------------------
# 主程序
#----------------------------------------------------------------------
def main(argv = None):
    load_config_success, ini_config = loadConfig()
    if not load_config_success:
        print("set an initialization file at `~/.config/translator/config.ini` first!")
        return -1
    
    if argv is None:
        argv = sys.argv
    argv = [ n for n in argv ]
    options, args = getopt(argv[1:])
    
    proxy = ini_config['default'].get('proxy').split(':')
    config = {}
    if checkProxyUsing(proxy):
        engine = 'google'
        config['proxy-enabled']=True
    else:
        engine = 'baidu'
        config['proxy-enabled']=False
    config.update(ini_config['default'])
    config.update(ini_config[engine])
        
    sl = options.get('from')
    if not sl:
        sl = 'auto'
    tl = options.get('to')
    if not tl:
        tl = 'auto'
    if not args:
        print('usage: translator.py {--from=xx} {--to=xx} text')
        print('engines:', list(ENGINES.keys()))
        return -2
    text = ' '.join(args)

    cls = ENGINES.get(engine)
    if not cls:
        print('bad engine name: ' + engine)
        return -3
    translator = cls()

    res = translator.translate(config, sl, tl, text)

    if not res:
        return -4
    if 'text' in res:
       if res['text']:
           print(res['text'])
    if 'phonetic' in res:
        if res['phonetic'] and ('phonetic' in options):
            print('[' + res['phonetic'] + ']')
    if 'definition' in res:
        if res['definition']:
            print(res['definition'])
    if 'explain' in res:
        if res['explain']:
            print('\n'.join(res['explain']))
    elif 'translation' in res:
        if res['translation']:
            if '*' in res['translation']:
                print(res['translation'].split("*", 1)[1].strip())
            else:
                print(res['translation'])
    if 'alternative' in res:
        if res['alternative']:
            print("-"*(len(res['alternative'][0])+5 if len(res['alternative'][0])+5<30 else 30+5))
            print('\n'.join(res['alternative']))
    return 0

if __name__ == '__main__':
    main()
