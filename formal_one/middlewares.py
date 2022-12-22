# Define here the models for your spider middleware
#
# See documentation in:
# https://docs.scrapy.org/en/latest/topics/spider-middleware.html

# import random
# import base64
# from formal_one.settings import PROXIES

from scrapy import signals

# useful for handling different item types with a single interface
import settings
from settings import PROXY_SERVER, PROXY_USER, PROXY_PASS, REDIS_HOST, REDIS_PORT, EXPIRY_DATE
import base64
import redis
import os

proxyServer = PROXY_SERVER
proxyAuth = "Basic " + base64.urlsafe_b64encode(bytes((PROXY_USER + ":" + PROXY_PASS), "ascii")).decode("utf8")


# class CustomProxyMiddleware(object):
#     def process_request(self, request, spider):
#         request.meta["proxy"] = proxyServer
#         request.headers["Proxy-Authorization"] = proxyAuth


class FormalOneSpiderMiddleware:
    # Not all methods need to be defined. If a method is not defined,
    # scrapy acts as if the spider middleware does not modify the
    # passed objects.
    database = redis.Redis(host=REDIS_HOST, port=REDIS_PORT)

    @classmethod
    def from_crawler(cls, crawler):
        # This method is used by Scrapy to create your spiders.
        s = cls()
        crawler.signals.connect(s.spider_opened, signal=signals.spider_opened)
        crawler.signals.connect(s.spider_closed, signal=signals.spider_closed)
        return s

    def process_spider_input(self, response, spider):
        # Called for each response that goes through the spider
        # middleware and into the spider.

        # Should return None or raise an exception.
        return None

    def process_spider_output(self, response, result, spider):
        # Called with the results returned from the Spider, after
        # it has processed the response.

        # Must return an iterable of Request, or item objects.
        for i in result:
            yield i

    def process_spider_exception(self, response, exception, spider):
        # Called when a spider or process_spider_input() method
        # (from other spider middleware) raises an exception.

        # Should return either None or an iterable of Request or item objects.
        pass

    def process_start_requests(self, start_requests, spider):
        # Called with the start requests of the spider, and works
        # similarly to the process_spider_output() method, except
        # that it doesn’t have a response associated.

        # Must return only requests (not items).
        for r in start_requests:
            yield r

    def spider_opened(self, spider):
        spider.logger.info('Spider opened: %s' % spider.name)

    def spider_closed(self, spider):
        f = open('STATUS.txt', 'w')
        f.close()
        # Set the processed author to Done.
        uid = settings.CURRENT_AUTHOR
        if uid != '':
            self.database.hset('AUTHOR_INFO_CF:' + uid, 'Done', 'YES')
            num_videos = self.database.scard('AUTHOR_VIDEO_CF:' + uid)
            self.database.hset('AUTHOR_INFO_CF:' + uid, 'Num_videos', str(num_videos))
            if EXPIRY_DATE != -1:
                self.database.expire('AUTHOR_INFO_CF:' + uid, time=EXPIRY_DATE)
        # Done crawling if all queues are empty.
        if self.database.llen('Author_queue') == 0 and self.database.llen('Video_queue') == 0:
            os.remove('STATUS.txt')


class FormalOneDownloaderMiddleware:
    # Not all methods need to be defined. If a method is not defined,
    # scrapy acts as if the downloader middleware does not modify the
    # passed objects.

    @classmethod
    def from_crawler(cls, crawler):
        # This method is used by Scrapy to create your spiders.
        s = cls()
        crawler.signals.connect(s.spider_opened, signal=signals.spider_opened)
        return s

    def process_request(self, request, spider):
        # Called for each request that goes through the downloader
        # middleware.

        # Must either:
        # - return None: continue processing this request
        # - or return a Response object
        # - or return a Request object
        # - or raise IgnoreRequest: process_exception() methods of
        #   installed downloader middleware will be called
        return None

    def process_response(self, request, response, spider):
        # Called with the response returned from the downloader.

        # Must either;
        # - return a Response object
        # - return a Request object
        # - or raise IgnoreRequest
        return response

    def process_exception(self, request, exception, spider):
        # Called when a download handler or a process_request()
        # (from other downloader middleware) raises an exception.

        # Must either:
        # - return None: continue processing this exception
        # - return a Response object: stops process_exception() chain
        # - return a Request object: stops process_exception() chain
        pass

    def spider_opened(self, spider):
        spider.logger.info('Spider opened: %s' % spider.name)
