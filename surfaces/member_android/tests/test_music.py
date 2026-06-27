"""
Third-Party Music test cases
FORME-1969 | FORME-1961 | FORME-1960 | FORME-1973
"""
import pytest
from surfaces.member_android.pages.studio_page import StudioPage


@pytest.fixture()
def studio(driver):
    page = StudioPage(driver)
    page.ensure_logged_in()
    return page


class TestMusicDuringSession:

    def test_FORME_1969_member_can_play_change_music_from_youtube_during_session(self, studio):
        """
        FORME-1969: Verify member can play/change music from YouTube during a session.
        Steps:
          1. Navigate to Studio → go to Barre category.
          2. Select any class.
          3. Tap Start Class.
          4. Tap Start Session (skip music selection).
          5. While class is playing, tap once to reveal session controls.
          6. Tap Music icon (top right).
          7. Select YouTube Music.
          8. Session pauses while app switches to YouTube Music.
          9. Play any song on YouTube Music.
          10. Switch back to Forme app (class session).
        """
        studio.navigate_to_studio()
        studio.start_vod_class(skip_music=True)  # steps 1–4
        studio.wait_seconds(3)

        studio.tap_screen_during_session()        # step 5: reveal controls
        studio.wait_seconds(1)

        studio.tap_music_icon()                   # step 6
        studio.wait_seconds(1)

        studio.select_youtube_music()             # step 7 — opens YouTube Music app
        studio.wait_seconds(3)                    # step 8: session pauses automatically

        studio.play_song_in_youtube_music()       # step 9
        studio.wait_seconds(2)

        studio.launch_app()                       # step 10: switch back to Forme app
        studio.wait_seconds(2)

        # The music selection dialog may still be showing as a Dialog overlay
        # on top of InClassActivity after returning from YouTube Music.
        # Dismiss it so the in-class view elements become visible.
        if studio.is_displayed(studio.MUSIC_YOUTUBE_BTN, timeout=3):
            studio.skip_music_selection()
            studio.wait_seconds(2)

        assert studio.is_session_active(), \
            "Session was not active after returning from YouTube Music"

        # Verify the session stays running for 30 more seconds, then end it.
        studio.keep_alive_wait(30)

        studio.tap_screen_during_session()        # reveal controls
        studio.wait_seconds(1)
        studio.tap_end_session()

    def test_FORME_1961_member_can_play_music_from_youtube_music_while_starting_session(self, studio):
        """
        FORME-1961: Verify member can play music from YouTube Music while starting a session.
        Steps:
          1. Navigate to Studio → go to Barre category.
          2. Select any class.
          3. Tap Start Class.
          4. Select YouTube Music on the Select Music screen.
          5. Play any song on YouTube Music.
          6. Switch back to Forme app (Select Music screen).
          7. Tap Start Session.
          8. After 60 seconds, tap screen then tap END SESSION.
        """
        studio.navigate_to_studio()
        studio.start_vod_class(skip_music=False)   # steps 1–3: stops at music dialog
        studio.wait_seconds(2)

        assert studio.is_music_selection_screen_displayed(), \
            "'Select Your Music' screen did not appear after tapping Start Class"

        studio.select_youtube_music()              # step 4 — opens YouTube Music app
        studio.wait_seconds(3)

        studio.play_song_in_youtube_music()        # step 5
        studio.wait_seconds(2)

        studio.launch_app()                        # step 6: switch back to Forme
        studio.wait_seconds(2)

        # Forme may auto-dismiss the music screen when YouTube Music is selected.
        # Tap Start Session only if the music screen is still showing.
        if studio.is_music_selection_screen_displayed():
            studio.tap(studio.START_BTN)           # step 7: tap Start Session
            studio.wait_seconds(2)

        assert studio.is_session_active(), \
            "Session was not active after returning from YouTube Music"

        studio.keep_alive_wait(60)                 # step 8: wait 60 seconds

        studio.tap_screen_during_session()         # reveal controls
        studio.wait_seconds(1)
        studio.tap_end_session()

    def test_FORME_1960_member_can_play_music_from_apple_music_while_starting_session(self, studio):
        """
        FORME-1960: Verify member can play music from Apple Music while starting a session.
        Steps:
          1. Navigate to Studio → go to Barre category.
          2. Select any class.
          3. Tap Start Class.
          4. Select Apple Music on the Select Music screen.
          5. Play any song on Apple Music.
          6. Switch back to Forme app (Select Music screen).
          7. Tap Start Session.
          8. After 60 seconds, tap screen then tap END SESSION.
        """
        studio.navigate_to_studio()
        studio.start_vod_class(skip_music=False)   # steps 1–3: stops at music dialog
        studio.wait_seconds(2)

        assert studio.is_music_selection_screen_displayed(), \
            "'Select Your Music' screen did not appear after tapping Start Class"

        studio.select_apple_music()                # step 4 — opens Apple Music app
        studio.wait_seconds(3)

        studio.play_song_in_apple_music()          # step 5
        studio.wait_seconds(2)

        studio.launch_app()                        # step 6: switch back to Forme
        studio.wait_seconds(2)

        # Apple Music may auto-dismiss the music screen; tap Start Session if still showing.
        if studio.is_music_selection_screen_displayed():
            studio.tap(studio.START_BTN)           # step 7: tap Start Session
            studio.wait_seconds(2)

        assert studio.is_session_active(), \
            "Session was not active after returning from Apple Music"

        studio.keep_alive_wait(60)                 # step 8: wait 60 seconds

        studio.tap_screen_during_session()         # reveal controls
        studio.wait_seconds(1)
        studio.tap_end_session()

    def test_FORME_1973_session_pauses_when_selecting_music(self, studio):
        """
        FORME-1973: Verify session pauses when switching to YouTube Music and
                    resumes when switching back to the Forme app.
        Steps:
          1. Navigate to Studio → Barre category.
          2. Select any class and tap Start Class.
          3. Tap Start Session (skip music selection).
          4. While class is playing, tap screen to reveal controls.
          5. Tap Music icon → Select YouTube Music (app switches to YTM).
          6. Switch back to Forme — verify session is paused.
          7. Switch back to YouTube Music and play a song.
          8. Switch back to Forme — verify session is active (resumed).
          9. After 30 seconds, tap screen and tap END SESSION.
        """
        studio.navigate_to_studio()
        studio.start_vod_class(skip_music=True)   # steps 1–3
        studio.wait_seconds(2)

        studio.tap_screen_during_session()         # step 4: reveal controls
        studio.wait_seconds(1)

        studio.tap_music_icon()                    # step 5
        studio.wait_seconds(1)

        # Validation 1: YouTube Music button visible → music picker is open → session paused.
        # Uses ID-based lookup (AppiumBy.ID) which returns in <100 ms when the element is
        # present. Avoids is_music_selection_screen_displayed() which calls find_by_text()
        # (UiSelector text query) and can block for several seconds under active CPS load.
        assert studio.is_displayed(studio.MUSIC_YOUTUBE_BTN), \
            "Music selection screen did not appear / session was not paused after tapping Music icon"

        studio.select_youtube_music()              # step 5 cont.: switches to YouTube Music
        # No extra sleep here — play_song_in_youtube_music() polls for the YTM package.

        # Step 7: play a song in YouTube Music.
        studio.play_song_in_youtube_music()
        studio.wait_seconds(1)

        # Step 8: return to Forme.
        studio.launch_app()
        studio.wait_seconds(1)
        if studio.is_music_selection_screen_displayed():
            studio.skip_music_selection()
            studio.wait_seconds(2)

        # Validation 2: session should be active (resumed) after returning.
        assert studio.is_session_active(), \
            "Session did not resume after switching back to Forme"

        # Step 9: wait 30 s then end the session.
        studio.keep_alive_wait(30)
        studio.tap_screen_during_session()
        studio.wait_seconds(1)
        studio.tap_end_session()
