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

import copy
import logging
import sys
import urllib.parse
from collections import deque
from collections.abc import AsyncIterator, Awaitable, Callable
from typing import TYPE_CHECKING, Any, ClassVar, Generic, Literal, TypeAlias, TypeVar

import aiohttp

from . import __version__
from .conduits import Shard
from .exceptions import HTTPException
from .models import (
    ChannelFollowedEvent,
    ChannelFollowerEvent,
    Clip,
    ExtensionTransaction,
    Game,
    SearchChannel,
    Stream,
    Video,
)
from .utils import _from_json  # type: ignore


if TYPE_CHECKING:
    import datetime
    from collections.abc import Generator, Sequence

    from typing_extensions import Self, Unpack

    from .assets import Asset
    from .types_.conduits import ShardData, ShardUpdateRequest
    from .types_.requests import APIRequestKwargs, HTTPMethod, ParamMapping
    from .types_.responses import (
        AdScheduleResponse,
        BitsLeaderboardResponse,
        ChannelEditorsResponse,
        ChannelEmotesResponse,
        ChannelFollowersResponseData,
        ChannelInformationResponse,
        CheermotesResponse,
        ClipsResponseData,
        ConduitPayload,
        ContentClassificationLabelsResponse,
        CustomRewardsResponse,
        DeleteVideosResponse,
        ExtensionTransactionsResponseData,
        FollowedChannelsResponseData,
        GamesResponse,
        GamesResponseData,
        GlobalChatBadgesResponse,
        GlobalEmotesResponse,
        RawResponse,
        SearchChannelsResponseData,
        SnoozeNextAdResponse,
        StartCommercialResponse,
        StreamsResponseData,
        TeamsResponse,
        TopGamesResponseData,
        UserChatColorResponse,
        VideosResponseData,
    )


logger: logging.Logger = logging.getLogger(__name__)


T = TypeVar("T")
PaginatedConverter: TypeAlias = Callable[[Any], Awaitable[T]] | None


async def json_or_text(resp: aiohttp.ClientResponse) -> dict[str, Any] | str:
    text: str = await resp.text()

    try:
        if resp.headers["Content-Type"].startswith("application/json"):
            return _from_json(text)  # type: ignore
    except KeyError:
        pass

    return text


class Route:
    __slots__ = (
        "params",
        "data",
        "json",
        "headers",
        "use_id",
        "method",
        "path",
        "packed",
        "_base_url",
        "_url",
        "token_for",
    )

    BASE: ClassVar[str] = "https://api.twitch.tv/helix/"
    ID_BASE: ClassVar[str] = "https://id.twitch.tv/"

    def __init__(
        self,
        method: HTTPMethod,
        path: str,
        *,
        use_id: bool = False,
        **kwargs: Unpack[APIRequestKwargs],
    ) -> None:
        self.params: ParamMapping = kwargs.pop("params", {})
        self.json: dict[str, Any] = kwargs.get("json", {})
        self.headers: dict[str, str] = kwargs.get("headers", {})
        self.token_for: str = str(kwargs.get("token_for", ""))

        self.use_id = use_id
        self.method = method
        self.path = path

        self._base_url: str = ""
        self._url: str = self.build_url(duplicate_key=not use_id)

    def __str__(self) -> str:
        return str(self._url)

    def __repr__(self) -> str:
        return f"{self.method}[{self.base_url}]"

    def build_url(self, *, remove_none: bool = True, duplicate_key: bool = True) -> str:
        base = self.ID_BASE if self.use_id else self.BASE
        self.path = self.path.lstrip("/").rstrip("/")

        url: str = f"{base}{self.path}"
        self._base_url = url

        if not self.params:
            return url

        url += "?"

        # We expect a dict so keys should be unique...
        for key, value in copy.copy(self.params).items():
            if value is None:
                if remove_none:
                    del self.params[key]
                continue

            if isinstance(value, (str, int)):
                url += f'{key}={self.encode(str(value), safe="+", plus=True)}&'
            elif duplicate_key:
                for v in value:
                    url += f"{key}={self.encode(str(v), safe='+', plus=True)}&"
            else:
                joined: str = "+".join([self.encode(str(v), safe="+") for v in value])
                url += f"{key}={joined}&"

        return url.rstrip("&")

    @classmethod
    def encode(cls, value: str, /, safe: str = "", plus: bool = False) -> str:
        method = urllib.parse.quote_plus if plus else urllib.parse.quote
        unquote = urllib.parse.unquote_plus if plus else urllib.parse.unquote

        return method(value, safe=safe) if unquote(value) == value else value

    @property
    def url(self) -> str:
        return self._url

    @property
    def base_url(self) -> str:
        return self._base_url

    def update_params(self, params: ParamMapping, *, remove_none: bool = True) -> str:
        self.params.update(params)
        self._url = self.build_url(remove_none=remove_none)

        return self.url

    def update_headers(self, headers: dict[str, str]) -> None:
        self.headers.update(headers)


