#!/usr/bin/env python
# encoding: utf-8

# primitive sanity tests

from __future__ import unicode_literals

import os
import sys
import shutil
import re
import pprint
import copy
import time
if sys.version_info[0] == 3:
	basestring = str

TestGarbledPathNames = False

# store the output, for further analysis
class StorePrinter(object):
	def __init__(self, opr):
		self.opr = opr
		self.q = []

	def pr(self, msg):
		self.q.append(msg)
		self.opr(msg)

	def empty(self):
		del self.q[:]

	def getq(self):
		return self.q

def banner(msg):
	title = "{0} {1} {0}".format('=' * 8, msg)
	line = '=' * len(title)
	print(line)
	print(title)
	print(line)

def ifany(list, require):
	for element in list:
		if require(element):
			return True

	return False

def filterregex(list, regex):
	rec = re.compile(regex)
	return filter(lambda x: rec and isinstance(x, basestring) and rec.search(x), list)

def makesuredir(dirname):
	if not os.path.exists(dirname):
		os.mkdir(dirname)

# TODO: this is a quick hack, need to re-structure the directory later
# http://stackoverflow.com/questions/11536764/attempted-relative-import-in-non-package-even-with-init-py/27876800#27876800
bypydir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
#sys.path.insert(0, bypydir)
sys.path.append(bypydir)
#print(sys.path)
configdir = 'configdir'
downloaddir = 'downdir'
testdir = 'testdir'
sharedir = 'sharedir'
import bypy
# monkey patch all the way
mpr = StorePrinter(bypy.pr)
bypy.pr = mpr.pr
# create some dummy files
zerofilename = os.path.join(testdir, 'allzero.1m.bin')
makesuredir(configdir)
shutil.copy('bypy.json', configdir)
shutil.copy('bypy.setting.json', configdir)
by = bypy.ByPy(configdir=configdir, debug=1, verbose=1)

def testmergeinto():
	fromc = {
		'a': {
			'a1': 1,
			'a2': 2
		},
		'b': {
			'b1': 10,
			'b2': 20
		}
	}

	to = {
		'a': {
			'a1': 9,
			'a3': 3
		},
		'b': {
			'b2': 90,
			'b3': 30,
		},
		'c': {
			'c1': 100
		}
	}
	toorig = copy.deepcopy(to)

	pprint.pprint(fromc)
	pprint.pprint(to)
	bypy.cached.mergeinto(fromc, to)
	pprint.pprint(to)
	print(repr(to))
	assert to == {u'a': {u'a1': 9, u'a3': 3, u'a2': 2}, u'c': {u'c1': 100}, u'b': {u'b1': 10, u'b2': 90, u'b3': 30}}

	to = toorig
	pprint.pprint(fromc)
	pprint.pprint(to)
	bypy.cached.mergeinto(fromc, to, False)
	pprint.pprint(to)
	print(repr(to))
	assert to == {u'a': {u'a1': 1, u'a3': 3, u'a2': 2}, u'c': {u'c1': 100}, u'b': {u'b1': 10, u'b2': 20, u'b3': 30}}

def createdummyfile(filename, size, value = 0):
	with open(filename, 'wb') as f:
		ba = bytearray([value] * size)
		f.write(ba)

def prepare():
	# preparation
	if 'refresh' in sys.argv:
		by.refreshtoken()
	# we must upload something first, otherwise, listing / deleting the root directory will fail
	banner("Uploading a file")
	assert by.upload(testdir + '/a.txt') == bypy.ENoError
	print("Response: {}".format(by.response.json()))
	banner("Listing the root directory")
	assert by.list('/') == bypy.ENoError
	print("Response: {}".format(by.response.json()))
	mpr.empty()
	createdummyfile(zerofilename, 1024 * 1024)

	makesuredir(sharedir)
	sharesubdir = sharedir + '/subdir'
	makesuredir(sharesubdir)
	createdummyfile(sharedir + '/1M0.bin', 1024 * 1024)
	createdummyfile(sharedir + '/1M1.bin', 1024 * 1024, 1)
	createdummyfile(sharesubdir + '/1M2.bin', 1024 * 1024, 2)

	if TestGarbledPathNames:
		jd = testdir.encode() + os.sep.encode() + b'garble\xec\xeddir'
		jf = testdir.encode() + os.sep.encode() + b'garble\xea\xebfile'
		makesuredir(jd)
		with open(jf, 'w') as f:
			f.write("garbled")

def emptyremote():
	banner("Deleting all the files at PCS")
	assert by.delete('/') == bypy.ENoError
	assert 'request_id' in by.response.json()
	mpr.empty()

def uploaddir():
	# upload
	banner("Uploading the local directory")
	assert by.upload(testdir, testdir) == bypy.ENoError
	assert filterregex(mpr.getq(),
					   r"RapidUpload: 'testdir[\\/]allzero.1m.bin' =R=\> '/apps/bypy/testdir/allzero.1m.bin' OK")
	assert filterregex(mpr.getq(), r"'testdir[\\/]a.txt' ==> '/apps/bypy/testdir/a.txt' OK.")
	assert filterregex(mpr.getq(), r"'testdir[\\/]b.txt' ==> '/apps/bypy/testdir/b.txt' OK.")
	print("Response: {}".format(by.response.json()))
	mpr.empty()

