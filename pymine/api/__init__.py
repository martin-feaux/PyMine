# A flexible and fast Minecraft server software written completely in Python.
# Copyright (C) 2021 PyMine

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.
import importlib
import asyncio
import zipfile
import time
import yaml
import git
import sys
import os

from pymine.api.events import PacketEvent, ServerStartEvent, ServerStopEvent
from pymine.types.abc import AbstractPlugin, AbstractEvent
from pymine.api.commands import CommandHandler
from pymine.api.register import Register


class PyMineAPI:
    def __init__(self, server):
        self.server = server
        self.console = server.console

        self.plugins = {}  # {plugin_quali_name: plugin_cog_instance}
        self.tasks = []
        self.console_task = None

        self.commands = CommandHandler(server)  # for commands
        self.register = Register()  # for non-event registering, like world generators

        self.eid_current = 0  # used to not generate duplicate entity ids

    def trigger_handlers(self, handlers: dict) -> None:
        for handler in handlers.values():
            try:
                self.tasks.append(asyncio.create_task(handler()))
            except BaseException as e:
                self.console.error(
                    f"Failed to call handler {handler.__module__}.{handler.__qualname__} due to: {self.console.f_traceback(e)}"
                )

    async def call_async(self, func, *args, **kwargs):  # used to run a blocking function in a process pool
        await asyncio.get_event_loop().run_in_executor(self.executor, func, *args, **kwargs)

    def eid(self):  # used to generate entity ids
        self.eid_current += 1
        return self.eid_current

    def update_repo(self, git_dir, git_url, root, plugin_name, do_clone=False):
        if do_clone:
            try:
                os.rename(root, os.path.join("plugins", f".{plugin_name}_backup_{int(time.time())}"))
                self.console.warn(f"Backing up and resetting {plugin_name}...")
            except FileNotFoundError as e:
                pass

            self.console.debug(f"Cloning from {git_url}...")
            git_dir.clone(git_url)
            self.console.info(f"Updated {plugin_name}!")

            return

        if not os.path.isdir(os.path.join(root, ".git")):
            return self.update_repo(git_dir, git_url, root, plugin_name, True)

        try:
            self.console.debug(f"Pulling from {git_url}...")
            res = git.Git(root).pull()  # pull latest from remote
        except BaseException as e:
            self.console.debug(f"Failed to pull from {git_url}, attempting to clone...")
            return self.update_repo(git_dir, git_url, root, plugin_name, True)

        if res == "Already up to date.":
            self.console.info(f"No updates found for {plugin_name}.")
        else:
            self.console.info(f"Updated {plugin_name}!")

    @staticmethod
    def load_plugin_config(root):
        plugin_config_file = os.path.join(root, "plugin.yml")

        try:
            with open(plugin_config_file) as conf:
                conf = yaml.safe_load(conf.read())
        except yaml.YAMLError:
            raise ValueError("Failed to parse plugin.yml")

        if not isinstance(conf, dict):
            raise ValueError("plugin.yml must contain a dict")

        if conf.get("git_url") is not None and not isinstance(conf["git_url"], str):
            raise ValueError('Value "git_url" must be of type "str"')

        if conf.get("module_folder") is not None and not isinstance(conf["module_folder"], str):
            raise ValueError('Value "module_folder" must be of type "str"')

        for key, value in conf.items():
            if value == "":
                conf[key] = None

        return conf

    @staticmethod
    async def install_plugin_deps(root):  # may need to be altered to support poetry.
        """Installs dependencies for a plugin."""

        requirements_file = os.path.join(root, "requirements.txt")

        if os.path.isfile(requirements_file):
            if not os.path.isfile(sys.executable):
                raise RuntimeError("Couldn't find system executable to update dependencies.")

            proc = await asyncio.subprocess.create_subprocess_shell(
                f"{sys.executable} -m pip install -U -r {requirements_file}",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            _, stderr = await asyncio.wait_for(proc.communicate(), 120)

            if proc.returncode != 0:
                raise RuntimeError(stderr.decode())

    async def load_plugin(self, git_dir, plugin_name):
        """Handles plugin-auto-updating, loading plugin configs, and importing + calling the setup() function in a plugin."""

        if plugin_name.startswith("."):
            return

        root = os.path.join("plugins", plugin_name)

        if os.path.isfile(root):
            if root.endswith(".py"):  # .py file (so try to import)
                try:
                    plugin_path = root.rstrip(".py").replace("\\", "/").replace("/", ".")

                    plugin_module = importlib.import_module(plugin_path)
                    await plugin_module.setup(None)

                    self.plugins[plugin_path] = plugin_module
                except BaseException as e:
                    self.console.error(f"Error while loading {plugin_name}: {self.console.f_traceback(e)}")

            return

        plugin_config_file = os.path.join(root, "plugin.yml")

        if not os.path.isfile(plugin_config_file):
            self.console.error(f"Error while loading {plugin_name}: Missing plugin.yml.")
            return

        try:
            conf = self.load_plugin_config(root)
        except ValueError as e:
            self.console.error(f"Error while loading {plugin_name}: Invalid plugin.yml ({str(e)})")
            return
        except BaseException as e:
            self.console.error(f"Error while loading {plugin_name}: {self.console.f_traceback(e)}")
            return

        try:
            await self.install_plugin_deps(root)
        except BaseException as e:
            self.console.error(f"Error while loading {plugin_name}: {self.console.f_traceback(e)}")
            return

        if conf.get("git_url"):
            self.console.info(f"Checking for updates for {plugin_name}...")

            try:
                self.update_repo(git_dir, conf["git_url"], root, plugin_name)
            except BaseException as e:
                self.console.error(f"Error while updating {plugin_name}: {self.console.f_traceback(e)}")

        plugin_path = root

        if conf.get("module_folder"):
            plugin_path = os.path.join(plugin_path, conf["module_folder"])

        plugin_path = plugin_path.replace("\\", "/").replace("/", ".")

        try:
            plugin_module = importlib.import_module(plugin_path)
        except BaseException as e:
            self.console.error(f"Error while loading {plugin_name}: {self.console.f_traceback(e)}")
            return

        try:
            await plugin_module.setup(conf)
        except BaseException as e:
            self.console.error(f"Error while setting up {plugin_name}: {self.console.f_traceback(e)}")

    def add_plugin(self, plugin: AbstractPlugin) -> None:
        """Actually registers the plugin cog and all of its events / registered things."""

        if not isinstance(plugin, AbstractPlugin):
            raise ValueError("Plugin must be an instance of AbstractPlugin.")

        plugin_quali_name = f"{plugin.__module__}.{plugin.__class__.__name__}"

        self.console.debug("add_plugin() called for " + plugin_quali_name)

        self.plugins[plugin_quali_name] = plugin

        for attr in dir(plugin):
            thing = getattr(plugin, attr)

            if isinstance(thing, AbstractEvent):
                if isinstance(thing, PacketEvent):
                    try:
                        self.register._on_packet[thing.state_id][thing.packet_id][plugin_quali_name] = thing
                    except KeyError:
                        self.register._on_packet[thing.state_id][thing.packet_id] = {plugin_quali_name: thing}
                elif isinstance(thing, ServerStartEvent):
                    self.register._on_server_start[plugin_quali_name] = thing
                elif isinstance(thing, ServerStopEvent):
                    self.register._on_server_stop[plugin_quali_name] = thing
                else:
                    self.console.warn(f"Unsupported event type: {thing.__module__}.{thing.__class__.__qualname__}")

    async def init(self):  # called when server starts up
        self.commands.load_commands()

        # Load packet handlers / packet logic handlers under pymine/logic/handle
        for root, dirs, files in os.walk(os.path.join("pymine", "logic", "handle")):
            for file in filter((lambda f: f.endswith(".py")), files):
                importlib.import_module(os.path.join(root, file)[:-3].replace("\\", "/").replace("/", "."))

        # Load world generators from pymine/logic/world_gen
        for root, dirs, files in os.walk(os.path.join("pymine", "logic", "world_gen")):
            for file in filter((lambda f: f.endswith(".py")), files):
                importlib.import_module(os.path.join(root, file)[:-3].replace("\\", "/").replace("/", "."))

        try:
            os.mkdir("plugins")
        except FileExistsError:
            pass

        plugins_dir = os.listdir("plugins")
        git_dir = git.Git("plugins")

        results = await asyncio.gather(*[self.load_plugin(git_dir, plugin) for plugin in plugins_dir], return_exceptions=True)

        for plugin, result in zip(plugins_dir, results):
            if isinstance(result, BaseException):
                self.console.error(f"Error while loading {plugin}: {self.console.f_traceback(result)}")

        # start console command handler task
        self.console_task = asyncio.create_task(self.commands.handle_console_commands())

        return self

    async def stop(self):  # called when server is stopping
        self.console_task.cancel()

        for task in self.tasks:
            try:
                await asyncio.wait_for(task, 5)
            except asyncio.TimeoutError:
                task.cancel()

        for plugin_name, plugin_cog in self.plugins.items():
            try:
                await plugin_cog.teardown()
            except BaseException as e:
                self.console.error(f"Error while tearing down {plugin_name}: {self.console.f_traceback(e)}")
