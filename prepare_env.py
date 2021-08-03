#!/usr/bin/env python3

import base64
import hashlib
import os
from urllib import request

DATA_FILE_NAME = "chain_configs.dat"
DATA_URL = "https://onekey-asset.com/app_configs/chain_configs.dat"
LOCAL_DATA_FILE = f"{os.path.dirname(__file__)}/electrum_gui/common/conf/data/{DATA_FILE_NAME}"


def download_data():
    if os.path.exists(LOCAL_DATA_FILE):
        resp = request.urlopen(request.Request(DATA_URL, method="HEAD"))
        md5sum = base64.b64decode(resp.headers.get("Content-Md5")).hex()
        with open(LOCAL_DATA_FILE, "rb") as f:
            tmp_data = f.read()
        if hashlib.md5(tmp_data).hexdigest() == md5sum:
            return

    with open(LOCAL_DATA_FILE, "wb") as f, request.urlopen(DATA_URL) as req:
        f.write(req.read())


if __name__ == '__main__':
    download_data()
