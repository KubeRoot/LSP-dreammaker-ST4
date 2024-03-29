# DreamMaker Language Client - Sublime package for DreamMaker Language Server
# Copyright (C) 2019  Tad Hardesty
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

# 'utils' package
import os
import stat
import sublime
import hashlib
import webbrowser
import time

from threading import Condition, Thread


def is_executable(path):
	req = stat.S_IXUSR | stat.S_IRUSR
	try:
		return (os.stat(path).st_mode & req) == req
	except FileNotFoundError:
		return False


def md5_file(path):
	h = hashlib.new('md5')
	with open(path, 'rb') as f:
		h.update(f.read())
	return h.hexdigest()


def cache_path():
	return os.path.join(sublime.cache_path(), 'DreamMaker Language Client')


def get_config(name, default=None):
	return sublime.load_settings("dreammaker.sublime-settings").get(name, default)


def set_config(name, value):
	sublime.load_settings("dreammaker.sublime-settings").set(name, value)
	sublime.save_settings("dreammaker.sublime-settings")


def open_config():
	sublime.run_command('edit_settings', {
		"base_file": "${packages}/DreamMaker Language Client/dreammaker.sublime-settings",
		"default": "// Settings in here override the defaults\n{\n\t$0\n}",
	})


def find_byond_file(nameset):
	opt = get_config('byondPath')
	if isinstance(opt, str):
		opt = [opt]
	if not opt:
		sublime.error_message("A BYOND path must be provided to use this feature.")
		open_config()
		return

	if isinstance(nameset, str):
		nameset = [nameset]

	for each in opt:
		for name in nameset:
			binary = "{}/{}".format(each, name)
			if os.path.exists(binary):
				return binary


def when_view_loaded(view, callback):
	if view.is_loading():
		def wait_until_loaded():
			while view.is_loading():
				time.sleep(0.1)
			callback()
		Thread(target=wait_until_loaded).start()
	else:
		callback()


class Promise:
	def __init__(self):
		self.cv = Condition()

	def notify(self, *args):
		with self.cv:
			self.result = args
			self.cv.notify()

	def wait(self):
		with self.cv:
			self.cv.wait()
			return self.result

