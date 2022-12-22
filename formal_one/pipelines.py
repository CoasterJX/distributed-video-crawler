# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: https://docs.scrapy.org/en/latest/topics/item-pipeline.html


# useful for handling different item types with a single interface
import redis
import random
import time
import urllib.request
import progressbar
import settings
from settings import REDIS_HOST, REDIS_PORT, DOWNLOAD_TRIES


pbar = None


# Classifier for video information
def classify_by_target(desc):
    target_words = ['影视', '音乐', 'vlog', '游戏', '搞笑', '综艺', '娱乐', '动漫', '生活', '广场舞', '美食', '宠物', '三农', '军事', '社会', '体育', '科技', '时尚', '汽车', '亲子', '文化', '旅游']
    tags = set()
    for word in target_words:
        if word in desc.lower():
            tags.add(word)
    return tags


def show_progress(block_num, block_size, total_size):
    global pbar
    if pbar is None:
        pbar = progressbar.ProgressBar(maxval=total_size)
        pbar.start()

    downloaded = block_num * block_size
    if downloaded < total_size:
        pbar.update(downloaded)
    else:
        pbar.finish()
        pbar = None


class FormalOnePipeline:

    database = redis.Redis(host=REDIS_HOST, port=REDIS_PORT)

    def process_item(self, item, spider):
        # Video downloading.
        if len(item) == 3:
            video_dir = item['Directory']
            url = item['download_URL']
            root = item['root_URL']
            # Download the video.
            tries = DOWNLOAD_TRIES
            while tries > 0:
                try:
                    urllib.request.urlretrieve(url, video_dir, show_progress)
                except:
                    print("Retry Downloading...")
                    tries = tries - 1
                    continue
                else:
                    # Mark the video as downloaded.
                    self.database.hset('VIDEO_INFO_CF:' + root, 'Done', 'YES')
                    break

        # Author processing.
        elif len(item) == 4:
            # Extract author information.
            a_name = item['Name']
            a_id = item['ID']
            a_info = item['Info']
            a_crawled_date = item['Crawled_date']
            # Extract author tags and push them into database.
            tags = classify_by_target(a_name + a_info)
            author_hash = {
                'Tags': str(tags),
                'Name': a_name,
                'Crawled_date': a_crawled_date,
                'Num_videos': '0',
                'Done': 'NO'
            }
            self.database.hmset('AUTHOR_INFO_CF:' + a_id, author_hash)
            # And set the author variable.
            settings.CURRENT_AUTHOR = a_id

        # Video information wrap-up.
        else:
            # Extract video information.
            vid_info = {
                'UID': item['UID'],
                'Title': item['Title'],
                'Duration': item['Video Time'],
                'Publish_time': item['Publish Time'],
                'Accessed_time': item['Crawled Date'],
                'Done': 'NO'
            }

            self.database.rpush('Video_queue', item['URL'])
            self.database.hmset('VIDEO_INFO_CF:' + item['URL'], vid_info)
            self.database.sadd('AUTHOR_VIDEO_CF:' + item['UID'], item['URL'])

        return item
