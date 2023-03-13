# -*- coding: utf-8 -*-
# !/usr/bin/python
"""=========================================
@author: James
@file: geek_download.py
@create_time: 2023/2/24 21:29
@file specification: 下载课程音频图片
    极客时间官网地址：https://time.geekbang.org/
    流程： 读取课程文件 -- 下载对应音频
========================================="""
import time
import datetime
import requests
import re
from copy import deepcopy
import logging
import os
import pathlib

# 定义日志相关内容
logging.basicConfig(
    format=
    '%(asctime)s - %(pathname)s[line:%(lineno)d] - %(levelname)s: %(message)s',
    level=logging.INFO)
handler = logging.FileHandler(filename='geek_download.log',
                              mode='w',
                              encoding='utf-8')
log = logging.getLogger(__name__)
log.addHandler(handler)

# 定义全局变量
FINISH_ARTICLES = []
ALL_ARTICLES = []


class RequestError(Exception):
    """ 请求错误 """
    pass


class NotValueError(Exception):
    """ 没有内容错误 """
    pass


def _load_finish_article():
    """ 将当前目录下已遍历过文章 ID 文件中的数据加载到内存中 """
    result = []
    _dir = pathlib.PurePosixPath()
    file_path = os.path.abspath(_dir / 'finish_crawler_article.txt')
    if os.path.exists(file_path):
        with open(file_path, 'r', encoding='utf-8') as f:
            for article_id in f.readlines():
                article_id = article_id.strip('\n')
                if article_id:
                    result.append(article_id)
    return list(set(result))


def _save_finish_article_id_to_file():
    """ 将已经遍历完成的文章 ID 保存成文本，后面不用再遍历 """
    global FINISH_ARTICLES
    _dir = pathlib.PurePosixPath()
    file_path = os.path.abspath(_dir / 'finish_crawler_article.txt')
    with open(file_path, 'a+', encoding='utf-8') as f:
        for i in FINISH_ARTICLES:
            f.write(str(i) + '\n')


def check_filename(file_name):
    """
    校验文件名称的方法，在 windows 中文件名不能包含('\','/','*','?','<','>','|') 字符
    Args:
        file_name: 文件名称
    Returns:
        修复后的文件名称
    """
    return file_name.replace('\\', '') \
                    .replace('/', '') \
                    .replace('*', 'x') \
                    .replace('?', '') \
                    .replace('<', '《') \
                    .replace('>', '》') \
                    .replace('|', '_') \
                    .replace('\n', '') \
                    .replace('\b', '') \
                    .replace('\f', '') \
                    .replace('\t', '') \
                    .replace('\r', '')


class Cookie:

    def __init__(self, cookie_string=None):
        self._cookies = {}
        if cookie_string:
            self.load_string_cookie(cookie_string)

    @property
    def cookie_string(self):
        """
        将对象的各属性转换成字符串形式的 Cookies
        Returns:
            字符串形式的 cookies，方便给 HTTP 请求时使用
        """
        return ';'.join([f'{k}={v}' for k, v in self._cookies.items()])

    def set_cookie(self, key, value):
        self._cookies[key] = value

    @staticmethod
    def list_to_dict(lis):
        """
        列表转换成字典的方法
        Args:
            lis: 列表内容
        Returns:
            转换后的字典
        """
        result = {}
        for ind in lis:
            try:
                ind = ind.split('=')
                result[ind[0]] = ind[1]
            except IndexError:
                continue
        return result

    def load_string_cookie(self, cookie_str):
        """
        从字符串中加载 Cookie 的方法（将字符串转换成字典形式）, 相当于 cookie_string 方法的逆反操作
        Args:
            cookie_str: 字符串形式的 Cookies，一般是从抓包请求中复制过来
                eg: gksskpitn=cc662cd7-0a39-430a-a603-a1c61d6f784f; LF_ID=1587783958277-6056470-8195597;
        Returns:
        """
        cookie_list = cookie_str.split(';')
        res = self.list_to_dict(cookie_list)
        self._cookies = {**self._cookies, **res}

    def load_set_cookie(self, set_cookie):
        """
        从抓包返回的 Response Headers 中的 set-cookie 中提取 cookie 的方法
        Args:
            set_cookie: set-cookie 的值
        Returns:
        """
        set_cookie = re.sub(".xpires=.*?;", "", set_cookie)
        cookies_list = set_cookie.split(',')
        cookie_list = []
        for cookie in cookies_list:
            cookie_list.append(cookie.split(';')[0])
        res = self.list_to_dict(cookie_list)
        self._cookies = {**self._cookies, **res}

    def __repr__(self):
        return f'The cookies is : {self._cookies}'


