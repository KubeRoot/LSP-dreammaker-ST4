from genericpath import exists
import gzip
from LSP.plugin import AbstractPlugin
from LSP.plugin import register_plugin
from LSP.plugin import unregister_plugin
from LSP.plugin.core.protocol import WorkspaceFolder
from LSP.plugin.core.types import ClientConfig
from LSP.plugin.core.typing import Any, Callable, List, Dict, Mapping, Optional, Tuple
import sublime
import os
import urllib.request
import hashlib
from .utils import *

URL = "https://wombat.platymuus.com/ss13/dm-langserver/update.php?sublime={}&platform={}&arch={}"
__version__ = "st4-0.1.0"

class DreamMakerST4(AbstractPlugin):
    environment_file = None

    @classmethod
    def name(cls) -> str:
        return "LSP-{}".format(cls.__name__.lower())

    @classmethod
    def basedir(cls) -> str:
        return os.path.join(cls.storage_path(), cls.name())

    @classmethod
    def configuration(cls) -> Tuple[sublime.Settings, str]:
        base_name = "{}.sublime-settings".format(cls.name())
        file_path = "Packages/{}/{}".format(cls.name(), base_name)
        return sublime.load_settings(base_name), file_path

    @classmethod
    def binplatform(cls) -> str:
        return {
            "windows": "win32",
            "osx": "darwin",
            "linux": "linux"
        }[sublime.platform()]

    @classmethod
    def auto_update_file(cls) -> str:
        arch = sublime.arch()
        platform = cls.binplatform()
        extension = ".exe" if platform == "win32" else ""
        path = os.path.join(cls.basedir(), "dm-langserver-{}-{}{}".format( arch, platform, extension))
        return path

    @classmethod
    def binfile(cls) -> str:
        settings, _ = cls.configuration()
        path = settings.get("langserverPath")
        if path is None:
            path = cls.auto_update_file()
        return path

    @classmethod
    def binhash(cls):
        path = cls.auto_update_file()
        if not exists(path):
            return None
        h = hashlib.new('md5')
        with open(path, 'rb') as f:
            h.update(f.read())
        return h.hexdigest()

    @classmethod
    def needs_update_or_installation(cls) -> bool:
        settings, _ = cls.configuration()

        choice = settings.get("autoUpdate")

        if choice is None:
            hash = cls.binhash()

            if hash:
                choices = [
                    "Enable dm-langserver updates (recommended).",
                    "Disable dm-langserver updates.",
                ]
                choice_actions = ['yes', 'no']
            else:
                choices = [
                    "Install dm-langserver now and enable updates (recommended).",
                    "Install dm-langserver now, but disable updates.",
                    "Manually install and configure dm-langserver executable.",
                ]
                choice_actions = ['yes', 'once', 'no']

            promise = Promise()
            sublime.active_window().show_quick_panel(
                choices,
                promise.notify,
                sublime.KEEP_OPEN_ON_FOCUS_LOST,
            )
            index, = promise.wait()

            if index < 0:
                # cancel = do nothing, but ask again later
                choice = False
            else:
                act = choice_actions[index]
                if act == 'yes':
                    cls.set_config('autoUpdate', True)
                    choice = True
                elif act == 'once':
                    cls.set_config('autoUpdate', False)
                    choice = True
                elif act == 'no':
                    cls.set_config('autoUpdate', False)
                    choice = False

        return choice

    @classmethod
    def install_or_update(cls) -> None:
        binplatform = cls.binplatform()
        url = URL.format(__version__, binplatform, sublime.arch())
        hash = cls.binhash()
        if hash:
            url += "&hash={}".format(hash)

        res = urllib.request.urlopen(url)

        print('dm-langserver updater:', res.status, res.reason)

        if res.status == 200:  # New version
            out_file = cls.auto_update_file()
            os.makedirs(cls.basedir(), exist_ok=True)
            with open(out_file, "wb") as stream:
                encoding = res.headers.get('Content-encoding')
                if encoding == 'gzip':
                    with gzip.open(res) as gz:
                        stream.write(gz.read())
                elif encoding is None:
                    with res:
                        stream.write(res.read())
                else:
                    raise Exception("Unknown Content-encoding: {}".format(encoding))

            # mark the file as executable
            mode = os.stat(out_file).st_mode
            mode |= stat.S_IXUSR
            os.chmod(out_file, mode)

        elif res.status in (204, 304):  # Unmodified
            if hash:
                return
            raise Exception("Binaries are not available for {}-{}.".format(sublime.arch(), binplatform))

        elif res.status == 404:  # Not found
            raise Exception("Binaries are not available for {}-{}.".format(sublime.arch(), binplatform))

        elif res.status == 410:  # Endpoint removed
            cls.set_config('autoUpdate', False)
            raise Exception("Update endpoint removed, try updating the extension.")

        else:  # Error
            raise Exception("Server returned {} {}.".format(res.status, res.reason))

    @classmethod
    def set_config(cls, key, value):
        settings, _ = cls.configuration()
        settings.set(key, value)
        sublime.save_settings("{}.sublime-settings".format(cls.name()))

    @classmethod
    def additional_variables(cls) -> Optional[Dict[str, str]]:
        return {
            "langserverPath": cls.binfile()
        }

    @classmethod
    def can_start(cls, window: sublime.Window, initiating_view: sublime.View, workspace_folders: List[WorkspaceFolder], configuration: ClientConfig) -> Optional[str]:
        path = cls.binfile()
        if not exists(path):
            return "Could not find dm-langserver executable at path \"{}\"".format(path)

    def m__window_status(self, params):
        """handles the $window/status notifications"""
        if params["environment"]:
            self.environment_file = "{}.dme".format(params["environment"])
        self.weaksession().set_window_status_async(DreamMakerST4.name(), ", ".join(params["tasks"]))
        print("; ".join(params["tasks"]))

def plugin_loaded() -> None:
    register_plugin(DreamMakerST4)


def plugin_unloaded() -> None:
    unregister_plugin(DreamMakerST4)