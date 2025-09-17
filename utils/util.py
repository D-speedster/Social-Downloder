import math
import datetime
import pytube
import shutil
import requests
import random


def convert_size(a,size_bytes):
   if size_bytes == 0:
       return "0B"
   size_name = ("B", "KB", "MB", "GB", "TB", "PB", "EB", "ZB", "YB")
   i = int(math.floor(math.log(size_bytes, 1024)))
   p = math.pow(1024, i)
   s = round(size_bytes / p, 2)
   if a == 1:
       if i >= 3 and s > 1:
            return False
       else:
           return True
   if a == 2:
        return "%s %s" % (s, size_name[i])


def download_image(url,itag):
    r = requests.get(url, stream=True)
    if r.status_code == 200:
        url = url.split("/")[-1]
        r.raw.decode_content = True
        with open(f"filename{itag}.jpg", 'wb') as f:
            shutil.copyfileobj(r.raw, f)


def thubnail_maker(res,step_link,step_itag):

    if res == "720p":
        high_res = step_link.thumbnail_url.replace('sddefault.jpg', 'maxresdefault.jpg')
        download_image(high_res, step_itag)

    elif res == "480p":
        mid_res = step_link.thumbnail_url.replace('sddefault.jpg', 'mqdefault.jpg')
        download_image(mid_res, step_itag)

    elif res == "360p":
        mid_res = step_link.thumbnail_url.replace('sddefault.jpg', 'maxresdefault.jpg')
        download_image(mid_res, step_itag)

    else:
        low_res = step_link.thumbnail_url.replace('sddefault.jpg', 'sddefault.jpg')
        download_image(low_res, step_itag)



