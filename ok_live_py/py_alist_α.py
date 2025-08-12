#coding=utf-8
#!/usr/bin/python
import os
import re
import json
import time
import sqlite3
import requests
from sys import path
from threading import Thread
from os.path import splitext
from urllib.parse import urlparse, quote, unquote

path.append('..')
from base.spider import Spider

class Spider(Spider):
	def getName(self):
		return "ALIST网盘"

	def init(self, extend):
		try:
			r = requests.get(extend, headers=self.header, timeout=5)
			self.alistInfos = r.json()
		except:
			self.alistInfos = {}

	def isVideoFormat(self, url):
		pass

	def manualVideoCheck(self):
		pass

	def homeContent(self, filter):
		result = {'class': [{"type_name": "电影", "type_id": "电影"}, {"type_name": "剧集", "type_id": "剧集"}, {"type_name": "其他", "type_id": "其他"}]}
		return result

	def homeVideoContent(self):
		return {}

	def categoryContent(self, tid, page, filter, ext):
		if tid == '电影':
			videos = []
			total = 0
			for result, total in self.handleSqlite(params={'table': 'alist', "where": {"type": '电影'}}, page=page, act='get'):
				for driveInfos in self.alistInfos['drives']:
					params = driveInfos.copy()
					if result['location'].startswith(params['server'].strip('/')):
						params['server'] = result['location']
						params['id'] = result['id']
						scrapeInfos = json.loads(unquote(result['dbInfos']))
						pic = re.sub(r'photo/(.*?)/', 'photo/l/', scrapeInfos['pic']['large']) + '@User-Agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36@Referer=https://www.douban.com/'
						remark = scrapeInfos['card_subtitle'].replace(' / ', '/').strip()
						videos.append({
							"vod_id": json.dumps(params, ensure_ascii=False),
							"vod_name": scrapeInfos['title'],
							"vod_pic": pic,
							"vod_remarks": remark
						})
						break

			pageCount = page + 1 if page * 20 < total else page
			limit = len(videos)
			total = len(videos)
		elif tid == '剧集':
			videos = []
			total = 0
			for result, total in self.handleSqlite(params={'table': 'alist', "where": {"type": '电视剧'}}, page=page, act='get'):
				for driveInfos in self.alistInfos['drives']:
					params = driveInfos.copy()
					if result['location'].startswith(params['server'].strip('/')):
						params['server'] = result['location']
						params['id'] = result['id']
						scrapeInfos = json.loads(unquote(result['dbInfos']))
						pic = re.sub(r'photo/(.*?)/', 'photo/l/', scrapeInfos['pic']['large']) + '@User-Agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36@Referer=https://www.douban.com/'
						remark = scrapeInfos['card_subtitle'].replace(' / ', '/').strip()
						videos.append({
							"vod_id": json.dumps(params, ensure_ascii=False),
							"vod_name": scrapeInfos['title'],
							"vod_pic": pic,
							"vod_remarks": remark
						})
						break

			pageCount = page + 1 if page * 20 < total else page
			limit = len(videos)
			total = len(videos)
		elif tid == '其他':
			videos = []
			for driver in self.alistInfos['drives']:
				if 'hidden' in driver and driver['hidden']:
					continue
				videos.append({
					"vod_id": json.dumps(driver, ensure_ascii=False),
					"vod_name": driver['name'],
					"vod_pic": "https://serv.leuse.top/files/img/alist.png",
					"vod_tag": "folder",
					"style": {
						"type": "rect",
						"ratio": 1
					},
					"vod_remarks": "文件夹"

				})
			pageCount = 1
			limit = len(videos)
			total = len(videos)
		else:
			password = ''
			params = json.loads(tid)
			url = params['server']
			if url.count('/') == 2:
				baseUrl = f"{url}/"
			else:
				baseUrl = re.search(r"(http.*://.*?/)", url).group(1)
			if 'login' in params:
				login = params['login']
			else:
				login = None
			header = self.header.copy()
			header["Referer"] = baseUrl
			token = self.getCache(f'alistToken_{baseUrl}')
			if token:
				token = token['token']
			else:
				r = requests.post(baseUrl + 'api/auth/login', json=login, headers=header)
				data = r.json()
				if data['code'] == 200:
					token = data['data']['token']
					self.setCache(f'alistToken_{baseUrl}', {'token': token, 'expires_at': int(time.time())+86400})
			header['Authorization'] = token
			path = urlparse(url).path if urlparse(url).path != '' else '/'
			try:
				name = re.search(r'.*/(.*?)/', path).group(1)
			except:
				name = params['name']
			if 'params' in params:
				for param in params['params']:
					if path.startswith(param['path']) and 'pass' in param:
						password = param['pass']
						break
			r = requests.post(baseUrl + 'api/fs/list', json={"path": path, 'password': password}, headers=header)
			data = r.json()
			vodList = data['data']['content']
			videos = []
			subtList = []
			videoList = []
			paramsList = []
			scrapeType = ''
			scrapePath = ''
			for scrapeInfo in params['scrape']:
				scrapeType = scrapeInfo['type']
				scrapePath = scrapeInfo['path'].strip('/')
				if scrapeType in ['电影', '电视剧']:
					if path.endswith(scrapeInfo['path'].strip('/')):
						break

			for vod in vodList:
				if vod['thumb'] == '':
					img = "https://serv.leuse.top/files/img/alist.png"
				elif vod['thumb'].startswith('http'):
					img = vod['thumb']
				else:
					img = baseUrl.strip('/') + vod['thumb']

				if vod['type'] == 1:
					cid = f"{baseUrl.strip('/')}{path}/{vod['name']}" if path != '/' else f"{baseUrl.strip('/')}{path}{vod['name']}"
					params['name'] = name
					params['server'] = cid
					if scrapeType in ['电影', '电视剧']:
						paramsList.append({"cid": cid, "scrapeType": scrapeType, "scrapePath": scrapePath})
					videos.append({
						"vod_id": json.dumps(params, ensure_ascii=False),
						"vod_name": vod['name'],
						"vod_pic": img,
						"vod_tag": "folder",
						"style": {
							"type": "rect",
							"ratio": 1
						},
						"vod_remarks": "文件夹"
					})
				else:
					if splitext(vod['name'])[1] in ['.mp4', '.mpg', '.mkv', '.ts', '.TS', '.avi', '.flv', '.rmvb', '.mp3', '.flac', '.wav', '.wma', '.dff']:
						if scrapeType == '电影':
							paramsList.append({"params": params, "scrapeType": scrapeType, "scrapePath": scrapePath})
						size = self.getSize(vod['size'])
						videoList.append({'fileName': vod['name'], "img": img, "remark": size})
					elif splitext(vod['name'])[1] in ['.ass', '.ssa', '.srt']:
						subtList.append(vod['name'])

			if videoList != []:
				params['name'] = name
				params['server'] = baseUrl.strip('/') + path
				params['playList'] = True
				self.setCache('alistPlayList', videoList)
				self.setCache(f"alistSubtList_{params['server']}", subtList)
				videos.insert(0, {
					"vod_id": json.dumps(params, ensure_ascii=False),
					"vod_name": '播放列表',
					"vod_pic": "https://vpsdn.leuse.top/files/img/alist.png",
					"vod_tag": 'file',
					"vod_remarks": path
				})
				del params['playList']
				for video in videoList:
					params['name'] = name
					params['server'] = f"{baseUrl.strip('/')}{path}/{video['fileName']}" if path != '/' else f"{baseUrl.strip('/')}{path}{video['fileName']}"
					videos.append({
						"vod_id": json.dumps(params, ensure_ascii=False),
						"vod_name": video['fileName'],
						"vod_pic": video['img'],
						"vod_tag": 'file',
						"vod_remarks": video['remark']
					})
			pageCount = 1
			limit = len(videos)
			total = len(videos)

			if len(paramsList) > 0:
				# self.handleScrape(paramsList)
				scrapeThread = Thread(target=self.handleScrape, args=(paramsList,))
				scrapeThread.start()
		result = {"list": videos, "page": page, "pagecount": pageCount, "limit": limit, "total": total}
		return result

	def detailContent(self, did):
		params = json.loads(did[0])
		if 'id' in params:
			self.categoryContent(did[0], 1, False, {})
			params['playList'] = True
			result = next(self.handleSqlite(params={'table': 'alist', "where": {"id": str(params['id'])}}, page=1, act='get'))[0]
			scrapeInfos = json.loads(unquote(result['dbInfos']))
			name = scrapeInfos['title']
			year = scrapeInfos['year']
			content = scrapeInfos['intro'].strip()
			actors = ''
			for actor in scrapeInfos['actors']:
				actors += f"{actor['name']}|"
			actors = actors.strip('|')
			directors = ''
			for director in scrapeInfos['directors']:
				directors += f"{director['name']}|"
			directors = directors.strip('|')
			countries = ''
			for country in scrapeInfos['countries']:
				countries += f"{country}|"
			countries = countries.strip('|')
		else:
			name = params['name']
			year = ''
			content = ''
			actors = ''
			directors = ''
			countries = ''
		if 'playList' in params and params['playList']:
			playUrl = ''
			fileList = self.getCache('alistPlayList')
			self.delCache('alistPlayList')
			del params['playList']
			for file in fileList:
				params['url'] = f'{params["server"].strip("/")}/{file["fileName"]}'
				playUrl += f'{file["fileName"]}${json.dumps(params, ensure_ascii=False)}#'
		else:
			params['url'] = params["server"]
			playUrl = f'{re.search(r".*/(.*)", params["server"]).group(1)}${json.dumps(params, ensure_ascii=False)}'

		vod = {
			"vod_id": did,
			"vod_name": name,
			"vod_actor": actors,
			"vod_year": year,
			"vod_area": countries,
			"vod_director": directors,
			"vod_content": content,
			"vod_play_from": "播放",
			"vod_play_url": playUrl.strip('#')
		}
		result = {'list': [vod]}
		return result

	def searchContent(self, key, quick):
		return self.searchContentPage(key, quick, '1')

	def searchContentPage(self, keywords, quick, page):
		keywords = f"%{keywords}%"
		videos = []
		for result, total in self.handleSqlite(params={'table': 'alist', "where": {"location": str(keywords)}}, page=1, act='get'):
			for driveInfos in self.alistInfos['drives']:
				params = driveInfos.copy()
				if result['location'].startswith(params['server'].strip('/')):
					params['server'] = result['location']
					params['id'] = result['id']
					scrapeInfos = json.loads(unquote(result['dbInfos']))
					pic = re.sub(r'photo/(.*?)/', 'photo/l/', scrapeInfos['pic']['large']) + '@User-Agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36@Referer=https://www.douban.com/'
					remark = scrapeInfos['card_subtitle'].replace(' / ', '/').strip()
					videos.append({
						"vod_id": json.dumps(params, ensure_ascii=False),
						"vod_name": scrapeInfos['title'],
						"vod_pic": pic,
						"vod_remarks": remark
					})
					break
		result = {'list': videos}
		return result

	def playerContent(self, flag, pid, vipFlags):
		params = json.loads(pid)
		url = self.getDownloadUrl(params)

		subs = []
		subList = self.getCache(f"alistSubtList_{params['server']}") if self.getCache(f"alistSubtList_{params['server']}") else []
		for sub in subList:
			if splitext(sub)[1] == '.srt':
				subFormat = 'application/x-subrip'
			elif splitext(sub)[1] == '.ass':
				subFormat = 'application/x-subtitle-ass'
			elif splitext(sub)[1] == '.ssa':
				subFormat = 'text/x-ssa'
			else:
				subFormat = 'text/plain'
			subUrl = f'http://127.0.0.1:9978/proxy?do=py&format={subFormat}'
			for key in params:
				subUrl += f"&{key}={params[key]}"
			subs.append({'url': subUrl, 'name': sub, 'format': subFormat})
		result = {"url": url, 'subs': subs, "parse": 0}
		return result

	def localProxy(self, params):
		format = params['format']
		url = self.getDownloadUrl(params)
		header = self.header
		header["Location"] = url
		return [302, format, None, header]

	def getDownloadUrl(self, params):
		url = params['url']
		password = ''
		if url.count('/') == 2:
			baseUrl = f"{url}/"
		else:
			baseUrl = re.search(r"(http.*://.*?/)", url).group(1)
		header = self.header.copy()
		header['Referer'] = baseUrl
		token = self.getCache(f'alistToken_{baseUrl}')
		if token:
			token = token['token']
		else:
			r = requests.post(baseUrl + 'api/auth/login', json=params['login'] if 'login' in params else None, headers=header)
			data = r.json()
			if data['code'] == 200:
				token = data['data']['token']
				self.setCache(f'alistToken_{baseUrl}', {'token': token, 'expires_at': int(time.time())+86400})
		header['Authorization'] = token
		path = urlparse(url).path if urlparse(url).path != '' else '/'
		if 'params' in params:
			for param in params[params]:
				if path.startswith(param['path']) and 'pass' in param:
					password = param['pass']
					break
		param = {
			"path": path,
			'password': password
		}
		r = requests.post(baseUrl + 'api/fs/get', json=param, headers=header)
		url = r.json()['data']['raw_url']
		if not url.startswith('http'):
			url = baseUrl + url.strip('/')
		return url

	def getCache(self, key):
		value = self.fetch(f'http://127.0.0.1:9978/cache?do=get&key={key}', timeout=5).text
		if len(value) > 0:
			if value.startswith('{') and value.endswith('}') or value.startswith('[') and value.endswith(']'):
				value = json.loads(value)
				if type(value) == dict:
					if not 'expiresAt' in value or value['expiresAt'] >= int(time.time()):
						return value
					else:
						self.delCache(key)
						return None
			return value
		else:
			return None

	def setCache(self, key, value):
		if type(value) in [int, float]:
			value = str(value)
		if len(value) > 0:
			if type(value) == dict or type(value) == list:
				value = json.dumps(value, ensure_ascii=False)
		self.post(f'http://127.0.0.1:9978/cache?do=set&key={key}', data={"value": value}, timeout=5)

	def delCache(self, key):
		self.fetch(f'http://127.0.0.1:9978/cache?do=del&key={key}', timeout=5)

	def getSize(self, size):
		if size > 1024 * 1024 * 1024 * 1024.0:
			fs = "TB"
			sz = round(size / (1024 * 1024 * 1024 * 1024.0), 2)
		elif size > 1024 * 1024 * 1024.0:
			fs = "GB"
			sz = round(size / (1024 * 1024 * 1024.0), 2)
		elif size > 1024 * 1024.0:
			fs = "MB"
			sz = round(size / (1024 * 1024.0), 2)
		elif size > 1024.0:
			fs = "KB"
			sz = round(size / (1024.0), 2)
		else:
			fs = "KB"
			sz = round(size / (1024.0), 2)
		return str(sz) + fs

	def handleScrape(self, paramsList):
		header = {
			'Content-Type': 'application/json',
			'Host': 'frodo.douban.com',
			'Connection': 'Keep-Alive',
			'Referer': 'https://servicewechat.com/wx2f9b06c1de1ccfca/84/page-frame.html',
			'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/53.0.2785.143 Safari/537.36 MicroMessenger/7.0.9.501 NetType/WIFI MiniProgramEnv/Windows WindowsWechat'}
		resultList = []
		scrapeInfosList = []
		for paramsInfos in paramsList:
			location = paramsInfos['cid']
			scrapeType = paramsInfos['scrapeType']
			scrapeInfosList.append([paramsInfos['scrapePath'], scrapeType, location])
			try:
				result, _ = next(self.handleSqlite(params={'table': 'alist', "where": {"location": location, "type": scrapeType}}, act='get'))
				if result and result['id'] != '':
					resultList.append(result)
					continue
			except:
				pass

		delList = []
		for scrapeInfos in scrapeInfosList:
			try:
				page = 1
				for result, total in self.handleSqlite(params={'table': 'alist', "where": {"location": f"%{scrapeInfos[0]}%", "type": scrapeInfos[1]}}, page=page, act='get'):
					if page * 20 < total:
						page += 1
					if not result in resultList:
						if not result in delList:
							delList.append(result)
			except:
				pass

		for scrapeInfos in scrapeInfosList:
			scrapeType = scrapeInfos[1]
			location = scrapeInfos[2]
			name = location[location.rfind('/'):].strip('/')
			try:
				result, _ = next(self.handleSqlite(params={'table': 'alist', "where": {"location": location, "type": scrapeType}}, act='get'))
				if result and result['id'] != '':
					continue
			except:
				pass

			try:
				tid = ''
				dbInfos = ''
				params = {'q': name, 'start': 0, 'count': 20, 'apikey': '0ac44ae016490db2204ce0a042db2916'}
				url = 'https://frodo.douban.com/api/v2/search/movie'
				r = requests.get(url, headers=header, verify=False, params=params, timeout=5)
				videoList = r.json()['items']
				for video in videoList:
					if video['type_name'] == scrapeType:
						tid = video['target_id']
						url = f'https://frodo.douban.com/api/v2/movie/{tid}'
						params = {'apikey': '0ac44ae016490db2204ce0a042db2916'}
						r = requests.get(url, headers=header, verify=False, params=params, timeout=5)
						dbInfos = r.text
						break
			except:
				tid = ''
				dbInfos = ''
			next(self.handleSqlite(params={'table': "alist", "columns": ['id', 'type', 'location', 'dbInfos'], "values": [str(tid), scrapeType, location, quote(dbInfos)]}, act='set'))

		for result in delList:
			next(self.handleSqlite({'table': "alist", "column": "id", "value": str(result['id'])}, act='del'))

	def handleSqlite(self, params, page=1, size=20, dbName='local', act='get'):
		fileName = f'{dbName}.db'
		if not os.path.exists(f'db/{fileName}'):
			with open(fileName, 'w'):
				pass

		table = str(params['table'])

		if act == 'get':
			offset = (page - 1) * size
			where = ''
			if 'where' in params:
				whereList = []
				for key in params['where']:
					if params['where'][key].startswith('%') and params['where'][key].endswith('%'):
						whereList.append(f"{key} LIKE '{str(params['where'][key])}'")
					else:
						whereList.append(f"{key} = '{str(params['where'][key])}'")
				where = "WHERE " + " AND ".join(whereList)
			query = f"SELECT COUNT(*) FROM {table} {where}"
			with sqlite3.connect(f'db/{dbName}.db') as conn:
				row = None
				cursor = conn.cursor()
				total = cursor.execute(query).fetchone()[0]
				query += f" LIMIT {size} OFFSET {offset}"
				cursor.execute(query.replace('COUNT(*)', '*'))
				keys = [column[0] for column in cursor.description]
				for row in cursor:
					yield dict(zip(keys, row)), total
				if not row:
					yield None, 0

		elif act == 'set':
			def tableExists(cursor, table):
				cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table}'")
				result = cursor.fetchone()  # 获取一行结果
				return result is not None

			try:
				values = ','.join(['?' for _ in range(len(params['values']))])
				with sqlite3.connect(f'db/{dbName}.db') as conn:
					cursor = conn.cursor()
					if not tableExists(cursor, table):
						query = f"CREATE TABLE IF NOT EXISTS {table} ({','.join(params['columns'])})"
						cursor.execute(query)
					cursor.execute(f"SELECT {params['columns'][0]} FROM {table} WHERE {params['columns'][0]}=\"{params['values'][0]}\"")
					if cursor.fetchone():
						setStr = ','.join([f'{key}="{value}"' for key, value in dict(zip(params['columns'], params['values'])).items()])
						query = f"UPDATE {table} SET {setStr} WHERE {params['columns'][0]} = \"{params['values'][0]}\""
						cursor.execute(query)
					else:
						query = f"INSERT INTO {table} ({','.join([str(item) if not isinstance(item, str) else item for item in params['columns']])}) VALUES ({values})"
						cursor.execute(query, [str(item) if not isinstance(item, str) else item for item in params['values']])
				yield f"Set {params['columns']} to {params['values']} success"
			except Exception as erroInfos:
				yield erroInfos

		elif act == 'del':
			try:
				with sqlite3.connect(f'db/{dbName}.db') as conn:
					cursor = conn.cursor()
					query = f"DELETE FROM {table} WHERE {params['column']} = \"{str(params['value'])}\""
					cursor.execute(query)
				yield f"Del {params['column']}: {params['value']} success"
			except Exception as erroInfos:
				yield erroInfos

		else:
			yield None

	header = {
		"User-Agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/94.0.4606.54 Safari/537.36"
	}
