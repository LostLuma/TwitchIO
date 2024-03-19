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

from typing import TYPE_CHECKING

from .assets import Asset
from .user import PartialUser
from .utils import parse_timestamp


if TYPE_CHECKING:
    import datetime

    from .http import HTTPClient
    from .types_.responses import RawResponse

__all__ = (
    "ChatterColor",
    "ChannelInfo",
    "CheerEmoteTier",
    "CheerEmote",
    "Clip",
    "ContentClassificationLabel",
    "Game",
    "GlobalEmote",
    "SearchChannel",
    "Stream",
    "Team",
)


class ChatterColor:
    """
    Represents chatters current name color.

    Attributes
    -----------
    user: :class:`~twitchio.PartialUser`
        PartialUser of the chatter.
    color: :class:`str`
        The hex color code of the chatter's name.
    """

    __slots__ = ("user", "color")

    def __init__(self, data: RawResponse) -> None:
        self.user = PartialUser(data["user_id"], data["user_login"])
        self.color: str = data["color"]

    def __repr__(self) -> str:
        return f"<ChatterColor user={self.user} color={self.color}>"


class ChannelInfo:
    """
    Represents a channel's current information

    Attributes
    -----------
    user: :class:`~twitchio.PartialUser`
        The user whose channel information was requested.
    game_id: :class:`int`
        Current game ID being played on the channel.
    game_name: :class:`str`
        Name of the game being played on the channel.
    title: :class:`str`
        Title of the stream.
    language: :class:`str`
        Language of the channel.
    delay: :class:`int`
        Stream delay in seconds.
        This defaults to 0 if the broadcaster_id does not match the user access token.
    tags: List[:class:`str`]
        The tags applied to the channel.
    content_classification_labels: List[:class:`str`]
        The CCLs applied to the channel.
    is_branded_content: :class:`bool`
        Boolean flag indicating if the channel has branded content.
    """

    __slots__ = (
        "user",
        "game_id",
        "game_name",
        "title",
        "language",
        "delay",
        "tags",
        "content_classification_labels",
        "is_branded_content",
    )

    def __init__(self, data: RawResponse) -> None:
        self.user = PartialUser(data["broadcaster_id"], data["broadcaster_name"])
        self.game_id: int = data["game_id"]
        self.game_name: str = data["game_name"]
        self.title: str = data["title"]
        self.language: str = data["broadcaster_language"]
        self.delay: int = data["delay"]
        self.tags: list[str] = data["tags"]
        self.content_classification_labels: list[str] = data["content_classification_labels"]
        self.is_branded_content: bool = data["is_branded_content"]

    def __repr__(self) -> str:
        return f"<ChannelInfo user={self.user} game_id={self.game_id} game_name={self.game_name} title={self.title} language={self.language} delay={self.delay}>"


class Clip:
    """
    Represents a Twitch Clip

    Attributes
    -----------
    id: :class:`str`
        The ID of the clip.
    url: :class:`str`
        The URL of the clip.
    embed_url: :class:`str`
        The URL to embed the clip with.
    broadcaster: :class:`~twitchio.PartialUser`
        The user whose channel the clip was created on.
    creator: :class:`~twitchio.PartialUser`
        The user who created the clip.
    video_id: :class:`str`
        The ID of the video the clip is sourced from.
    game_id: :class:`str`
        The ID of the game that was being played when the clip was created.
    language: :class:`str`
        The language, in an `ISO 639-1 <https://en.wikipedia.org/wiki/List_of_ISO_639-1_codes>`_ format, of the stream when the clip was created.
    title: :class:`str`
        The title of the clip.
    views: :class:`int`
        The amount of views this clip has.
    created_at: :class:`datetime.datetime`
        When the clip was created.
    thumbnail_url: :class:`str`
        The url of the clip thumbnail.
    is_featured: :class:`bool`
        Indicates if the clip is featured or not.
    """

    __slots__ = (
        "id",
        "url",
        "embed_url",
        "broadcaster",
        "creator",
        "video_id",
        "game_id",
        "language",
        "title",
        "views",
        "created_at",
        "thumbnail_url",
        "is_featured",
    )

    def __init__(self, data: RawResponse) -> None:
        self.id: str = data["id"]
        self.url: str = data["url"]
        self.embed_url: str = data["embed_url"]
        self.broadcaster: PartialUser = PartialUser(data["broadcaster_id"], data["broadcaster_name"])
        self.creator: PartialUser = PartialUser(data["creator_id"], data["creator_name"])
        self.video_id: str = data["video_id"]
        self.game_id: str = data["game_id"]
        self.language: str = data["language"]
        self.title: str = data["title"]
        self.views: int = data["view_count"]
        self.created_at: datetime.datetime = parse_timestamp(data["created_at"])
        self.thumbnail_url: str = data["thumbnail_url"]
        self.is_featured: bool = data["is_featured"]

    def __repr__(self) -> str:
        return f"<Clip id={self.id} broadcaster={self.broadcaster} creator={self.creator}>"


