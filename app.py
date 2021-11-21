from typing import Dict
from async_asmr import get_movie_id
import tqdm, tqdm.asyncio
import numpy as np
import json
import subprocess, os
import asyncio
import argparse

#for i in tqdm.tqdm(range(int(1e7))):
#    np.pi*np.pi


class File_IO():
    @classmethod
    def load_json(self) -> list[dict]:
        with open('./config/lists.json') as f:
            jfile = json.load(f)
        if jfile is None:
            jfile = []
        return jfile

    @classmethod
    def get_downloaded_movie_id(self, vtuber):
        path = vtuber + '/movie.txt'
        with open(path) as f:
            #ids = f.readline().replace("\n", "")
            ids = f.read().split('\n')
        return [id for id in ids if id != '']

    @classmethod
    def write_id_file(self, vtuber, complate_id):
        path = vtuber + '/movie.txt'
        with open(path, mode='a') as f:
            f.write(complate_id + '\n')

    @classmethod
    def json_dump(self, path, data):
        with open(path, 'w') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

class SettingConfig():
    @classmethod
    def exists_config(self) -> bool:
        return os.path.isfile("./config/lists.json")
    
    def create_config(self):
        if not self.exists_config():
            subprocess.run(['mkdir', '-p', './config']) 
            touch = subprocess.run(['touch', './config/lists.json'])
            return touch

    def write_config(self, data: dict = None):
        if not data:
            return

        if not ('name' in data and 'url' in data):
            return
        
        if not all([data['name'], data['url']]):
            return

        read = File_IO.load_json()
        read.append(data)
        File_IO.json_dump('./config/lists.json', read)

class Asmr():
    def get_asmr(self, tuber: dict) -> dict:
        target_ids = self.fetch_download_id(tuber['url'], tuber['name'])
        if len(target_ids) == 0:
            return []
        return {'name': tuber['name'], 'url': target_ids}

    def fetch_download_id(self, url: str, name: str) -> list:
        target_movie_id = self.get_movie_id(url)
        downloaded_movie_id = File_IO.get_downloaded_movie_id(name)
        ids = set(target_movie_id) ^ set(downloaded_movie_id)
        return list(ids)

    def get_movie_id(self, url: str) -> list:
        cmd = "youtube-dl -i --get-id " + url + " --cookies ./config/Cookies.txt"
        result = subprocess.run(cmd.split(), stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        id_list = result.stdout
        ids = id_list.decode().split()
        return ids

    def do_download(self, name: str, url: str) -> bool:
        cmd = "youtube-dl -o ./" + name + \
            "/%(title)s-%(id)s.%(ext)s -f 251 -ci " + \
            url + " --cookies ./config/Cookies.txt"
        result = subprocess.run(cmd.split(), stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if result.returncode == 0:
            File_IO.write_id_file(name, url)
            return '{name} : {url}\n成功しました。'
        return '{name} : {url}\n失敗しました。'

    async def handler(self, loop, f_json):
        async def exec(i):
            # 並列制限を2に設定
            async with asyncio.Semaphore(2):
                return await loop.run_in_executor(None, self.get_asmr, i)
        tasks = [exec(i) for i in f_json]
        #return await asyncio.gather(*tasks)
        result = []
        for t in tqdm.tqdm(asyncio.as_completed(tasks), desc="動画の検索", total=len(f_json)):
            result.append(await t)
        return result

    async def do_handler(self, loop, f_json):
        async def exec(url):
            # 並列制限を2に設定
            async with asyncio.Semaphore(2):
                return await loop.run_in_executor(None, self.do_download, f_json['name'], url)
        tasks = [exec(url) for url in f_json['url']]
        for t in tqdm.tqdm(asyncio.as_completed(tasks), desc="{}の動画をダウンロード".format(f_json['name']), total=len(f_json['url']), leave=False):
            print(await t)

    @classmethod
    def main(self):
        loop = asyncio.new_event_loop()
        json = File_IO.load_json()
        result = loop.run_until_complete(self.handler(loop, json))
        loop.close()

        loop = asyncio.new_event_loop()
        for vtuber in tqdm.tqdm(result, desc="ダウンロード"):
            loop.run_until_complete(self.do_handler(loop, vtuber))
        loop.close()
        

    def single_test(self):
        json = File_IO.load_json()
        result = []
        for j in json:
            result.append(self.get_asmr(j))
        for tuber in result:
            for url in tuber['url']:
                self.do_download(tuber['name'], url)
        return result

parser = argparse.ArgumentParser(description='ASMRダウンロード')
parser.add_argument('-n', '--name', help='YouTuberの名前')
parser.add_argument('-l', '--link', help='再生リスト、チャンネルのURL')
args = parser.parse_args()

if __name__ == '__main__':
    if not SettingConfig.exists_config():
        print("設定ファイルが存在しません。作成しますか？ Y/N")
        select = input()
        if select in ['Y', 'y']:
            sg = SettingConfig()
            sg.create_config()
            print("設定ファイルを作成しました。")
        exit

    if args.name and args.link:
        print("―――――追記モード―――――")
        print('{name}\n{link}\nを追記しますか？ Y/N'.format(name=args.name, link=args.link))
        select = input()
        if select in ['Y', 'y']:
            sg = SettingConfig()
            sg.write_config({'name': args.name, 'url': args.link})
        exit

    Asmr.main()
    #asmr.single_test()