def getquota():
	# quota
	banner("Getting quota")
	assert by.info() == bypy.ENoError
	resp = by.response.json()
	print("Response: {}".format(resp))
	#assert resp['used'] == 1048626
	assert resp['quota'] == 2206539448320
	mpr.empty()

def assertsame():
	bypy.pr(by.result)
	assert len(by.result['diff']) == 0
	assert len(by.result['local']) == 0
	assert len(by.result['remote']) == 0
	assert len(by.result['same']) >= 5

def compare():
	# comparison
	banner("Comparing")
	assert by.compare(testdir, testdir) == bypy.ENoError
	assertsame()
	mpr.empty()

def downdir():
	# download
	banner("Downloading dir")
	shutil.rmtree(downloaddir, ignore_errors=True)
	assert by.downdir(testdir, downloaddir) == bypy.ENoError
	assert by.download(testdir, downloaddir) == bypy.ENoError
	assert by.compare(testdir, downloaddir) == bypy.ENoError
	assertsame()
	mpr.empty()

def syncup():
	banner("Syncing up")
	emptyremote()
	assert by.syncup(testdir, testdir) == bypy.ENoError
	assert by.compare(testdir, testdir) == bypy.ENoError
	assertsame()
	mpr.empty()

def syncdown():
	banner("Syncing down")
	shutil.rmtree(downloaddir, ignore_errors=True)
	assert by.syncdown(testdir, downloaddir) == bypy.ENoError
	assert by.compare(testdir, downloaddir) == bypy.ENoError
	shutil.rmtree(downloaddir, ignore_errors=True)
	assertsame()
	mpr.empty()

def cdl():
	banner("Offline (cloud) download")
	result = by.cdl_cancel(123)
	assert int(result) == 36016
	mpr.empty()
	assert by.cdl_list() == bypy.ENoError
	# {u'request_id': 353951550, u'task_info': [], u'total': 0}
	assert filterregex(mpr.getq(), r"'total'\s*:\s*0")
	mpr.empty()
	assert by.cdl_query(123) == bypy.ENoError
	assert filterregex(mpr.getq(), r"'result'\s*:\s*1")
	mpr.empty()
	assert by.cdl_add("http://dl.client.baidu.com/BaiduKuaijie/BaiduKuaijie_Setup.exe", testdir) == bypy.ENoError
	assert filterregex(mpr.getq(), r"'task_id'\s*:\s*\d+")
	assert by.cdl_addmon("http://dl.client.baidu.com/BaiduKuaijie/BaiduKuaijie_Setup.exe", testdir) == bypy.ENoError
	mpr.empty()

def testshare():
	banner("Share")
	#assert bypy.ENoError == by.share(sharedir, '/', True, True)
	assert bypy.ENoError == by.share(sharedir, sharedir)
	assert filterregex(mpr.getq(), r"bypy accept /{}/1M0.bin".format(sharedir))
	assert filterregex(mpr.getq(), r"bypy accept /{}/1M1.bin".format(sharedir))
	assert filterregex(mpr.getq(), r"bypy accept /{}/subdir/1M2.bin".format(sharedir))
	mpr.empty()
	assert bypy.ENoError == by.upload(sharedir, sharedir)
	assert bypy.ENoError == by.share(sharedir, sharedir, False)
	assert filterregex(mpr.getq(), r"bypy accept /{}/1M0.bin".format(sharedir))
	assert filterregex(mpr.getq(), r"bypy accept /{}/1M1.bin".format(sharedir))
	assert filterregex(mpr.getq(), r"bypy accept /{}/subdir/1M2.bin".format(sharedir))
	mpr.empty()

def main():
	testmergeinto()
	prepare()
	time.sleep(2)
	testshare()
	time.sleep(2)
	# sleep sometime helps preventing hanging requests <scorn>
	cdl()
	time.sleep(2)
	emptyremote()
	time.sleep(2)
	time.sleep(2)
	uploaddir()
	time.sleep(2)
	getquota()
	time.sleep(2)
	compare()
	time.sleep(2)
	downdir()
	time.sleep(2)
	syncup()
	time.sleep(2)
	syncdown()

	# test aria2 downloading
	global by
	by = bypy.ByPy(configdir=configdir, downloader='aria2', debug=1, verbose=1)
	downdir()

	# clean up
	os.remove(zerofilename)
	shutil.rmtree(configdir, ignore_errors=True)
	shutil.rmtree(sharedir, ignore_errors=True)
	shutil.rmtree(downloaddir, ignore_errors=True)

# this is barely a sanity test, more to be added
if __name__ == "__main__":
	main()

# vim: tabstop=4 noexpandtab shiftwidth=4 softtabstop=4 ff=unix fileencoding=utf-8
