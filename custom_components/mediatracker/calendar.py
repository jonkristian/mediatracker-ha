"""Support for MediaTracker calendars."""
from __future__ import annotations
import logging
from datetime import date, datetime, timedelta
from homeassistant.util import dt

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
        entities.append(MediaTrackerCalendar(coordinator, entity))

    async_add_entities(entities, True)


class MediaTrackerCalendar(MediaTrackerEntity, CalendarEntity):
    """Define a MediaTracker calendar."""

    def __init__(
        self,
        coordinator: DataUpdateCoordinator,
        entity: str,
    ) -> None:
        """Initialize the MediaTracker entity."""
        super().__init__(coordinator)
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
                event = await get_calendar_item(self.coordinator.data, calendar_item)
                if event is not None:
                    events.append(event)

        return events


async def get_calendar_item(client, calendar_item) -> object | None:
    """Return formatted calendar entry based on media type."""
    media = calendar_item.mediaItem

    media_title = media.title
    media_release = get_release_date(calendar_item.releaseDate)
    media_poster = ""
    media_description = ""
    media_episode_title = ""
    media_episode_nr = ""

    #if media.mediaType == "audiobook":
    #if media.mediaType == "book":
    #if media.mediaType == "video_game":
    #if media.mediaType == "movie":

    if media.mediaType == "tv":
        media_title = f"{media.title}"
        media_release = get_release_date(calendar_item.releaseDate)

        if EXPAND_DETAILS is True:
            item_details = await client.get_item(media.id)
            media_description = item_details.overview
            media_poster = item_details.poster

        if calendar_item.episode.episodeNumber is not None:
            if calendar_item.episode.title and EPISODE_SPOILERS is True:
                media_episode_title = f" - {calendar_item.episode.title}"

            if calendar_item.episode.episodeNumber is not None:
                media_episode_nr = (
                    f" S{calendar_item.episode.seasonNumber:02d}E{calendar_item.episode.episodeNumber:02d}"
                )

            media_title = "".join([media_title, media_episode_nr, media_episode_title])
            media_release = get_release_date(calendar_item.episode.releaseDate)

    return CalendarEvent(
        summary=media_title,
        description=media_description,
        location=media_poster,
        start=media_release,
        end=media_release + timedelta(hours=2),
    )


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
