"""Support for MediaTracker calendars."""
from __future__ import annotations
import logging
from datetime import date, datetime, timedelta
from homeassistant.util import dt
import json

from pymediatracker.objects.calendar import MediaTrackerCalendar
from pymediatracker.exceptions import MediaTrackerException

from homeassistant.components.calendar import CalendarEntity, CalendarEvent
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import MediaTrackerEntity
from .const import DOMAIN, EPISODE_SPOILERS, EXPAND_DETAILS

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up MediaTracker calendars based on a config entry."""
    coordinator: DataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]

    entities = []

    for entity in coordinator.data.entities:
        entities.append(MediaTrackerCalendar(coordinator, entry, entity))

    async_add_entities(entities, True)


class MediaTrackerCalendar(MediaTrackerEntity, CalendarEntity):
    """Define a MediaTracker calendar."""

    def __init__(
        self,
        coordinator: DataUpdateCoordinator,
        entry: ConfigEntry,
        entity: str,
    ) -> None:
        """Initialize the MediaTracker entity."""
        super().__init__(coordinator)
        self._entry = entry
        self._entity = entity
        self._attr_unique_id = self._entity["key"]
        self._attr_name = self._entity["name"]
        self._event: CalendarEvent | None = None

    @property
    def event(self) -> CalendarEvent | None:
        """Return the next upcoming event."""
        return self._event

    async def async_get_events(
        self,
        hass: HomeAssistant,
        start_date: datetime,
        end_date: datetime,
    ) -> list[CalendarEvent]:
        """Return calendar events within a datetime range."""
        events = []

        start = start_date.strftime("%Y-%m-%d")
        end = end_date.strftime("%Y-%m-%d")

        for calendar_item in await self.coordinator.data.get_calendar_items(start, end):
            if self._attr_unique_id in calendar_item.mediaItem.mediaType:
                event = await self.get_calendar_item(calendar_item)
                if event is not None:
                    events.append(event)

        return events

    async def get_calendar_item(self, calendar_item) -> object | None:
        """Return formatted calendar entry based on media type."""
        media = calendar_item.mediaItem
        media_details = await self.coordinator.data.get_item(media.id)

        media_title = media.title
        media_release = get_release_date(calendar_item.releaseDate)
        media_description = ""
        media_episode_title = ""
        media_episode_nr = ""

        media_extra_data = {
            'host': self._entry.data.get("host"),
            'token': self._entry.data.get("token"),
            'poster': media_details.poster,
            'backdrop': media_details.backdrop,
            'source': media_details.source,
            'color': "#dfdfdf"
        }

        if EXPAND_DETAILS is True:
            media_description = media_details.overview

        # if media.mediaType == "audiobook":
        # if media.mediaType == "book":
        # if media.mediaType == "video_game":
        # if media.mediaType == "movie":

        if media.mediaType == "tv":
            media_title = f"{media.title}"
            media_release = get_release_date(calendar_item.releaseDate)

            if calendar_item.episode.episodeNumber is not None:
                if calendar_item.episode.title and EPISODE_SPOILERS is True:
                    media_episode_title = f" - {calendar_item.episode.title}"

                if calendar_item.episode.episodeNumber is not None:
                    media_episode_nr = (
                        f" S{calendar_item.episode.seasonNumber:02d}E{calendar_item.episode.episodeNumber:02d}"
                    )

                media_title = "".join(
                    [media_title, media_episode_nr, media_episode_title])
                media_release = get_release_date(
                    calendar_item.episode.releaseDate)

                if EXPAND_DETAILS is True:
                    media_description = get_episode_description(media_details.seasons, calendar_item.episode.id)


        return CalendarEvent(
            summary=media_title,
            description=media_description,
            location=json.dumps(media_extra_data),
            start=media_release,
            end=media_release + timedelta(hours=2),
        )


def get_episode_description(seasons, episode_id):
    """Find season episode and return its description"""
    episode = next(
        (
            e
            for season in seasons
            for e in season.episodes
            if e.id == episode_id
        ),
        None
    )

    if episode:
        episode_description = episode.description
        return episode_description
    else:
        return None


def get_release_date(due) -> datetime | date | None:
    """Return formatted release date for media tracker item."""
    if due is not None:
        if due.endswith("000Z"):
            start = dt.parse_datetime(due.replace("Z", "+00:00"))
            if not start:
                return None

            return dt.as_local(start)

        if check_date(due):
            start = dt.parse_date(due)
            return dt.start_of_local_day(start)

    return None


def check_date(date_str):
    """Check a date string for bare minimum"""
    try:
        if date_str != datetime.strptime(date_str, "%Y-%m-%d").strftime("%Y-%m-%d"):
            raise ValueError
        return True
    except ValueError:
        return False
