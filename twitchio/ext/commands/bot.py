"""
MIT License

Copyright (c) 2017 - Present PythonistaGuild

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, TypeAlias, Unpack

from twitchio.client import Client

from .context import Context
from .converters import _BaseConverter
from .core import Command, CommandErrorPayload, Group, Mixin
from .exceptions import *


if TYPE_CHECKING:
    from collections.abc import Callable, Coroutine, Iterable

    from models.eventsub_ import ChatMessage

    from twitchio.eventsub.subscriptions import SubscriptionPayload
    from twitchio.types_.eventsub import SubscriptionResponse
    from twitchio.types_.options import ClientOptions
    from twitchio.user import PartialUser

    from .components import Component

    PrefixT: TypeAlias = str | Iterable[str] | Callable[["Bot", ChatMessage], Coroutine[Any, Any, str | Iterable[str]]]


logger: logging.Logger = logging.getLogger(__name__)


class Bot(Mixin[None], Client):
    """The TwitchIO ``commands.Bot`` class.

    The Bot is an extension of and inherits from :class:`twitchio.Client` and comes with additonal powerful features for
    creating and managing bots on Twitch.

    Unlike :class:`twitchio.Client`, the :class:`~.Bot` class allows you to easily make use of built-in the commands ext.

    The easiest way of creating and using a bot is via subclassing, some examples are provided below.

    .. note::

        Any examples contained in this class which use ``twitchio.Client`` can be changed to ``commands.Bot``.


    Parameters
    ----------
    client_id: str
        The client ID of the application you registered on the Twitch Developer Portal.
    client_secret: str
        The client secret of the application you registered on the Twitch Developer Portal.
        This must be associated with the same ``client_id``.
    bot_id: str
        The User ID associated with the Bot Account.
        Unlike on :class:`~twitchio.Client` this is a required argument on :class:`~.Bot`.
    owner_id: str | None
        An optional ``str`` which is the User ID associated with the owner of this bot. This should be set to your own user
        accounts ID, but is not required. Defaults to ``None``.
    prefix: str | Iterabale[str] | Coroutine[Any, Any, str | Iterable[str]]
        The prefix(es) to listen to, to determine whether a message should be treated as a possible command.

        This can be a ``str``, an iterable of ``str`` or a coroutine which returns either.

        This is a required argument, common prefixes include: ``"!"`` or ``"?"``.

    Example
    -------

        .. code:: python3

            import asyncio
            import logging

            import twitchio
            from twitchio import eventsub
            from twitchio.ext import commands

            LOGGER: logging.Logger = logging.getLogger("Bot")

            class Bot(commands.Bot):

                def __init__(self) -> None:
                    super().__init__(client_id="...", client_secret="...", bot_id="...", owner_id="...", prefix="!")

                # Do some async setup, as an example we will load a component and subscribe to some events...
                # Passing the bot to the component is completely optional...
                async def setup_hook(self) -> None:

                    # Listen for messages on our channel...
                    # You need appropriate scopes, see the docs on authenticating for more info...
                    payload = eventsub.ChatMessageSubscription(broadcaster_user_id=self.owner_id, user_id=self.bot_id)
                    await self.subscribe_websocket(payload=payload)

                    await self.add_component(SimpleCommands(self))
                    LOGGER.info("Finished setup hook!")

            class SimpleCommands(commands.Component):

                def __init__(self, bot: Bot) -> None:
                    self.bot = bot

                @commands.command()
                async def hi(self, ctx: commands.Context) -> None:
                    '''Command which sends you a hello.'''
                    await ctx.reply(f"Hello {ctx.chatter}!")

                @commands.command()
                async def say(self, ctx: commands.Context, *, message: str) -> None:
                    '''Command which repeats what you say: !say I am an apple...'''
                    await ctx.send(message)

            def main() -> None:
                # Setup logging, this is optional, however a nice to have...
                twitchio.utils.setup_logging(level=logging.INFO)

                async def runner() -> None:
                    async with Bot() as bot:
                        await bot.start()

                try:
                    asyncio.run(runner())
                except KeyboardInterrupt:
                    LOGGER.warning("Shutting down due to Keyboard Interrupt...")

            main()
    """

    def __init__(
        self,
        *,
        client_id: str,
        client_secret: str,
        bot_id: str,
        owner_id: str | None = None,
        prefix: PrefixT,
        **options: Unpack[ClientOptions],
    ) -> None:
        super().__init__(
            client_id=client_id,
            client_secret=client_secret,
            bot_id=bot_id,
            **options,
        )

        self._owner_id: str | None = owner_id
        self._get_prefix: PrefixT = prefix
        self._components: dict[str, Component] = {}
        self._base_converter: _BaseConverter = _BaseConverter(self)

    @property
    def bot_id(self) -> str:
        """Property returning the ID of the bot.

        You must ensure you set this via the keyword argument ``bot_id="..."`` in the constructor of this class.

        Returns
        -------
        str
            The ``bot_id`` that was set.
        """
        assert self._bot_id
        return self._bot_id

    @property
    def owner_id(self) -> str | None:
        """Property returning the ID of the user who owns this bot.

        This can be set via the keyword argument ``owner_id="..."`` in the constructor of this class.

        Returns
        -------
        str | None
            The owner ID that has been set. ``None`` if this has not been set.
        """
        return self._owner_id

    def _cleanup_component(self, component: Component, /) -> None:
        for command in component.__all_commands__.values():
            self.remove_command(command.name)

        for listeners in component.__all_listeners__.values():
            for listener in listeners:
                self.remove_listener(listener)

    async def _add_component(self, component: Component, /) -> None:
        for command in component.__all_commands__.values():
            command._injected = component

            if isinstance(command, Group):
                for sub in command.walk_commands():
                    sub._injected = component

            self.add_command(command)

        for name, listeners in component.__all_listeners__.items():
            for listener in listeners:
                self.add_listener(listener, event=name)

        await component.component_load()

    async def add_component(self, component: Component, /) -> None:
        """|coro|

        Method to add a :class:`.commands.Component` to the bot.

        All :class:`~.commands.Command` and :meth:`~.commands.Component.listener`'s in the component will be loaded alongside
        the component.

        If this method fails, including if :meth:`~.commands.Component.component_load` fails, everything will be rolled back
        and cleaned up and a :exc:`.commands.ComponentLoadError` will be raised from the original exception.

        Parameters
        ----------
        component: :class:`~.commands.Component`
            The component to add to the bot.

        Raises
        ------
        ComponentLoadError
            The component failed to load.
        """
        try:
            await self._add_component(component)
        except Exception as e:
            self._cleanup_component(component)
            raise ComponentLoadError from e

        self._components[component.__component_name__] = component

    async def remove_component(self, name: str, /) -> Component | None:
        """|coro|

        Method to remove a :class:`.commands.Component` from the bot.

        All :class:`~.commands.Command` and :meth:`~.commands.Component.listener`'s in the component will be unloaded
        alongside the component.

        If this method fails when :meth:`~.commands.Component.component_teardown` fails, the component will still be unloaded
        completely from the bot, with the exception being logged.

        Parameters
        ----------
        name: str
            The name of the component to unload.

        Returns
        -------
        Component | None
            The component that was removed. ``None`` if the component was not found.
        """
        component: Component | None = self._components.pop(name, None)
        if not component:
            return component

        self._cleanup_component(component)

        try:
            await component.component_teardown()
        except Exception as e:
            msg = f"Ignoring exception in {component.__class__.__qualname__}.component_teardown: {e}\n"
            logger.error(msg, exc_info=e)

        return component

    async def _process_commands(self, message: ChatMessage) -> None:
        ctx: Context = Context(message, bot=self)
        await self.invoke(ctx)

    async def process_commands(self, message: ChatMessage) -> None:
        await self._process_commands(message)

    async def invoke(self, ctx: Context) -> None:
        try:
            await ctx.invoke()
        except CommandError as e:
            payload = CommandErrorPayload(context=ctx, exception=e)
            self.dispatch("command_error", payload=payload)

    async def event_message(self, payload: ChatMessage) -> None:
        if payload.chatter.id == self.bot_id:
            return

        await self.process_commands(payload)

    async def event_command_error(self, payload: CommandErrorPayload) -> None:
        """An event called when an error occurs during command invocation.

        By default this event logs the exception raised.

        You can override this method, however you should take care to log unhandled exceptions.

        Parameters
        ----------
        payload: :class:`.commands.CommandErrorPayload`
            The payload associated with this event.
        """
        command: Command[Any, ...] | None = payload.context.command
        if command and command.has_error and payload.context.error_dispatched:
            return

        msg = f'Ignoring exception in command "{payload.context.command}":\n'
        logger.error(msg, exc_info=payload.exception)

    async def before_invoke(self, ctx: Context) -> None:
        """A pre invoke hook for all commands that have been added to the bot.

        Commands from :class:`~.commands.Component`'s are included, however if you wish to control them separately,
        see: :meth:`~.commands.Component.component_before_invoke`.

        The pre-invoke hook will be called directly before a valid command is scheduled to run. If this coroutine errors,
        a :exc:`~.commands.CommandHookError` will be raised from the original error.

        Useful for setting up any state like database connections or http clients for command invocation.

        The order of calls with the pre-invoke hooks is:

        - :meth:`.commands.Bot.before_invoke`

        - :meth:`.commands.Component.component_before_invoke`

        - Any ``before_invoke`` hook added specifically to the :class:`~.commands.Command`.


        .. note::

            This hook only runs after successfully parsing arguments and passing all guards associated with the
            command, component (if applicable) and bot.

        Parameters
        ----------
        ctx: :class:`.commands.Context`
            The context associated with command invocation, before being passed to the command.
        """

    async def after_invoke(self, ctx: Context) -> None:
        """A post invoke hook for all commands that have been added to the bot.

        Commands from :class:`~.commands.Component`'s are included, however if you wish to control them separately,
        see: :meth:`~.commands.Component.component_after_invoke`.

        The post-invoke hook will be called after a valid command has been invoked. If this coroutine errors,
        a :exc:`~.commands.CommandHookError` will be raised from the original error.

        Useful for cleaning up any state like database connections or http clients.

        The order of calls with the post-invoke hooks is:

        - :meth:`.commands.Bot.after_invoke`

        - :meth:`.commands.Component.component_after_invoke`

        - Any ``after_invoke`` hook added specifically to the :class:`~.commands.Command`.


        .. note::

            This hook is always called even when the :class:`~.commands.Command` fails to invoke but similar to
            :meth:`.before_invoke` only if parsing arguments and guards are successfully completed.

        Parameters
        ----------
        ctx: :class:`.commands.Context`
            The context associated with command invocation, after being passed through the command.
        """

    async def global_guard(self, ctx: Context, /) -> bool:
        """|coro|

        A global guard applied to all commmands added to the bot.

        This coroutine function should take in one parameter :class:`~.commands.Context` the context surrounding
        command invocation, and return a bool indicating whether a command should be allowed to run.

        If this function returns ``False``, the chatter will not be able to invoke the command and an error will be
        raised. If this function returns ``True`` the chatter will be able to invoke the command,
        assuming all the other guards also pass their predicate checks.

        See: :func:`~.commands.guard` for more information on guards, what they do and how to use them.

        .. note::

            This is the first guard to run, and is applied to every command.

        .. important::

            Unlike command specific guards or :meth:`.commands.Component.guard`, this function must
            be always be a coroutine.


        This coroutine is intended to be overriden when needed and by default always returns ``True``.

        Parameters
        ----------
        ctx: commands.Context
            The context associated with command invocation.

        Raises
        ------
        GuardFailure
            The guard predicate returned ``False`` and prevented the chatter from using the command.
        """
        return True

    async def subscribe_webhook(
        self,
        *,
        payload: SubscriptionPayload,
        as_bot: bool = True,
        token_for: str | PartialUser | None,
        callback_url: str | None = None,
        eventsub_secret: str | None = None,
    ) -> SubscriptionResponse | None:
        return await super().subscribe_webhook(
            payload=payload,
            as_bot=as_bot,
            token_for=token_for,
            callback_url=callback_url,
            eventsub_secret=eventsub_secret,
        )

    async def subscribe_websocket(
        self,
        *,
        payload: SubscriptionPayload,
        as_bot: bool = True,
        token_for: str | PartialUser | None = None,
        socket_id: str | None = None,
    ) -> SubscriptionResponse | None:
        return await super().subscribe_websocket(payload=payload, as_bot=as_bot, token_for=token_for, socket_id=socket_id)
