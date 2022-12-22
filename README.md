# 多模ASR数据爬取

多模ASR数据爬取，依赖 scrapy 库进行数据爬取。对于数据爬取过程中，待使用和解析出的连接。
利用 pika 进行保存和管理，支持分布式多进程爬取及多台电脑数据库共享。

## ===== 准备工作 =====

### 准备环境

``` BASH
pip install -r ${avks_root}/data_process/mmasr_spider/requirements.txt
```

### 设置参数

在${avks_root}/data_process/mmasr_spider/formal_one/settings.py里：

``` BASH
# Redis Connection Host and Port.
REDIS_HOST = '10.10.112.85'
REDIS_PORT = 18448

# Number of tries for case when downloading fails.
DOWNLOAD_TRIES = 3

# Videos downloaded for each recurse.
DOWNLOAD_LIMIT = 10

# Number of videos per batch.
VIDEOS_PER_BATCH = 2000

# 代理IP.
PROXY_SERVER = "http://http-dyn.abuyun.com:9020"
PROXY_USER = "HOT2WA0CC19734ZD"
PROXY_PASS = "00503A9B2B26B66D"

# 作者信息过期时间（秒），-1为不过期
EXPIRY_DATE = 7776000

# 意外情况处理：
# 延迟时间
EXCEPTION_DELAY = 30

# =============================================================
#      WARNING: Do NOT touch the following Variables!!!
# =============================================================
CURRENT_AUTHOR = ''
```

REDIS_HOST和REDIS_PORT请基于PIKA数据库的IP+端口填写；
DOWNLOAD_TRIES为视频下载失败后重新尝试下载的最高次数；
DOWNLOAD_LIMIT为每一次迭代运行下载的视频数量；
VIDEO_PER_BATCH为一个batch下存储的视频数量（为了统一请不要改动）；
PROXY_SERVER, PROXY_USER和PROXY_PASS为代理IP信息，在过期前请不要改动；
EXPIRY_DATE为作者信息在数据库中的保质期（为了统一请不要改动）；
EXCEPTION_DELAY为意外（进程意外关闭）处理的延迟判断，尽量不要小于30。

### 准备作者UID

在${avks_root}/data_process/mmasr_spider/formal_one里，找到并打开UID.txt；
在UID.txt文档里，输入作者UID，一行一个，格式如下：

``` BASH
1668459242176996
1234567890123456
...（以此类推）
```

当前版本支持：
容错（作者UID不存在的情况）
作者去重（作者UID写了2遍）
空UID.txt运行（UID.txt即使是空的，只要数据库队列里存在还未爬取的作者UID，编译依然可以正常运行）

## ===== 启动爬虫 =====

### 后台运行爬虫服务

``` BASH
cd ${avks_root}/data_process/mmasr_spider/
screen
make
```

编译后会生成新路径videos/，下载的视频会存入该路径,等待全部爬取完成即可，关闭终端不会kill进程
注意：基于分布式爬虫特点，视频号（batchxxxx_11xxxx）出现跳跃属正常现象

当前版本支持：
分布式爬取（一个数据库->多台电脑）
视频整合（共用一个数据库的所有爬虫爬取的视频可以进行整合，所有视频整合后视频号将不会出现断层）
多进程爬取（可以开多个终端/screen同时make）
基于作者下载（下载后的视频会很清楚地将不同作者的视频分开，前提是每个电脑只开一个进程）
去重（在一个数据库下，已下载的视频不会重复下载）
自动爬取下一个作者/自动下载视频（只要还有作者待处理，或还有视频待下载，该爬虫程序将持续运行，直到全部爬取完成)
爬取强行中断（不会影响其他进程，且有检查程序，但速度较慢）

### 检查正在运行中的爬虫程序

``` BASH
screen -ls
```

会生成类似下面的信息：

``` BASH
There are screens on:
        32581.pts-23.gpu-dev035 (Attached)
        32266.pts-19.gpu-dev035 (Attached)
        ...
```

进入一个爬虫进程（以上面第一个为例）：

``` BASH
screen -r 32581
```

即可进入爬虫运行界面。

### 强行终止爬虫程序（不推荐）

该爬虫在没有人工干预的情况下将不会被强行结束进程，但如果一定要终止，
以之前的进程为例：

``` BASH
kill -9 32581
screen -wipe
```

若如此做，请运行：

``` BASH
screen
make exception
```

需要等待较长时间才能完全恢复数据。

## ===== 备注 =====

### scrapy.cfg

``scrapy.cfg`` 默认将自动生成。其中，保存了运行 scrapy 爬虫时，将会使用的一些配置项

```
[settings]
default = formal_one.settings

[deploy]
#url = http://localhost:6800/
project = formal_one
```

其中， ``default`` 会指定默认配置的位置，``project`` 会指定整个爬虫的项目目录。

### bash

运行完成后出现：

``` BASH
rm STATUS.txt
rm: cannot remove ‘STATUS.txt’: No such file or directory
make: *** [run] Error 1
```

属正常现象
