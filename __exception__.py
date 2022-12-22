import os
import sys
import redis
import time
from waiting import wait

sys.path.insert(0, './formal_one')
from settings import *


def not_a_death_progress(uid_info, r, num_vid):
    return num_vid != r.hget(uid_info, 'Num_videos') or r.hget(uid_info, 'Done') == b'YES'


def check_author(database):
    print('正在恢复作者信息，请稍后...')
    for uid_info in database.keys(pattern='AUTHOR_INFO_CF:*'):
        print('检查 ' + uid_info.decode().lstrip('AUTHOR_INFO_CF:'))
        if database.hget(uid_info, 'Done') != b'YES':
            try:
                num_vid = database.hget(uid_info, 'Num_videos')
                wait(lambda: not_a_death_progress(uid_info, database, num_vid), timeout_seconds=EXCEPTION_DELAY)
            except:
                print(uid_info.decode().lstrip('AUTHOR_INFO_CF:') + ': 已重新放入队列')
                database.delete(uid_info)
                database.rpush('Author_queue', uid_info.decode().lstrip('AUTHOR_INFO_CF:'))
                return
        print(uid_info.decode().lstrip('AUTHOR_INFO_CF:') + ': 正常')


def check_videos(database):
    print('正在恢复视频下载，请稍后...')
    for vid_info in database.keys(pattern='VIDEO_INFO_CF:*'):
        print('检查 ' + vid_info.decode().lstrip('VIDEO_INFO_CF:'))
        if database.hget(vid_info, 'Done') != b'YES' and database.hget(vid_info, 'Batch') is not None:
            if os.path.exists(database.hget(vid_info, 'Directory').decode()):
                os.remove(database.hget(vid_info, 'Directory').decode())
                database.rpush('Video_queue', vid_info.decode().lstrip('VIDEO_INFO_CF:'))


if __name__ == '__main__':
    database = redis.Redis(host=REDIS_HOST, port=REDIS_PORT)
    check_author(database)
    check_videos(database)