class GeekDownload:
    """ 极客时间相关操作的类 """

    def __init__(self, exclude=None):
        self.cookie = Cookie(
            "LF_ID=1587783958277-6056470-8195597;_ga=GA1.2.880710184.1587783959;"
            "_gid=GA1.2.1020649675.1587783959; SERVERID=1fa1f330efedec1559b3abbc"
            "b6e30f50|1587784166|1587783958; _gat=1;Hm_lvt_022f847c4e3acd44d4a24"
            "81d9187f1e6=1587775851,1587775917,1587783916,1587784202; Hm_lpvt_02"
            "2f847c4e3acd44d4a2481d9187f1e6=1587784202;")
        self.common_headers = {
            "Accept":
            "application/json, text/plain, */*",
            "Accept-Encoding":
            "gzip, deflate, br",
            "Accept-Language":
            "zh-CN,zh;q=0.9,en;q=0.8",
            "Cache-Control":
            "no-cache",
            "Connection":
            "keep-alive",
            "Pragma":
            "no-cache",
            "Sec-Fetch-Dest":
            "empty",
            "Sec-Fetch-Mode":
            "cors",
            "Sec-Fetch-Site":
            "same-origin",
            "User-Agent":
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_13_6) "
            "AppleWebKit/537.36 (KHTML, like Gecko)Chrome/81.0.4044.122 Safari/537.36"
        }
        self.products = []
        self.exclude = exclude

    def _products(self, data):
        """
        取得文件夹下所有课程
        """
        file = rf'{data}'
        for root, dirs, files in os.walk(file):
            if root != file:
                break
            for dir in dirs:
                if dir.startswith('.'):
                    continue
                path = os.path.join(root, dir)
                new_pro = {'path': path}
                new_pro['articles'] = []
                new_pro['articles_paths'] = []
                self.products.append(new_pro)

    def _parser_product(self, pro):
        """
        解析课程列表, 取得文件列表
        Args:
            pro: 课程信息
        Returns: 文章列表
        """
        global ALL_ARTICLES
        articles_paths = []
        # log.info(pro)
        file = rf'{pro["path"]}'
        for root, dirs, files in os.walk(file):
            if root != file:
                break
            for dir in files:
                path = os.path.join(root, dir)
                articles_paths.append(path)
                ALL_ARTICLES.append(path)
        return articles_paths

    def _article(self, article):
        """
        修改文章资源
        """
        global FINISH_ARTICLES

        articleName = self.findName(article)
        modArticle = ''
        proDir = os.path.dirname(article)
        articleDir = f"{proDir}\{articleName}"
        if not os.path.exists(articleDir):
            os.makedirs(articleDir)

        try:
            fileobj = open(article, 'r', encoding='utf-8')
            cnt = 0
            while True:
                line = fileobj.readline()
                if line:
                    modLine = self.replaceLine(articleDir, articleName, line)
                    modArticle += modLine + "\n"
                else:
                    break
                # 修改了资源
                if modLine != line:
                    # 下载一次， 暂停两秒
                    time.sleep(1)
                    cnt += 1
                # if cnt > 1:
                #     break
        finally:
            if fileobj:
                fileobj.close()

        self.save_to_file(articleDir, 'index', modArticle, '.html')

        FINISH_ARTICLES.append(article)
        log.info(articleName)
        log.info('-' * 40)

    def replaceUrl(self, folder, articleName, resource):
        findSrc = re.search('src=".+?"', resource)
        if findSrc != None:
            span = findSrc.span()
            start = span[0] + 5
            end = span[1] - 1
            url = resource[start:end]
            isAudio = False
            fileName = ""
            if re.search("\S\.mp3", url):
                fileName = f"audio.mp3"
                path = f"{folder}\{fileName}"
                isAudio = True
            else:
                realPath = self.removeSearch(url)
                name = self.findName(realPath)
                ext = self.findExt(realPath)
                if ext == None:
                    ext = 'img'
                fileName = f"{name}.{ext}"
                path = f"{folder}\{fileName}"

            self.download_to_file(url, path)
            return resource[:start] + fileName + resource[end:]
        else:
            return resource

    def replaceResource(self, folder, articleName, line, findResource):
        dest = self.replaceUrl(folder, articleName, findResource.group())
        span = findResource.span()
        replace = line[:span[0]] + dest + line[span[1]:]
        return replace

    def replaceLine(self, folder, articleName, line: str):
        """
        返回修改过资源的行
        """
        findRes = re.search('<audio.*src=".+.mp3".+?></audio>', line)
        if findRes == None:
            findRes = re.search('<img.+src=".+?"', line)
        if findRes != None:
            line = self.replaceResource(folder, articleName, line, findRes)
        return line

    def testDownload(self):
        self.download_to_file(
            'https://thirdwx.qlogo.cn/mmopen/vi_32/Ewb31JsMN7J18ZoZMR2DBGvoxv06oLDuMGBibE4LfHVDHrwNb7JWPXia787OGKAkMUYrymLqmj2hWut1R4bzEWAQ/132',
            'D:/1.g')
        import sys
        sys.exit(1)

    @staticmethod
    def removeSearch(data):
        findQues = re.search('[^\?]*', data)
        if findQues != None:
            return data[:findQues.span()[1]]
        else:
            return data

    @staticmethod
    def findName(data):
        pathArr = data.split("\\")
        if len(pathArr) == 1:
            pathArr = data.split("/")
        lastSeg = pathArr[len(pathArr) - 1]
        # 找到最后一个 .字符位置
        nameFind = re.search('.*\.', lastSeg)
        if nameFind != None:
            return lastSeg[:nameFind.span()[1] - 1]
        else:
            return lastSeg

    @staticmethod
    def findExt(data):
        pathArr = data.split("\\")
        if len(pathArr) == 1:
            pathArr = data.split("/")
        lastSeg = pathArr[len(pathArr) - 1]
        nameFind = re.search('.*\.', lastSeg)
        if nameFind != None:
            return lastSeg[nameFind.span()[1]:]
        else:
            return None

    @staticmethod
    def download_to_file(url, path):
        """
        下载链接文件到指定路径
        """
        if os.path.exists(path):
            print('exist:' + url)
            return

        print('download:' + url)
        # 下载文件
        res = requests.get(url)

        print('saveto:' + path)
        # # 写入本地磁盘文件
        with open(path, 'wb') as f:
            f.write(res.content)

    @staticmethod
    def save_to_file(dir_name, filename, content, file_type=None):
        """
        将结果保存成文件的方法，保存在当前目录下
        Args:
            dir_name: 文件夹名称，如果不存在该文件夹则会创建文件夹
            filename: 文件名称，直接新建
            content: 需要保存的文本内容
            file_type: 文档类型（需要保存什么类型的文档），默认保存为 Markdown 文档
        Returns:
        """
        if not file_type:
            file_type = '.md'
        file_path = f"{dir_name}\{filename}{file_type}"

        # 将所有数据写入文件中
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)