class HTTPAsyncIterator(Generic[T]):
    __slots__ = (
        "_http",
        "_route",
        "_cursor",
        "_first",
        "_max_results",
        "_converter",
        "_buffer",
    )

    def __init__(
        self,
        http: HTTPClient,
        route: Route,
        max_results: int | None = None,
        converter: PaginatedConverter[T] = None,
    ) -> None:
        self._http = http
        self._route = route

        self._cursor: str | None | bool = None
        self._first: int = int(route.params.get("first", 20))  # 20 is twitch default
        self._max_results: int | None = max_results

        if self._max_results is not None and self._max_results < self._first:
            self._first = self._max_results

        self._converter = converter or self._base_converter
        self._buffer: deque[T] = deque()

    async def _base_converter(self, data: Any) -> T:
        return data

    async def _call_next(self) -> None:
        if self._cursor is False:
            raise StopAsyncIteration

        if self._max_results is not None and self._max_results <= 0:
            raise StopAsyncIteration

        self._route.update_params({"after": self._cursor})
        data: RawResponse = await self._http.request_json(self._route)
        self._cursor = data.get("pagination", {}).get("cursor", False)

        try:
            inner: list[RawResponse] = data["data"]
        except KeyError as e:
            # TODO: Proper exception...
            raise ValueError('Expected "data" key not found.') from e

        for value in inner:
            if self._max_results is None:
                self._buffer.append(await self._do_conversion(value))
                continue

            self._max_results -= 1  # If this is causing issues, it's just pylance bugged/desynced...
            if self._max_results < 0:
                return

            self._buffer.append(await self._do_conversion(value))

    async def _do_conversion(self, data: RawResponse) -> T:
        return await self._converter(data)

    async def _flatten(self) -> list[T]:
        if not self._buffer:
            await self._call_next()

        return list(self._buffer)

    def __await__(self) -> Generator[Any, None, list[T]]:
        return self._flatten().__await__()

    def __aiter__(self) -> Self:
        return self

    async def __anext__(self) -> T:
        if not self._buffer:
            await self._call_next()

        try:
            data = self._buffer.popleft()
        except IndexError as e:
            raise StopAsyncIteration from e

        return data


