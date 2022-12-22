import os
import sys
import scrapy
import json
import re
import time
import redis

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from settings import REDIS_HOST, REDIS_PORT, VIDEOS_PER_BATCH, DOWNLOAD_LIMIT


# Batch and Video number calculation.
def batch_decoder(x, step):
    if x % step == 0:
        return str(x//step), str(step)
    else:
        return str(x//step + 1), str(x % step)


# Haokan website Crawler.
class Haokan2Spider(scrapy.Spider):
    # Data for Videos and authors.
    name = "haokan2"
    database = redis.Redis(host=REDIS_HOST, port=REDIS_PORT)

    def start_requests(self):
        # Root website.
        start_url = 'https://haokan.baidu.com/author/'

        # Create a root path for videos.
        try:
            os.mkdir('videos')
        except OSError:
            pass

        # Process all the authors.
        with open('UID.txt', 'r') as f:
            all_ids = f.readlines()
            for aut_id in all_ids:
                self.database.rpush('Author_queue', aut_id.rstrip('\n'))

        # Then empty the file.
        with open('UID.txt', 'w') as f:
            f.write('')

        # Author processing mode.
        while self.database.llen('Author_queue') != 0:
            aut_id = self.database.lpop('Author_queue').decode()
            if self.database.hgetall('AUTHOR_INFO_CF:' + aut_id) != {}:
                print('===== 该作者已经爬取过了 =====')
                continue
            aut_url = start_url + aut_id
            yield scrapy.Request(url=aut_url, callback=self.parse)
            return

        # Start to download the processed videos.
        limit = DOWNLOAD_LIMIT
        while True:
            # The amount of videos downloaded will be limited for each run.
            if limit <= 0:
                break
            video_url = self.database.lpop('Video_queue')
            # Check if video queue is empty.
            if video_url is not None:
                if self.database.hget('VIDEO_INFO_CF:' + video_url.decode(), 'Done') != b'YES':
                    yield scrapy.Request(url=video_url.decode(), callback=self.parse_video)
            else:
                print('===== 视频队列已经空了 =====')
                break
            limit = limit - 1

    def parse(self, response):
        # Extract author informations.
        info = response.css('title::text').getall()
        path = info[0]
        author = path[:path.find('-')]
        act = response.url
        author_id = act.rsplit("/")[-1]
        author_info = response.css("div.uinfo-head-info p.uinfo-head-list-vlog::text").get()
        if author_info is None:
            author_info = response.css("div.uinfo-head-info p.uinfo-head-list-desc::text").get()
        else:
            author_info += response.css("div.uinfo-head-info p.uinfo-head-list-desc::text").get()
        if author_info is None:
            author_info = ""

        # Get the local date information and send the author information.
        local_date = time.strftime('%Y{y}%m{m}%d{d}').format(y='年', m='月', d='日')
        yield {
            "Name": author,
            "ID": author_id,
            "Info": author_info,
            "Crawled_date": local_date
        }

        # Extract video informations.
        video_srcs = re.findall('\"content\":(.*?)},{\"tplName\":', response.body.decode())
        for video_sr in video_srcs:
            # Count the number of videos | FIXME: Not reliable.
            self.database.hset('AUTHOR_INFO_CF:' + author_id, 'Num_videos', str(int(self.database.hget('AUTHOR_INFO_CF:' + author_id, 'Num_videos').decode())+1))
            i = json.loads(video_sr)
            title = i["title"]
            video_time = i["duration"]
            video_url = "https://haokan.baidu.com/v?vid=" + i["vid"]

            # Skip the videos already downloaded or already in the queue.
            if self.database.hgetall('VIDEO_INFO_CF:' + video_url) != {}:
                continue

            publish_time = i["publish_time"]
            item = {
                'URL': video_url,
                'UID': author_id,
                'Title': title,
                'Video Time': video_time,
                'Publish Time': publish_time,
                'Crawled Date': local_date
            }
            yield item

        # Crawl next webpage.
        ctime = re.findall('\"ctime\":(.*?),\"results\":', response.body.decode())
        print(ctime)
        next_url = "https://haokan.baidu.com/web/author/listall?app_id=%s&ctime=%s&rn=10&_api=1" % (str(author_id), ctime)
        yield scrapy.Request(url=next_url, callback=self.parse_next)

    def parse_next(self, response):
        data = response.body.decode()
        # Dealing with banned IP situation.
        errno = re.findall('\"errno\":(.*?),', response.body.decode())[0]
        if errno == '101007':
            print('网络异常！该IP已被封禁！~请稍后再爬取')
            return

        # Extract video information.
        author_id = re.findall('app_id=(.*?)&', response.url)[0]
        video_srcs = re.findall('\"content\":(.*?)},{\"tplName\":', data)
        for video_sr in video_srcs:
            # Count the number of videos | FIXME: Not reliable.
            self.database.hset('AUTHOR_INFO_CF:' + author_id, 'Num_videos', str(int(self.database.hget('AUTHOR_INFO_CF:' + author_id, 'Num_videos').decode())+1))
            i = json.loads(video_sr)
            title = i["title"]
            video_time = i["duration"]
            video_url = "https://haokan.baidu.com/v?vid=" + i["vid"]

            # Skip the videos already downloaded or already in the queue.
            if self.database.hgetall('VIDEO_INFO_CF:' + video_url) != {}:
                continue

            publish_time = i["publish_time"]
            local_date = time.strftime('%Y{y}%m{m}%d{d}').format(y='年', m='月', d='日')
            item = {
                'URL': video_url,
                'UID': author_id,
                'Title': title,
                'Video Time': video_time,
                'Publish Time': publish_time,
                'Crawled Date': local_date
            }
            yield item

        # Crawl next webpage.
        ctime = re.findall('\"ctime\":(.*?),\"results\":', data)[0]
        next_url = "https://haokan.baidu.com/web/author/listall?app_id=%s&ctime=%s&rn=10&_api=1" % (str(author_id), ctime)
        yield scrapy.Request(url=next_url, callback=self.parse_next)

    def parse_video(self, response):
        # Extract video downloading information.
        s = response.css('script').re('window.__PRELOADED_STATE__ = (.+);')[0]
        start = '\"playurl\":\"'
        s = s[s.find(start)+len(start):]
        end = '.mp4'
        s = s[:s.find(end)+len(end)]
        s = s.replace('\\', '')
        title = response.css("h1.videoinfo-title::text").get()

        # Dealing with special case when some videos need to be redownloaded.
        if self.database.hget('VIDEO_INFO_CF:' + response.url, 'Batch') is not None:
            batch = int(self.database.hget('VIDEO_INFO_CF:' + response.url, 'Batch').decode())
        else:
            batch = self.database.incr('VIDEO_COUNT')

        # Get the download directory information.
        b_num, v_num = batch_decoder(batch, VIDEOS_PER_BATCH)
        try:
            os.makedirs('videos/batch{batch_num}/record/data'.format(batch_num=b_num.zfill(4)))
        except OSError:
            pass
        vid_dir = 'videos/batch{batch_num}/record/data/batch{batch_num}_11{video_num}.mp4'.format(batch_num=b_num.zfill(4), video_num=v_num.zfill(4))
        self.database.hset('VIDEO_INFO_CF:' + response.url, 'Batch', batch)
        self.database.hset('VIDEO_INFO_CF:' + response.url, 'Directory', vid_dir)

        # Download the video.
        yield {
            'Directory': vid_dir,
            'root_URL': response.url,
            'download_URL': s
        }