def run(exclude=None):
    """ 整体流程的请求方法 """
    global FINISH_ARTICLES
    global ALL_ARTICLES

    geek = GeekDownload(exclude=exclude)
    geek._products('./courses')
    number = 0

    for pro in geek.products:
        pro['articles_paths'] = geek._parser_product(pro)
        article_paths = pro['articles_paths']
        cnt = 0
        for article in article_paths:
            if set(ALL_ARTICLES) == set(FINISH_ARTICLES):
                import sys
                log.info("正常下载完成啦，不用再继续跑脚本了。")
                sys.exit(1)
            if str(article) in FINISH_ARTICLES:
                continue
            geek._article(article)
            # import sys
            # sys.exit(1)
        #time.sleep(5)  # 做一个延时请求，避免过快请求接口被限制访问
        number += 1
        # 判断是否连续抓取过 37次，如果是则暂停 10s
        if number == 37:
            log.info("抓取达到37次了，先暂停 10s 再继续。")
            time.sleep(10)
            number = 0  # 重新计数
    log.info("正常抓取完成。")


if __name__ == "__main__":
    # 忽略文章
    exclude = []

    try:
        FINISH_ARTICLES = _load_finish_article()
        run(exclude=exclude)
    except Exception:
        import traceback
        log.error(f"请求过程中出错了，出错信息为：{traceback.format_exc()}")
    finally:
        _save_finish_article_id_to_file()
