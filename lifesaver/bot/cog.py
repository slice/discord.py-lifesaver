# encoding: utf-8

import asyncio
import inspect
import logging
import os
from typing import Type

import aiohttp
from lifesaver.config import Config


class Cog:
    """The base class for cogs."""

    def __init__(self, bot):
        #: The bot instance.
        self.bot = bot

        #: The logger for this cog.
        self.name = type(self).__name__.lower()
        self.log = logging.getLogger('cog.' + self.name)  # type: logging.Logger

        #: A ClientSession for this cog.
        self.session = aiohttp.ClientSession(loop=self.loop)

        self.config = None

        if hasattr(self, '__config_cls'):
            path = os.path.join(self.bot.config.cog_config_path, self.name + '.yml')
            self.config = getattr(self, '__config_cls').load(path)

        self._scheduled_tasks = []
        self._setup_schedules()

    @property
    def loop(self):
        return self.bot.loop

    @property
    def pg_pool(self):
        return self.bot.pg_pool

    @staticmethod
    def with_config(config_cls: Type[Config]):
        def decorator(cls):
            setattr(cls, '__config_cls', config_cls)
            return cls
        return decorator

    def _setup_schedules(self):
        # Bypass Python's name mangling.
        unload_key = '_' + type(self).__name__ + '__unload'

        self._original_unload = getattr(self, unload_key, None)
        setattr(self, unload_key, self.__unload)  # Override.

        for key in dir(self):
            func = getattr(self, key)
            if not hasattr(func, '_schedule'):
                continue

            schedule = func._schedule

            async def wrapped():
                if 'wait_until_ready' in schedule:
                    await self.bot.wait_until_ready()

                while True:
                    if 'initial_sleep' in schedule:
                        await asyncio.sleep(schedule['interval'])
                    await func()
                    await asyncio.sleep(schedule['interval'])

            task = self.bot.loop.create_task(wrapped())
            self._scheduled_tasks.append(task)

    def __unload(self):
        for scheduled_task in self._scheduled_tasks:
            self.log.debug('Cancelling scheduled task: %s', scheduled_task)
            scheduled_task.cancel()

        self.loop.create_task(self.session.close())

        if self._original_unload:
            self._original_unload()

    @classmethod
    def every(cls, interval: int, **kwargs):
        """A decorator that designates this function to be executed every ``n`` second(s).

        Parameters
        ----------
        interval
            The time interval in seconds.
        wait_until_ready
            Waits until the bot is ready before running.
        initial_sleep
            The number of seconds to sleep before running.
        """

        def outer(func):
            if not inspect.iscoroutinefunction(func):
                raise TypeError('Scheduled method is not a coroutine')

            func._schedule = {'interval': interval}
            func._schedule.update(kwargs)

            return func

        return outer
