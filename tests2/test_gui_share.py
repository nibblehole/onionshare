import pytest
import os
import requests
import tempfile
import zipfile

from PyQt5 import QtCore, QtTest

from .gui_base_test import GuiBaseTest


class TestShare(GuiBaseTest):
    # Shared test methods

    # Persistence tests
    def have_same_password(self, tab, password):
        """Test that we have the same password"""
        self.assertEqual(tab.get_mode().server_status.web.password, password)

    # Share-specific tests

    def file_selection_widget_has_files(self, tab, num=2):
        """Test that the number of items in the list is as expected"""
        self.assertEqual(
            tab.get_mode().server_status.file_selection.get_num_files(), num
        )

    def deleting_all_files_hides_delete_button(self, tab):
        """Test that clicking on the file item shows the delete button. Test that deleting the only item in the list hides the delete button"""
        rect = tab.get_mode().server_status.file_selection.file_list.visualItemRect(
            tab.get_mode().server_status.file_selection.file_list.item(0)
        )
        QtTest.QTest.mouseClick(
            tab.get_mode().server_status.file_selection.file_list.viewport(),
            QtCore.Qt.LeftButton,
            pos=rect.center(),
        )
        # Delete button should be visible
        self.assertTrue(
            tab.get_mode().server_status.file_selection.delete_button.isVisible()
        )
        # Click delete, delete button should still be visible since we have one more file
        QtTest.QTest.mouseClick(
            tab.get_mode().server_status.file_selection.delete_button,
            QtCore.Qt.LeftButton,
        )
        rect = tab.get_mode().server_status.file_selection.file_list.visualItemRect(
            tab.get_mode().server_status.file_selection.file_list.item(0)
        )
        QtTest.QTest.mouseClick(
            tab.get_mode().server_status.file_selection.file_list.viewport(),
            QtCore.Qt.LeftButton,
            pos=rect.center(),
        )
        self.assertTrue(
            tab.get_mode().server_status.file_selection.delete_button.isVisible()
        )
        QtTest.QTest.mouseClick(
            tab.get_mode().server_status.file_selection.delete_button,
            QtCore.Qt.LeftButton,
        )

        # No more files, the delete button should be hidden
        self.assertFalse(
            tab.get_mode().server_status.file_selection.delete_button.isVisible()
        )

    def add_a_file_and_delete_using_its_delete_widget(self, tab):
        """Test that we can also delete a file by clicking on its [X] widget"""
        tab.get_mode().server_status.file_selection.file_list.add_file(self.tmpfiles[0])
        QtTest.QTest.mouseClick(
            tab.get_mode().server_status.file_selection.file_list.item(0).item_button,
            QtCore.Qt.LeftButton,
        )
        self.file_selection_widget_has_files(tab, 0)

    def file_selection_widget_read_files(self, tab):
        """Re-add some files to the list so we can share"""
        tab.get_mode().server_status.file_selection.file_list.add_file(self.tmpfiles[0])
        tab.get_mode().server_status.file_selection.file_list.add_file(self.tmpfiles[1])
        self.file_selection_widget_has_files(tab, 2)

    def add_large_file(self, tab):
        """Add a large file to the share"""
        size = 1024 * 1024 * 155
        with open("/tmp/large_file", "wb") as fout:
            fout.write(os.urandom(size))
        tab.get_mode().server_status.file_selection.file_list.add_file(
            "/tmp/large_file"
        )

    def add_delete_buttons_hidden(self, tab):
        """Test that the add and delete buttons are hidden when the server starts"""
        self.assertFalse(
            tab.get_mode().server_status.file_selection.add_button.isVisible()
        )
        self.assertFalse(
            tab.get_mode().server_status.file_selection.delete_button.isVisible()
        )

    def download_share(self, tab):
        """Test that we can download the share"""
        url = f"http://127.0.0.1:{tab.app.port}/download"
        if tab.settings.get("general", "public"):
            r = requests.get(url)
        else:
            r = requests.get(
                url,
                auth=requests.auth.HTTPBasicAuth(
                    "onionshare", tab.get_mode().server_status.web.password
                ),
            )

        tmp_file = tempfile.NamedTemporaryFile()
        with open(tmp_file.name, "wb") as f:
            f.write(r.content)

        zip = zipfile.ZipFile(tmp_file.name)
        QtTest.QTest.qWait(2000)
        self.assertEqual("onionshare", zip.read("test.txt").decode("utf-8"))

    def individual_file_is_viewable_or_not(self, tab):
        """Test whether an individual file is viewable (when in autostop_sharing is false) and that it isn't (when not in autostop_sharing is true)"""
        url = f"http://127.0.0.1:{tab.app.port}"
        download_file_url = f"http://127.0.0.1:{tab.app.port}/test.txt"
        if tab.settings.get("general", "public"):
            r = requests.get(url)
        else:
            r = requests.get(
                url,
                auth=requests.auth.HTTPBasicAuth(
                    "onionshare", tab.get_mode().server_status.web.password
                ),
            )

        if not tab.settings.get("share", "autostop_sharing"):
            self.assertTrue('a href="test.txt"' in r.text)

            if tab.settings.get("general", "public"):
                r = requests.get(download_file_url)
            else:
                r = requests.get(
                    download_file_url,
                    auth=requests.auth.HTTPBasicAuth(
                        "onionshare", tab.get_mode().server_status.web.password
                    ),
                )

            tmp_file = tempfile.NamedTemporaryFile()
            with open(tmp_file.name, "wb") as f:
                f.write(r.content)

            with open(tmp_file.name, "r") as f:
                self.assertEqual("onionshare", f.read())
        else:
            self.assertFalse('a href="/test.txt"' in r.text)
            if tab.settings.get("general", "public"):
                r = requests.get(download_file_url)
            else:
                r = requests.get(
                    download_file_url,
                    auth=requests.auth.HTTPBasicAuth(
                        "onionshare", tab.get_mode().server_status.web.password
                    ),
                )
            self.assertEqual(r.status_code, 404)
            self.download_share(tab)

        QtTest.QTest.qWait(2000)

    def hit_401(self, tab):
        """Test that the server stops after too many 401s, or doesn't when in public_mode"""
        url = f"http://127.0.0.1:{tab.app.port}/"

        for _ in range(20):
            password_guess = self.gui.common.build_password()
            requests.get(
                url, auth=requests.auth.HTTPBasicAuth("onionshare", password_guess)
            )

        # A nasty hack to avoid the Alert dialog that blocks the rest of the test
        if not tab.settings.get("general", "public"):
            QtCore.QTimer.singleShot(1000, self.accept_dialog)

        # In public mode, we should still be running (no rate-limiting)
        if tab.settings.get("general", "public"):
            self.web_server_is_running(tab)
        # In non-public mode, we should be shut down (rate-limiting)
        else:
            self.web_server_is_stopped(tab)

    # Auto-start timer tests

    def set_autostart_timer(self, tab, timer):
        """Test that the timer can be set"""
        schedule = QtCore.QDateTime.currentDateTime().addSecs(timer)
        tab.get_mode().mode_settings_widget.autostart_timer_widget.setDateTime(schedule)
        self.assertTrue(
            tab.get_mode().mode_settings_widget.autostart_timer_widget.dateTime(),
            schedule,
        )

    def autostart_timer_widget_hidden(self, tab):
        """Test that the auto-start timer widget is hidden when share has started"""
        self.assertFalse(
            tab.get_mode().mode_settings_widget.autostart_timer_widget.isVisible()
        )

    def scheduled_service_started(self, tab, mode, wait):
        """Test that the server has timed out after the timer ran out"""
        QtTest.QTest.qWait(wait)
        # We should have started now
        self.assertEqual(tab.get_mode().server_status.status, 2)

    def cancel_the_share(self, tab, mode):
        """Test that we can cancel a share before it's started up """
        self.server_working_on_start_button_pressed(tab)
        self.server_status_indicator_says_scheduled(tab)
        self.add_delete_buttons_hidden(tab)
        self.mode_settings_widget_is_hidden(tab)
        self.set_autostart_timer(tab, 10)
        QtTest.QTest.mousePress(
            tab.get_mode().server_status.server_button, QtCore.Qt.LeftButton
        )
        QtTest.QTest.qWait(2000)
        QtTest.QTest.mouseRelease(
            tab.get_mode().server_status.server_button, QtCore.Qt.LeftButton
        )
        self.assertEqual(tab.get_mode().server_status.status, 0)
        self.server_is_stopped(tab)
        self.web_server_is_stopped(tab)

    # Grouped tests follow from here

    def run_all_share_mode_setup_tests(self, tab):
        """Tests in share mode prior to starting a share"""
        tab.get_mode().server_status.file_selection.file_list.add_file(self.tmpfiles[0])
        tab.get_mode().server_status.file_selection.file_list.add_file(self.tmpfiles[1])
        self.file_selection_widget_has_files(tab, 2)
        self.history_is_not_visible(tab)
        self.click_toggle_history(tab)
        self.history_is_visible(tab)
        self.deleting_all_files_hides_delete_button(tab)
        self.add_a_file_and_delete_using_its_delete_widget(tab)
        self.file_selection_widget_read_files(tab)

    def run_all_share_mode_started_tests(self, tab, startup_time=2000):
        """Tests in share mode after starting a share"""
        self.server_working_on_start_button_pressed(tab)
        self.server_status_indicator_says_starting(tab)
        self.add_delete_buttons_hidden(tab)
        self.mode_settings_widget_is_hidden(tab)
        self.server_is_started(tab, startup_time)
        self.web_server_is_running(tab)
        self.have_a_password(tab)
        self.url_description_shown(tab)
        self.have_copy_url_button(tab)
        self.server_status_indicator_says_started(tab)

    def run_all_share_mode_download_tests(self, tab):
        """Tests in share mode after downloading a share"""
        tab.get_mode().server_status.file_selection.file_list.add_file(
            self.tmpfile_test
        )
        self.web_page(tab, "Total size")
        self.download_share(tab)
        self.history_widgets_present(tab)
        self.server_is_stopped(tab)
        self.web_server_is_stopped(tab)
        self.server_status_indicator_says_closed(tab)
        self.add_button_visible(tab)
        self.server_working_on_start_button_pressed(tab)
        self.toggle_indicator_is_reset(tab)
        self.server_is_started(tab)
        self.history_indicator(tab)

    def run_all_share_mode_individual_file_download_tests(self, tab):
        """Tests in share mode after downloading a share"""
        self.web_page(tab, "Total size")
        self.individual_file_is_viewable_or_not(tab)
        self.history_widgets_present(tab)
        self.server_is_stopped(tab)
        self.web_server_is_stopped(tab)
        self.server_status_indicator_says_closed(tab)
        self.add_button_visible(tab)
        self.server_working_on_start_button_pressed(tab)
        self.server_is_started(tab)
        self.history_indicator(tab)

    def run_all_share_mode_tests(self, tab):
        """End-to-end share tests"""
        self.run_all_share_mode_setup_tests(tab)
        self.run_all_share_mode_started_tests(tab)
        self.run_all_share_mode_download_tests(tab)

    def run_all_clear_all_button_tests(self, tab):
        """Test the Clear All history button"""
        self.run_all_share_mode_setup_tests(tab)
        self.run_all_share_mode_started_tests(tab)
        self.individual_file_is_viewable_or_not(tab)
        self.history_widgets_present(tab)
        self.clear_all_history_items(tab, 0)
        self.individual_file_is_viewable_or_not(tab)
        self.clear_all_history_items(tab, 2)

    def run_all_share_mode_individual_file_tests(self, tab):
        """Tests in share mode when viewing an individual file"""
        self.run_all_share_mode_setup_tests(tab)
        self.run_all_share_mode_started_tests(tab)
        self.run_all_share_mode_individual_file_download_tests(tab)

    def run_all_large_file_tests(self, tab):
        """Same as above but with a larger file"""
        self.run_all_share_mode_setup_tests(tab)
        self.add_large_file(tab)
        self.run_all_share_mode_started_tests(tab, startup_time=15000)
        self.assertTrue(tab.filesize_warning.isVisible())
        self.server_is_stopped(tab)
        self.web_server_is_stopped(tab)
        self.server_status_indicator_says_closed(tab)

    def run_all_share_mode_persistent_tests(self, tab):
        """Same as end-to-end share tests but also test the password is the same on multiple shared"""
        self.run_all_share_mode_setup_tests(tab)
        self.run_all_share_mode_started_tests(tab)
        password = tab.get_mode().server_status.web.password
        self.run_all_share_mode_download_tests(tab)
        self.have_same_password(tab, password)

    def run_all_share_mode_timer_tests(self, tab):
        """Auto-stop timer tests in share mode"""
        self.run_all_share_mode_setup_tests(tab)
        self.set_timeout(tab, 5)
        self.run_all_share_mode_started_tests(tab)
        self.autostop_timer_widget_hidden(tab)
        self.server_timed_out(tab, 10000)
        self.web_server_is_stopped(tab)

    def run_all_share_mode_unreadable_file_tests(self, tab):
        """Attempt to share an unreadable file"""
        self.run_all_share_mode_setup_tests(tab)
        QtCore.QTimer.singleShot(1000, self.accept_dialog)
        tab.get_mode().server_status.file_selection.file_list.add_file(
            "/tmp/nonexistent.txt"
        )
        self.file_selection_widget_has_files(tab, 2)

    # Tests

    @pytest.mark.gui
    def test_autostart_and_autostop_timer_mismatch(self):
        """
        If autostart timer is after autostop timer, a warning should be thrown
        """
        tab = self.new_share_tab()

        def accept_dialog():
            window = tab.common.gui.qtapp.activeWindow()
            if window:
                window.close()

        tab.get_mode().mode_settings_widget.toggle_advanced_button.click()
        tab.get_mode().mode_settings_widget.autostart_timer_checkbox.click()
        tab.get_mode().mode_settings_widget.autostop_timer_checkbox.click()

        self.run_all_common_setup_tests()

        self.run_all_share_mode_setup_tests(tab)
        self.set_autostart_timer(tab, 15)
        self.set_timeout(tab, 5)
        QtCore.QTimer.singleShot(200, accept_dialog)
        tab.get_mode().server_status.server_button.click()
        self.server_is_stopped(tab)

        self.close_all_tabs()

    @pytest.mark.gui
    def test_autostart_timer(self):
        """
        Autostart timer should automatically start
        """
        tab = self.new_share_tab()
        self.run_all_common_setup_tests()

        self.run_all_share_mode_setup_tests(tab)
        self.set_autostart_timer(tab, 5)
        self.server_working_on_start_button_pressed(tab)
        self.autostart_timer_widget_hidden(tab)
        self.server_status_indicator_says_scheduled(tab)
        self.web_server_is_stopped(tab)
        self.scheduled_service_started(tab, 7000)
        self.web_server_is_running(tab)

        self.close_all_tabs()