class CheerEmoteTier:
    """
    Represents a Cheer Emote tier.

    Attributes
    -----------
    min_bits: :class:`int`
        The minimum bits for the tier
    id: :class:`str`
        The ID of the tier
    colour: :class:`str`
        The colour of the tier
    images: :class:`dict`
        contains two dicts, ``light`` and ``dark``. Each item will have an ``animated`` and ``static`` item,
        which will contain yet another dict, with sizes ``1``, ``1.5``, ``2``, ``3``, and ``4``.
        Ex. ``cheeremotetier.images["light"]["animated"]["1"]``
    can_cheer: :class:`bool`
        Indicates whether emote information is accessible to users.
    show_in_bits_card: :class`bool`
        Indicates whether twitch hides the emote from the bits card.
    """

    __slots__ = "min_bits", "id", "color", "images", "can_cheer", "show_in_bits_card"

    def __init__(self, data: RawResponse) -> None:
        self.min_bits: int = data["min_bits"]
        self.id: str = data["id"]
        self.color: str = data["color"]
        self.images = data["images"]  # TODO types
        self.can_cheer: bool = data["can_cheer"]
        self.show_in_bits_card: bool = data["show_in_bits_card"]

    def __repr__(self) -> str:
        return f"<CheerEmoteTier id={self.id} min_bits={self.min_bits}>"


class CheerEmote:
    """
    Represents a Cheer Emote

    Attributes
    -----------
    prefix: :class:`str`
        The string used to Cheer that precedes the Bits amount.
    tiers: :class:`~CheerEmoteTier`
        The tiers this Cheer Emote has
    type: :class:`str`
        Shows whether the emote is ``global_first_party``, ``global_third_party``, ``channel_custom``, ``display_only``, or ``sponsored``.
    order: :class:`str`
        Order of the emotes as shown in the bits card, in ascending order.
    last_updated :class:`datetime.datetime`
        The date this cheermote was last updated.
    charitable: :class:`bool`
        Indicates whether this emote provides a charity contribution match during charity campaigns.
    """

    __slots__ = "_http", "prefix", "tiers", "type", "order", "last_updated", "charitable"

    def __init__(self, data: RawResponse) -> None:
        self.prefix: str = data["prefix"]
        self.tiers = [CheerEmoteTier(d) for d in data["tiers"]]
        self.type: str = data["type"]
        self.order: str = data["order"]
        self.last_updated = parse_timestamp(data["last_updated"])
        self.charitable: bool = data["is_charitable"]

    def __repr__(self) -> str:
        return f"<CheerEmote prefix={self.prefix} type={self.type} order={self.order}>"


class ContentClassificationLabel:
    """
    Represents a Content Classification Label.

    Attributes
    -----------
    id: :class:`str`
        Unique identifier for the CCL.
    description: :class:`str`
        Localized description of the CCL.
    name: :class:`str`
        Localized name of the CCL.
    """

    __slots__ = ("id", "description", "name")

    def __init__(self, data: RawResponse) -> None:
        self.id: str = data["id"]
        self.description: str = data["description"]
        self.name: str = data["name"]

    def __repr__(self) -> str:
        return f"<ContentClassificationLabel id={self.id}>"


class Game:
    """
    Represents a Game on twitch

    Attributes
    -----------
    id: :class:`str`
        Game ID.
    name: :class:`str`
        Game name.
    box_art: :class:`str`
        Template URL for the game's box art.
    igdb_id: Optional[:class:`str`]
        The IGDB ID of the game. If this is not available to Twitch it will return None
    """

    __slots__ = "id", "name", "box_art", "igdb_id"

    def __init__(self, data: RawResponse, *, http: HTTPClient) -> None:
        self.id: str = data["id"]
        self.name: str = data["name"]
        self.igdb_id: str | None = data.get("igdb_id")
        self.box_art: Asset = Asset(data["box_art_url"], http=http, dimensions=(1080, 1440))

    def __repr__(self) -> str:
        return f"<Game id={self.id} name={self.name}>"


class GlobalEmote:
    """
    Represents a Global Emote

    Attributes
    -----------
    id: :class:`str`
        The ID of the emote.
    name: :class:`str`
        The name of the emote.
    images: :class:`dict`
        Contains the image URLs for the emote. These image URLs will always provide a static (i.e., non-animated) emote image with a light background.
    format: List[:class:`str`]
        The formats that the emote is available in.
    scale: List[:class:`str`]
        The sizes that the emote is available in.
    theme_mode: List[:class:`str`]
        The background themes that the emote is available in.
    """

    __slots__ = ("id", "name", "images", "format", "scale", "theme_mode", "template")

    def __init__(self, data: RawResponse) -> None:
        self.id: str = data["id"]
        self.name: str = data["name"]
        self.images: dict[str, str] = data["images"]
        self.format: list[str] = data["format"]
        self.scale: list[str] = data["scale"]
        self.theme_mode: list[str] = data["theme_mode"]

    def __repr__(self) -> str:
        return f"<GlobalEmote id={self.id} name={self.name}"


