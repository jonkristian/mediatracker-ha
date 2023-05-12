"""Support for MediaTracker calendars."""
from __future__ import annotations
import logging
from datetime import date, datetime, timedelta
from homeassistant.util import dt

from homeassistant.components.calendar import CalendarEntity, CalendarEvent
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import MediaTrackerEntity
from .const import DOMAIN, AVOID_EPISODE_SPOILERS

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
        entity: MediaTrackerEntity,
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
        for item in self.coordinator.data.items:
            if self._attr_unique_id in item.mediaType:
                media = get_media(item)

                if item is not None:
                    event = CalendarEvent(
                        summary=media["title"],
                        description=media["description"],
                        start=media["release"],
                        end=media["release"] + timedelta(hours=2),
                    )

                    events.append(event)

        return events


def get_release_date(due) -> datetime | date | None:
    """Return formatted release date for media tracker item."""

    if due.endswith("000Z"):
        start = dt.parse_datetime(due.replace("Z", "+00:00"))
        if not start:
            return None

        return dt.as_local(start)

    if due is not None:
        start = dt.parse_date(due)
        return dt.start_of_local_day(start)

    return None


def get_media(item) -> object | None:
    """Return formatted calendar entry based on media type."""
    if item.mediaType is None:
        return

    media_title = ""
    media_episode_title = ""
    media_episode_nr = ""
    media_description = ""
    media_release = ""

    if item.mediaType == "audiobook":
        media_title = item.title
        media_description = item.overview
        media_release = get_release_date(item.releaseDate)

    if item.mediaType == "book":
        media_title = item.title
        media_description = item.overview
        media_release = get_release_date(item.releaseDate)

    if item.mediaType == "video_game":
        media_title = item.title
        media_description = item.overview
        media_release = get_release_date(item.releaseDate)

    if item.mediaType == "movie":
        media_title = item.title
        media_description = item.overview
        media_release = get_release_date(item.releaseDate)

    if item.mediaType == "tv":
        media_title = f"{item.title}"
        media_description = item.overview
        media_release = get_release_date(item.releaseDate)

        if item.upcomingEpisode:
            episode = item.upcomingEpisode
            if episode.title and AVOID_EPISODE_SPOILERS is False:
                media_episode_title = f" - {episode.title}"

            if episode.episodeNumber is not None:
                media_episode_nr = (
                    f" - S{episode.episodeNumber:02d}E{episode.seasonNumber:02d}"
                )

            media_title = "".join([media_title, media_episode_nr, media_episode_title])
            media_description = episode.description
            media_release = get_release_date(episode.releaseDate)

    return {
        "title": media_title,
        "description": media_description,
        "release": media_release,
    }
