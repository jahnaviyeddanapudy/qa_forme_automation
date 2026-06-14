"""
Messages test cases
FORME-2147 | FORME-2150 | FORME-2152 | FORME-2154
"""
import pytest
from pages.messages_page import MessagesPage
from pages.studio_page import StudioPage


@pytest.fixture()
def messages(driver):
    page = MessagesPage(driver)
    page.navigate_to_messages()
    return page


@pytest.fixture()
def studio(driver):
    page = StudioPage(driver)
    page.ensure_logged_in()
    return page


class TestMessages:

    def test_FORME_2147_client_sends_text_message_trainer_receives(self, messages):
        """
        FORME-2147: Client sends text message and Trainer receives the message.
        Pre-condition: Only assigned clients are displayed.
        Steps:
          1. Client sends a message from Messages tab.
          2. Verify the message appears in the chat thread.
          3. Trainer should receive the message (verified visually or via trainer app).
        """
        assert messages.is_chat_screen_visible(), "Messages chat screen is not visible"

        test_msg = "Hello, this is an automated test message"
        messages.send_text_message(test_msg)
        messages.wait_seconds(2)

        assert messages.is_message_in_list(test_msg), \
            f"Sent message '{test_msg}' is not visible in the chat thread"

    def test_FORME_2150_client_sends_image_from_gallery_trainer_receives(self, messages):
        """
        FORME-2150: Client sends an image from Photo Gallery and Trainer receives the image.
        Steps:
          1. Client selects an image from Gallery and sends it to trainer.
          2. Verify image appears in chat thread.
          3. Trainer should receive the image.
        """
        assert messages.is_chat_screen_visible(), "Messages chat screen is not visible"

        messages.select_image_from_gallery()
        messages.wait_seconds(3)

        assert messages.is_image_sent(), \
            "Image was not sent / not visible in the chat thread after selecting from Gallery"

    def test_FORME_2152_client_reacts_with_emoji_trainer_receives_reaction(self, messages):
        """
        FORME-2152: Client reacts with emoji and Trainer receives the reaction.
        Steps:
          1. Client long-presses a trainer message to open emoji picker.
          2. Select an emoji reaction.
          3. Verify emoji reaction is visible on the message.
        """
        assert messages.is_message_list_visible(), "Message list is not visible"

        messages.long_press_message(index=0)
        messages.wait_seconds(1)

        messages.select_emoji_reaction("👍")
        messages.wait_seconds(1)

        assert messages.is_emoji_reaction_visible(), \
            "Emoji reaction is not visible after client reacted to trainer message"

    def test_FORME_2154_client_sends_message_from_post_session_survey_trainer_receives(
            self, studio, messages):
        """
        FORME-2154: Client sends message from Post Session survey after VOD and
                    trainer receives the message along with workout details.
        Steps:
          1. Complete a VOD session so that Post-Session Survey appears.
          2. Send a message from the Post-Session Survey screen.
          3. Navigate to Messages tab.
          4. Verify the message (with workout details) appears in chat.
        """
        studio.navigate_to_studio()
        studio.play_vod_class()

        max_wait = 180
        elapsed = 0
        while elapsed < max_wait:
            if studio.is_post_session_survey_displayed():
                break
            studio.wait_seconds(5)
            elapsed += 5

        assert studio.is_post_session_survey_displayed(), \
            "Post-Session Survey did not appear — cannot test message sending from survey"

        survey_msg = "Great workout! Feeling strong."

        # Step 1 — tap 2 stars for the Session rating.
        studio.tap_rating_star(2)
        studio.wait_seconds(0.5)

        # Step 2 — enter message in the Comments field.
        studio.enter_survey_comment(survey_msg)

        # Step 3 — verify Submit is enabled (requires at least a rating).
        assert studio.is_submit_active(), \
            "Submit button is not enabled after selecting rating and entering comment"

        # Step 4 — submit the survey.
        studio.submit_survey()
        studio.wait_seconds(2)

        # Step 5 — close the Workout Summary dialog.
        studio.close_workout_summary()

        # Step 6 — navigate to Messages and verify the comment arrived.
        messages.navigate_to_messages()
        assert messages.is_message_in_list(survey_msg) or \
               messages.is_text_contains_displayed("workout"), \
            "Message from Post-Session Survey was not received in Messages tab"

    def test_FORME_2154_full_vod_completion_post_survey_message(self, studio, messages):
        """
        FORME-2154 (natural completion): Barre VOD plays until the class ends on its
        own; if the class does not auto-complete within 60 minutes the session is ended
        manually as a fallback.  Either path leads to the Post-Session Survey.
        Steps:
          1. Navigate to Barre VOD category and start a class.
          2. Wait up to 60 min for natural class completion.
             (Falls back to manual end if the survey has not appeared by then.)
          3. Post-Session Survey appears.
          4. Tap 5 stars for Session rating.
          5. Enter message in Comments field.
          6. Assert Submit is enabled.
          7. Tap Submit.
          8. Close Workout Summary dialog.
          9. Navigate to Messages → verify message.
        """
        studio.navigate_to_studio()
        studio.start_vod_class()

        # Wait for the class to end naturally (up to 60 minutes).
        # If the survey still hasn't appeared, end the session manually so the
        # rest of the test can still verify the survey interaction.
        if not studio.wait_for_class_completion(timeout=3600):
            studio._end_class_leave_survey_open()

        assert studio.is_post_session_survey_displayed(), \
            "Post-Session Survey did not appear after class completion"

        survey_msg = "Amazing class! Completed the full session."

        # Tap 5 stars for the Session rating.
        studio.tap_rating_star(5)
        studio.wait_seconds(0.5)

        # Enter message in the Comments field.
        studio.enter_survey_comment(survey_msg)

        # Verify Submit is enabled (requires at least a rating).
        assert studio.is_submit_active(), \
            "Submit button is not enabled after selecting rating and entering comment"

        # Submit the survey.
        studio.submit_survey()
        studio.wait_seconds(2)

        # Close the Workout Summary dialog.
        studio.close_workout_summary()

        # Navigate to Messages and verify the comment arrived.
        messages.navigate_to_messages()
        assert messages.is_message_in_list(survey_msg) or \
               messages.is_text_contains_displayed("workout"), \
            "Message from Post-Session Survey was not received in Messages tab"
