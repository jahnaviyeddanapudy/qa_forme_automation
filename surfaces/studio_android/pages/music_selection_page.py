"""MusicSelectionPage — music picker shown between Start Class and Start Session.

This is a high-leverage page object — a single implementation drives most
of the 45 music-playlist sanity/regression tests:
  - FORME-3331: Select Music on Class Preview Screen
  - FORME-3332: Music Volume controls during session
  - FORME-3333: Select song before starting session
  - FORME-3334: Select song during session
  - FORME-3335: VOD shouldn't start until music selection dismissed
  - FORME-3337: Select/change music during session
  - FORME-3338: Trainer + music balance

Placeholder — all IDs TODO until we dump the screen on Studio.
"""
from surfaces.studio_android.pages.base import StudioBasePage


class MusicSelectionPage(StudioBasePage):
    # TODO: All element IDs need confirmation

    def wait_for_music_screen(self):
        # TODO: confirm a reliable "screen loaded" marker
        raise NotImplementedError(
            "MusicSelectionPage.wait_for_music_screen() — confirm IDs first"
        )

    def select_first_song(self):
        """Tap the first song in the list — simplest starting point for
        any music-related test."""
        raise NotImplementedError("MusicSelectionPage.select_first_song()")

    def search_and_select(self, search_term):
        """FORME-3334 / 3337: search for a specific track."""
        raise NotImplementedError("MusicSelectionPage.search_and_select()")

    def set_music_balance(self, trainer_volume_pct, music_volume_pct):
        """FORME-3338 / FORME-3321: adjust trainer vs music balance."""
        raise NotImplementedError("MusicSelectionPage.set_music_balance()")

    def dismiss(self):
        """Close the music selection screen without selecting a track.
        FORME-3335: VOD shouldn't start until this is dismissed — the test
        verifies the player doesn't begin playback while this screen is up."""
        raise NotImplementedError("MusicSelectionPage.dismiss()")