class SearchChannel:
    __slots__ = (
        "id",
        "game_id",
        "name",
        "display_name",
        "language",
        "title",
        "thumbnail_url",
        "live",
        "started_at",
        "tag_ids",
    )

    def __init__(self, data: RawResponse) -> None:
        self.display_name: str = data["display_name"]
        self.name: str = data["broadcaster_login"]
        self.id: str = data["id"]
        self.game_id: str = data["game_id"]
        self.title: str = data["title"]
        self.thumbnail_url: str = data["thumbnail_url"]
        self.language: str = data["broadcaster_language"]
        self.live: bool = data["is_live"]
        self.started_at = parse_timestamp(data["started_at"]) if self.live else None
        self.tag_ids: list[str] = data["tag_ids"]

    def __repr__(self) -> str:
        return f"<SearchUser name={self.name} title={self.title} live={self.live}>"


class Stream:
    """
    Represents a Stream

    Attributes
    -----------
    id: :class:`int`
        The current stream ID.
    user: :class:`~twitchio.PartialUser`
        The user who is streaming.
    game_id: :class:`str`
        Current game ID being played on the channel.
    game_name: :class:`str`
        Name of the game being played on the channel.
    type: :class:`str`
        Whether the stream is "live" or not.
    title: :class:`str`
        Title of the stream.
    viewer_count: :class:`int`
        Current viewer count of the stream
    started_at: :class:`datetime.datetime`
        UTC timestamp of when the stream started.
    language: :class:`str`
        Language of the channel.
    thumbnail_url: :class:`str`
        Thumbnail URL of the stream.
    tag_ids: List[:class:`str`]
        Tag IDs that apply to the stream.

        .. warning::

            This field will be deprecated by twitch in 2023.

    is_mature: :class:`bool`
        Indicates whether the stream is intended for mature audience.
    tags: List[:class:`str`]
        The tags applied to the channel.
    """

    __slots__ = (
        "id",
        "user",
        "game_id",
        "game_name",
        "type",
        "title",
        "viewer_count",
        "started_at",
        "language",
        "thumbnail_url",
        "tag_ids",
        "is_mature",
        "tags",
    )

    def __init__(self, data: RawResponse) -> None:
        self.id: int = data["id"]
        self.user = PartialUser(data["user_id"], data["user_name"])
        self.game_id: str = data["game_id"]
        self.game_name: str = data["game_name"]
        self.type: str = data["type"]
        self.title: str = data["title"]
        self.viewer_count: int = data["viewer_count"]
        self.started_at = parse_timestamp(data["started_at"])
        self.language: str = data["language"]
        self.thumbnail_url: str = data["thumbnail_url"]
        self.tag_ids: list[str] = data["tag_ids"] or []
        self.is_mature: bool = data["is_mature"]
        self.tags: list[str] = data["tags"]

    def __repr__(self) -> str:
        return f"<Stream id={self.id} user={self.user} title={self.title} started_at={self.started_at}>"


class Team:
    """
    Represents information for a specific Twitch Team

    Attributes
    -----------
    users: list[:class:`~twitchio.PartialUser`]
        List of users in the specified Team.
    background_image_url: :class:`str`
        URL for the Team background image.
    banner: :class:`str`
        URL for the Team banner.
    created_at: :class:`datetime.datetime`
        Date and time the Team was created.
    updated_at: :class:`datetime.datetime`
        Date and time the Team was last updated.
    info: :class:`str`
        Team description.
    thumbnail_url: :class:`str`
        Image URL for the Team logo.
    team_name: :class:`str`
        Team name.
    team_display_name: :class:`str`
        Team display name.
    id: :class:`str`
        Team ID.
    """

    __slots__ = (
        "users",
        "background_image_url",
        "banner",
        "created_at",
        "updated_at",
        "info",
        "thumbnail_url",
        "team_name",
        "team_display_name",
        "id",
    )

    def __init__(self, data: RawResponse) -> None:
        data = data["data"][0]
        self.users: list[PartialUser] = [PartialUser(x["user_id"], x["user_login"]) for x in data["users"]]
        self.background_image_url: str = data["background_image_url"]
        self.banner: str = data["banner"]
        self.created_at: datetime.datetime = parse_timestamp(data["created_at"])
        self.updated_at: datetime.datetime = parse_timestamp(data["updated_at"])
        self.info: str = data["info"]
        self.thumbnail_url: str = data["thumbnail_url"]
        self.team_name: str = data["team_name"]
        self.team_display_name: str = data["team_display_name"]
        self.id: int = data["id"]

    def __repr__(self) -> str:
        return f"<Team users={self.users} team_name={self.team_name} team_display_name={self.team_display_name} id={self.id} created_at={self.created_at}>"
