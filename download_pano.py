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

        import sys
        sys.exit(1)


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

def download_face(face, level, size, url, path):
    """
    下载某一面的全景图
    """
    for i in range(1,size+1):
        for j in range(1,size+1):
            # 拼接下载链接
            download_url = f'{url}/{face}/{level}/{i}/{level}_{face}_{i}_{j}.jpg'
            # 拼接保存路径
            save_path = f'{path}/{level}_{face}_{i}_{j}.jpg'
            # 下载文件
            download_to_file(download_url, save_path)
    
def download_level(level, size, url, path):
    """
    下载某一层级的全景图
    """
    download_face('l', level, size, url, path)
    download_face('r', level, size, url, path)
    download_face('u', level, size, url, path)
    download_face('d', level, size, url, path)
    download_face('f', level, size, url, path)
    download_face('b', level, size, url, path)

def download_pano(url, path):
    """
    下载全景图
    """
    download_level('l1', 3, url, path)
    download_level('l2', 5, url, path)
    download_level('l3', 9, url, path)

if __name__ == "__main__":
    # 忽略文章
    exclude = ['WebAssembly入门课', '10x程序员工作法', 'AB测试从0到1']

    try:
        download_pano('https://ssl-panoimg134.720static.com/resource/prod/3da31c39e5d/550jks4ksf0/60680866/imgs',
                         'E:/pano/panorama2')
        download_pano('https://ssl-panoimg131.720static.com/resource/prod/3da31c39e5d/550jks4ksf0/60680867/imgs',
                        'E:/pano/panorama3')
    except Exception:
        import traceback
        log.error(f"请求过程中出错了，出错信息为：{traceback.format_exc()}")
    finally:
        pass