class HTTPClient:
    __slots__ = ("_session", "_client_id", "user_agent")

    def __init__(self, session: aiohttp.ClientSession | None = None, *, client_id: str) -> None:
        self._session: aiohttp.ClientSession | None = session  # should be set on the first request
        self._client_id: str = client_id

        # User Agent...
        pyver = f"{sys.version_info[0]}.{sys.version_info[1]}"
        ua = "TwitchioClient (https://github.com/PythonistaGuild/TwitchIO {0}) Python/{1} aiohttp/{2}"
        self.user_agent: str = ua.format(__version__, pyver, aiohttp.__version__)

    @property
    def headers(self) -> dict[str, str]:
        return {"User-Agent": self.user_agent, "Client-ID": self._client_id}

    async def _init_session(self) -> None:
        if self._session and not self._session.closed:
            return

        logger.debug("Initialising a new session on %s.", self.__class__.__qualname__)

        session = self._session or aiohttp.ClientSession()
        session.headers.update(self.headers)

        self._session = session

    def clear(self) -> None:
        if self._session and self._session.closed:
            logger.debug(
                "Clearing %s session. A new session will be created on the next request.",
                self.__class__.__qualname__,
            )
            self._session = None

    async def close(self) -> None:
        if self._session and not self._session.closed:
            try:
                await self._session.close()
            except Exception as e:
                logger.debug(
                    "Ignoring exception caught while closing %s session: %s.",
                    self.__class__.__qualname__,
                    e,
                )

            self.clear()
            logger.debug("%s session closed successfully.", self.__class__.__qualname__)

    async def request(self, route: Route) -> RawResponse | str:
        await self._init_session()
        assert self._session is not None

        logger.debug("Attempting a request to %r with %s.", route, self.__class__.__qualname__)

        async with self._session.request(
            route.method,
            route.url,
            headers=route.headers,
            json=route.json or None,
        ) as resp:
            data: RawResponse | str = await json_or_text(resp)

            if resp.status >= 400:
                raise HTTPException(
                    f"Request {route} failed with status {resp.status}: {data}",
                    route=route,
                    status=resp.status,
                    extra=data,
                )

        return data

    async def request_json(self, route: Route) -> Any:
        data = await self.request(route)

        if isinstance(data, str):
            # TODO: Add a HTTPException here.
            raise TypeError("Expected JSON data, but received text data.")

        return data

    async def _request_asset_head(self, url: str) -> dict[str, str]:
        await self._init_session()
        assert self._session is not None

        logger.debug('Attempting to request headers for asset "%s" with %s.', url, self.__class__.__qualname__)

        async with self._session.head(url) as resp:
            if resp.status != 200:
                msg = f'Failed to header for asset at "{url}" with status {resp.status}.'
                raise HTTPException(msg, status=resp.status, extra=await resp.text())

            return dict(resp.headers)

    async def _request_asset(self, asset: Asset, *, chunk_size: int = 1024) -> AsyncIterator[bytes]:
        await self._init_session()
        assert self._session is not None

        logger.debug('Attempting a request to asset "%r" with %s.', asset, self.__class__.__qualname__)

        async with self._session.get(asset.url) as resp:
            if resp.status != 200:
                msg = f'Failed to get asset at "{asset.url}" with status {resp.status}.'
                raise HTTPException(msg, status=resp.status, extra=await resp.text())

            headers: dict[str, str] = dict(resp.headers)
            asset._set_ext(headers)

            async for chunk in resp.content.iter_chunked(chunk_size):
                yield chunk

    def request_paginated(
        self,
        route: Route,
        max_results: int | None = None,
        *,
        converter: PaginatedConverter[T] | None = None,
    ) -> HTTPAsyncIterator[T]:
        iterator: HTTPAsyncIterator[T] = HTTPAsyncIterator(self, route, max_results, converter=converter)
        return iterator

    async def get_global_chat_badges(self, token_for: str | None = None) -> GlobalChatBadgesResponse:
        route: Route = Route("GET", "chat/badges/global", token_for=token_for)
        return await self.request_json(route)

    async def get_chatters_color(
        self, user_ids: list[str | int], token_for: str | None = None
    ) -> UserChatColorResponse:
        params: dict[str, list[str | int]] = {"user_id": user_ids}
        route: Route = Route("GET", "chat/color", params=params, token_for=token_for)
        return await self.request_json(route)

    async def get_channels(
        self, broadcaster_ids: list[str | int], token_for: str | None = None
    ) -> ChannelInformationResponse:
        params = {"broadcaster_id": broadcaster_ids}
        route: Route = Route("GET", "channels", params=params, token_for=token_for)
        return await self.request_json(route)

    async def get_cheermotes(
        self, broadcaster_id: str | int | None, token_for: str | None = None
    ) -> CheermotesResponse:
        params = {"broadcaster_id": broadcaster_id}
        route: Route = Route("GET", "bits/cheermotes", params=params, token_for=token_for)
        return await self.request_json(route)

    async def get_channel_emotes(
        self, broadcaster_id: str | int, token_for: str | None = None
    ) -> ChannelEmotesResponse:
        params = {"broadcaster_id": broadcaster_id}
        route: Route = Route("GET", "chat/emotes", params=params, token_for=token_for)
        return await self.request_json(route)

    async def get_content_classification_labels(
        self, locale: str, token_for: str | None = None
    ) -> ContentClassificationLabelsResponse:
        params: dict[str, str] = {"locale": locale}
        route: Route = Route("GET", "content_classification_labels", params=params, token_for=token_for)
        return await self.request_json(route)

    async def get_global_emotes(self, token_for: str | None = None) -> GlobalEmotesResponse:
        route: Route = Route("GET", "chat/emotes/global", token_for=token_for)
        return await self.request_json(route)

    async def get_clips(
        self,
        first: int,
        broadcaster_id: str | None = None,
        game_id: str | None = None,
        clip_ids: list[str] | None = None,
        started_at: datetime.datetime | None = None,
        ended_at: datetime.datetime | None = None,
        is_featured: bool | None = None,
        token_for: str | None = None,
    ) -> HTTPAsyncIterator[Clip]:
        params: dict[str, str | int | list[str]] = {"first": first}
        if broadcaster_id:
            params["broadcaster_id"] = broadcaster_id
        elif game_id:
            params["game_id"] = game_id
        elif clip_ids:
            params["id"] = clip_ids

        if started_at:
            params["started_at"] = started_at.isoformat()
        if ended_at:
            params["ended_at"] = ended_at.isoformat()
        if is_featured is not None:
            params["is_featured"] = is_featured

        route: Route = Route("GET", "streams", params=params, token_for=token_for)

        async def converter(data: ClipsResponseData) -> Clip:
            return Clip(data, http=self)

        iterator: HTTPAsyncIterator[Clip] = self.request_paginated(route, converter=converter)
        return iterator

    async def get_extension_transactions(
        self, extension_id: str, ids: list[str] | None = None, first: int = 20
    ) -> HTTPAsyncIterator[ExtensionTransaction]:
        params: dict[str, str | int | list[str]] = {"extension_id": extension_id, "first": first}
        if ids:
            params["id"] = ids
        route: Route = Route("GET", "extensions/transactions", params=params)

        async def converter(data: ExtensionTransactionsResponseData) -> ExtensionTransaction:
            return ExtensionTransaction(data, http=self)

        iterator: HTTPAsyncIterator[ExtensionTransaction] = self.request_paginated(route, converter=converter)
        return iterator

    async def get_streams(
        self,
        first: int,
        user_ids: list[int | str] | None = None,
        game_ids: list[int | str] | None = None,
        user_logins: list[int | str] | None = None,
        languages: list[str] | None = None,
        token_for: str | None = None,
        type: Literal["all", "live"] = "all",
    ) -> HTTPAsyncIterator[Stream]:
        params: dict[str, str | int | Sequence[str | int]] = {
            "type": type,
            "first": first,
        }

        if user_ids is not None:
            params["user_id"] = user_ids
        if game_ids is not None:
            params["game_ids"] = game_ids
        if user_logins is not None:
            params["user_login"] = user_logins
        if languages is not None:
            params["language"] = languages

        route: Route = Route("GET", "streams", params=params, token_for=token_for)

        async def converter(data: StreamsResponseData) -> Stream:
            return Stream(data, http=self)

        iterator: HTTPAsyncIterator[Stream] = self.request_paginated(route, converter=converter)
        return iterator

    async def get_search_categories(
        self, query: str, first: int, token_for: str | None = None
    ) -> HTTPAsyncIterator[Game]:
        params: dict[str, str | int | Sequence[str | int]] = {
            "query": query,
            "first": first,
        }
        route: Route = Route("GET", "search/categories", params=params, token_for=token_for)

        async def converter(data: GamesResponseData) -> Game:
            return Game(data, http=self)

        iterator: HTTPAsyncIterator[Game] = self.request_paginated(route, converter=converter)
        return iterator

    async def get_search_channels(
        self, query: str, first: int, live: bool = False, token_for: str | None = None
    ) -> HTTPAsyncIterator[SearchChannel]:
        params: dict[str, str | int] = {"query": query, "live": live, "first": first}
        route: Route = Route("GET", "search/channels", params=params, token_for=token_for)

        async def converter(data: SearchChannelsResponseData) -> SearchChannel:
            return SearchChannel(data, http=self)

        iterator: HTTPAsyncIterator[SearchChannel] = self.request_paginated(route, converter=converter)
        return iterator

    async def get_teams(
        self,
        team_name: str | None = None,
        team_id: str | None = None,
        token_for: str | None = None,
    ) -> TeamsResponse:
        params: dict[str, str] = {}

        if team_name:
            params = params = {"name": team_name}
        elif team_id:
            params = {"id": team_id}

        route: Route = Route("GET", "teams", params=params, token_for=token_for)

        return await self.request_json(route)

    async def get_games(
        self,
        names: list[str] | None = None,
        ids: list[str] | None = None,
        igdb_ids: list[str] | None = None,
        token_for: str | None = None,
    ) -> GamesResponse:
        params: dict[str, list[str]] = {}

        if names is not None:
            params["name"] = names
        if ids is not None:
            params["id"] = ids
        if igdb_ids is not None:
            params["igdb_id"] = igdb_ids

        route: Route = Route("GET", "games", params=params, token_for=token_for)

        return await self.request_json(route)

    async def get_top_games(self, first: int, token_for: str | None = None) -> HTTPAsyncIterator[Game]:
        params: dict[str, int] = {"first": first}
        route: Route = Route("GET", "games/top", params=params, token_for=token_for)

        async def converter(data: TopGamesResponseData) -> Game:
            return Game(data, http=self)

        iterator: HTTPAsyncIterator[Game] = self.request_paginated(route, converter=converter)
        return iterator

    async def get_videos(
        self,
        ids: list[str | int] | None = None,
        user_id: str | int | None = None,
        game_id: str | int | None = None,
        language: str | None = None,
        period: Literal["all", "day", "month", "week"] = "all",
        sort: Literal["time", "trending", "views"] = "time",
        type: Literal["all", "archive", "highlight", "upload"] = "all",
        first: int = 20,
        token_for: str | None = None,
    ) -> HTTPAsyncIterator[Video]:
        params: dict[str, int | str | list[str | int]] = {"first": first, "period": period, "sort": sort, "type": type}

        if ids is not None:
            params["id"] = ids
        if user_id is not None:
            params["user_id"] = user_id
        if game_id is not None:
            params["game_id"] = game_id
        if language is not None:
            params["language"] = language

        route = Route("GET", "videos", params=params, token_for=token_for)

        async def converter(data: VideosResponseData) -> Video:
            return Video(data, http=self)

        iterator = self.request_paginated(route, converter=converter)
        return iterator

    async def delete_videos(self, ids: list[str | int], token_for: str) -> DeleteVideosResponse:
        params = {"id": ids}
        route: Route = Route("DELETE", "videos", params=params, token_for=token_for)
        return await self.request_json(route)

    async def create_conduit(self, shard_count: int, /) -> ConduitPayload:
        params = {"shard_count": shard_count}
        route: Route = Route("POST", "eventsub/conduits", params=params)
        return await self.request_json(route)

    async def get_conduits(self) -> ConduitPayload:
        route = Route("GET", "eventsub/conduits")
        return await self.request_json(route)

    async def get_conduit_shards(self, conduit_id: str, /) -> HTTPAsyncIterator[Shard]:
        params = {"conduit_id": conduit_id}

        async def converter(data: ShardData) -> Shard:
            return Shard(data=data)

        route: Route = Route("GET", "eventsub/conduits/shards", params=params)
        iterator = self.request_paginated(route, converter=converter)
        return iterator

    async def update_conduit_shards(self, conduit_id: str, /, *, shards: list[ShardUpdateRequest], session_id: str | None = None,) -> ...:
        # TODO: Type for return...

        params = {"conduit_id": conduit_id}
        body = {"shards": shards}

        route = Route("PATCH", "eventsub/conduits/shards", params=params, json=body)
        return await self.request_json(route)

    async def start_commercial(self, broadcaster_id: str | int, length: int, token_for: str) -> StartCommercialResponse:
        data = {"broadcaster_id": broadcaster_id, "length": length}
        route: Route = Route("POST", "channels/commercial", json=data, token_for=token_for)
        return await self.request_json(route)

    async def get_ad_schedule(self, broadcaster_id: str | int, token_for: str) -> AdScheduleResponse:
        params = {"broadcaster_id": broadcaster_id}
        route: Route = Route("GET", "channels/ads", params=params, token_for=token_for)
        return await self.request_json(route)

    async def post_snooze_ad(self, broadcaster_id: str | int, token_for: str) -> SnoozeNextAdResponse:
        params = {"broadcaster_id": broadcaster_id}
        route: Route = Route("POST", "channels/ads/snooze", params=params, token_for=token_for)
        return await self.request_json(route)

    async def get_bits_leaderboard(
        self,
        broadcaster_id: str | int,
        token_for: str,
        count: int = 10,
        period: Literal["day", "week", "month", "year", "all"] = "all",
        started_at: datetime.datetime | None = None,
        user_id: str | int | None = None,
    ) -> BitsLeaderboardResponse:
        params: dict[str, str | int | datetime.datetime] = {
            "broadcaster_id": broadcaster_id,
            "count": count,
            "period": period,
        }

        if started_at is not None:
            params["started_at"] = started_at
        if user_id:
            params["user_id"] = user_id

        route: Route = Route("GET", "bits/leaderboard", params=params, token_for=token_for)
        return await self.request_json(route)

    async def patch_channel_info(
        self,
        broadcaster_id: str | int,
        token_for: str,
        game_id: str | int | None = None,
        language: str | None = None,
        title: str | None = None,
        delay: int | None = None,
        tags: list[str] | None = None,
        branded_content: bool | None = None,
        classification_labels: list[dict[str, bool]] | None = None,
    ) -> None:
        params = {"broadcaster_id": broadcaster_id}

        data: dict[str, str | int | list[str] | list[dict[str, str | bool]]] = {
            k: v
            for k, v in {
                "game_id": game_id,
                "broadcaster_language": language,
                "title": title,
                "delay": delay,
                "tags": tags,
                "is_branded_content": branded_content,
            }.items()
            if v is not None
        }

        if classification_labels is not None:
            converted_labels = [
                {"id": label, "is_enabled": enabled}
                for item in classification_labels
                for label, enabled in item.items()
            ]
            data["content_classification_labels"] = converted_labels

        route: Route = Route("PATCH", "channels", params=params, json=data, token_for=token_for)
        return await self.request_json(route)

    async def get_channel_editors(self, broadcaster_id: str | int, token_for: str) -> ChannelEditorsResponse:
        params = {"broadcaster_id": broadcaster_id}
        route: Route = Route("GET", "channels/editors", params=params, token_for=token_for)
        return await self.request_json(route)

    async def get_followed_channels(
        self,
        user_id: str | int,
        token_for: str,
        broadcaster_id: str | int | None = None,
        first: int = 20,
    ) -> HTTPAsyncIterator[ChannelFollowedEvent]:
        params = {"first": first, "user_id": user_id}

        if broadcaster_id is not None:
            params["broadcaster_id"] = broadcaster_id

        route = Route("GET", "channels/followed", params=params, token_for=token_for)

        async def converter(data: FollowedChannelsResponseData) -> ChannelFollowedEvent:
            return ChannelFollowedEvent(data, http=self)

        iterator = self.request_paginated(route, converter=converter)
        return iterator

    async def get_channel_followers(
        self,
        broadcaster_id: str | int,
        token_for: str,
        user_id: str | int | None = None,
        first: int = 20,
    ) -> HTTPAsyncIterator[ChannelFollowerEvent]:
        params = {"first": first, "broadcaster_id": broadcaster_id}

        if user_id is not None:
            params["user_id"] = broadcaster_id

        route = Route("GET", "channels/followers", params=params, token_for=token_for)

        async def converter(data: ChannelFollowersResponseData) -> ChannelFollowerEvent:
            return ChannelFollowerEvent(data, http=self)

        iterator = self.request_paginated(route, converter=converter)
        return iterator

    async def post_create_custom_reward(self, broadcaster_id: str, token_for: str) -> CustomRewardsResponse:
        params = {"broadcaster_id": broadcaster_id}
        route: Route = Route("POST", "channel_points/custom_rewards", params=params, token_for=token_for)
        return await self.request_json(route)

    async def delete_custom_reward(self, broadcaster_id: str, reward_id: str, token_for: str) -> None:
        params = {"broadcaster_id": broadcaster_id, "id": reward_id}
        route: Route = Route("DELETE", "channel_points/custom_rewards", params=params, token_for=token_for)
        return await self.request_json(route)

    async def get_custom_reward(
        self, broadcaster_id: str, token_for: str, reward_id: str | None = None, manageable: bool = False
    ) -> CustomRewardsResponse:
        params = {"broadcaster_id": broadcaster_id, "only_manageable_rewards": manageable}

        if reward_id is not None:
            params["id"] = reward_id

        route: Route = Route("GET", "channel_points/custom_rewards", params=params, token_for=token_for)
        return await self.request_json(route)
