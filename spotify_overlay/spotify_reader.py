import asyncio
import time
from winrt.windows.media.control import GlobalSystemMediaTransportControlsSessionManager as Manager
from winrt.windows.media.control import GlobalSystemMediaTransportControlsSessionPlaybackStatus as Status
from winrt.windows.storage.streams import DataReader


async def poll(state, lock):
    manager = await Manager.request_async()
    previous = None
    cover = b""
    last_position = None
    position_revision = 0
    while True:
        try:
            session = next((s for s in manager.get_sessions() if "spotify" in s.source_app_user_model_id.lower()), None)
            if session:
                media = await session.try_get_media_properties_async()
                timeline = session.get_timeline_properties()
                track = (media.title, media.artist, media.album_title)
                position = max(0, timeline.position.total_seconds())
                if track != previous or last_position is None or abs(position - last_position) >= 0.1:
                    position_revision += 1
                    last_position = position
                if track != previous:
                    cover = b""
                    if media.thumbnail:
                        stream = await media.thumbnail.open_read_async()
                        try:
                            size = min(int(stream.size), 5_000_000)
                            reader = DataReader(stream)
                            try:
                                await reader.load_async(size)
                                buffer = bytearray(size)
                                reader.read_bytes(buffer)
                                cover = bytes(buffer)
                            finally:
                                reader.close()
                        finally:
                            stream.close()
                    previous = track
                update = dict(title=media.title or "—", artist=media.artist or "", cover=cover,
                              track=track,
                              elapsed=position,
                              position_revision=position_revision,
                              duration=max(0, (timeline.end_time - timeline.start_time).total_seconds()),
                              playing=session.get_playback_info().playback_status == Status.PLAYING,
                              stamp=time.monotonic())
            else:
                previous, cover = None, b""
                last_position = None
                update = dict(title="En attente de Spotify...", artist="", cover=b"", track=None,
                              elapsed=0.0, duration=0.0, playing=False, stamp=time.monotonic(),
                              position_revision=position_revision)
            with lock:
                state.update(update)
        except Exception as exc:
            print("[Spotify] lecture impossible:", exc)
        await asyncio.sleep(1)
