"""
Studio / Programs test cases
FORME-1902
"""
import pytest
from surfaces.member_android.pages.studio_page import StudioPage


@pytest.fixture()
def studio(driver):
    page = StudioPage(driver)
    page.ensure_logged_in()
    return page


class TestPrograms:

    def test_FORME_1902_completed_state_for_program(self, studio):
        """
        FORME-1902: Verify Completed state for Program.
        Pre-condition:
          - Member has watched a video from a Program playlist for ≥50% of total time on the Lift device.
          - Member is signed into the Android app.
        Steps:
          1. Navigate to Studio tab.
          2. Tap on Programs section.
          3. Verify the main Programs tile shows the correct number of completed classes.
          4. Tap into the Program and verify the individual class tile shows 'Completed' state.
        """
        studio.go_to_programs()

        assert studio.is_completed_state_shown() or studio.is_text_contains_displayed("completed"), \
            "Completed count is not shown on the Programs tile"

        studio.select_first_cps()
        studio.wait_seconds(2)
        assert studio.is_completed_state_shown(), \
            "Individual class does not show 'Completed' state after being watched ≥50%"
