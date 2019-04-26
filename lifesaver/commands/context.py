# encoding: utf-8

__all__ = ['Context']

from typing import Any, List, Optional, TypeVar

import discord
from discord.ext import commands
from lifesaver import utils

T = TypeVar('T')


class Context(commands.Context):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self._paginator = commands.Paginator()

    def __iadd__(self, line: str) -> 'Context':
        self._paginator.add_line(line)
        return self

    def emoji(self, *args, **kwargs):
        """A shortcut to :meth:`BotBase.emoji`."""
        return self.bot.emoji(*args, **kwargs)

    def tick(self, *args, **kwargs):
        """A shortcut to :meth:`BotBase.tick`."""
        return self.bot.tick(*args, **kwargs)

    @property
    def pool(self):
        """A shortcut to :attr:`BotBase.pool`."""
        return self.bot.pool

    @property
    def can_send_embeds(self) -> bool:
        """Return whether the bot can send embeds in this context."""
        if self.guild is None:
            return True

        perms = self.channel.permissions_for(self.guild.me)
        return perms.embed_links

    async def send(
        self,
        content: Any = None,
        *args,
        scrub: bool = True,
        **kwargs
    ) -> discord.Message:
        """Send a message to this context. Identical to :meth:`discord.abc.Messageable.send`.

        If ``scrub`` is ``True``, then @everyone and @here mentions are removed
        from the content (after going through :py:func:`str`).
        """
        if content is not None:
            content = str(content)
            if scrub:
                content = content.replace('@everyone', '@\u200beveryone') \
                    .replace('@here', '@\u200bhere')
        return await super().send(content, *args, **kwargs)

    async def confirm(
        self,
        title: str,
        message=discord.Embed.Empty,
        *,
        color: discord.Color = discord.Color.red(),
        delete_after: bool = False,
        cancellation_message: str = None
    ) -> bool:
        """Create a confirmation prompt for the user. Returns whether the user
        reacted with an affirmative emoji.

        Parameters
        ----------
        title
            The title of the confirmation prompt.
        message
            The message (description) of the confirmation prompt.
        color
            The color of the embed. Defaults to :meth:`discord.Color.red`.
        delete_after
            Deletes the confirmation after a choice has been picked.
        cancellation_message
            A message to send after cancelling.

        Returns
        -------
        bool
            Whether the user confirmed or not.
        """
        embed = discord.Embed(title=title, description=message, color=color)
        msg: discord.Message = await self.send(embed=embed)

        reactions = [self.emoji('generic.yes'), self.emoji('generic.no')]
        for emoji in reactions:
            await msg.add_reaction(emoji)

        def check(reaction: discord.Reaction, user: discord.User) -> bool:
            return (
                user == self.author
                and reaction.message.id == msg.id
                and reaction.emoji in reactions
            )

        reaction, _ = await self.bot.wait_for('reaction_add', check=check)

        if delete_after:
            await msg.delete()

        confirmed = reaction.emoji == reactions[0]
        if not confirmed and cancellation_message:
            await self.send(cancellation_message)

        return confirmed

    async def wait_for_response(self) -> discord.Message:
        """Wait for a message from the message author, then returns it.

        The message we are waiting for will only be accepted if it was sent by
        the original command invoker, and if it was sent in the same channel as
        the command message.

        Returns
        -------
        discord.Message
            The sent message.
        """

        def check(msg: discord.Message):
            if isinstance(msg.channel, discord.DMChannel):
                # Accept any message, because we are in a DM.
                return True
            return msg.channel == self.channel and msg.author == self.author

        return await self.bot.wait_for('message', check=check)

    async def pick_from_list(
        self,
        choices: List[T],
        *,
        delete_after_choice: bool = False,
        tries: int = 3
    ) -> Optional[T]:
        """Send a list of items, allowing the user to pick one. Returns the
        picked item.

        The choices are formatted with :func:`lifesaver.utils.formatting.format_list`.

        Parameters
        ----------
        choices
            The list of choices.
        delete_after_choice
            Deletes the message prompt after the user has picked.
        tries
            The amount of tries to grant the user.
        """
        choices_list = utils.format_list(choices)

        choices_message = await self.send('Pick one, or send `cancel`.\n\n' + choices_list)
        remaining_tries = tries
        picked = None

        while True:
            if remaining_tries <= 0:
                await self.send('You ran out of tries, I give up!')
                return None

            msg = await self.wait_for_response()

            if msg.content == 'cancel':
                await self.send('Canceled selection.')
                break

            try:
                chosen_index = int(msg.content) - 1
            except ValueError:
                await self.send('Invalid number. Send the number of the item you want.')
                remaining_tries -= 1
                continue

            if chosen_index < 0 or chosen_index > len(choices) - 1:
                await self.send('Invalid choice. Send the number of the item you want.')
                remaining_tries -= 1
            else:
                picked = choices[chosen_index]
                if delete_after_choice:
                    await choices_message.delete()
                    await msg.delete()
                break

        return picked

    def new_paginator(self, *args, **kwargs):
        self._paginator = commands.Paginator(*args, **kwargs)

    async def send_pages(self):
        for page in self._paginator.pages:
            await self.send(page)

    async def ok(self, emoji: str = None):
        """Respond with an emoji in acknowledgement to an action performed by the user.

        This method tries to react to the original message, falling back to the
        emoji being sent a message in the channel. This additionally falls back
        to sending the author a direct message with the emoji.

        If all of these fail, the message author will not be notified.

        Parameters
        ----------
        emoji
            The emoji to react with.
        """
        emoji = emoji or self.emoji('generic.ok')
        actions = [self.message.add_reaction, self.send, self.author.send]

        for action in actions:
            try:
                await action(emoji)
                break
            except discord.HTTPException:
                pass