"""
Tests for the non-blocking Mixpanel tracking (utils/mixpanel/utils.py) and
PageMixin's page-view tracking.
"""

import threading
import time
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase, RequestFactory, override_settings
from django.urls import reverse

import utils.mixpanel.utils as mixpanel_utils

User = get_user_model()


class EnqueueTest(TestCase):
    """The background queue itself."""

    @override_settings(MIXPANEL_TOKEN="real-token")
    def test_call_runs_in_background_without_blocking(self):
        done = threading.Event()

        def slow_call():
            time.sleep(0.5)
            done.set()

        start = time.perf_counter()
        mixpanel_utils._enqueue(slow_call)
        self.assertLess(time.perf_counter() - start, 0.1)
        self.assertTrue(done.wait(timeout=5))

    @override_settings(MIXPANEL_TOKEN="real-token")
    def test_failing_call_does_not_kill_the_worker(self):
        done = threading.Event()

        def failing_call():
            raise RuntimeError("Mixpanel down")

        mixpanel_utils._enqueue(failing_call)
        mixpanel_utils._enqueue(done.set)
        self.assertTrue(done.wait(timeout=5))

    @override_settings(MIXPANEL_TOKEN="real-token")
    def test_full_queue_drops_calls_instead_of_blocking(self):
        calls = []
        with patch.object(mixpanel_utils, "_pending", mixpanel_utils.queue.Queue(maxsize=1)), \
                patch.object(mixpanel_utils, "_ensure_worker"):
            mixpanel_utils._enqueue(calls.append, 1)
            mixpanel_utils._enqueue(calls.append, 2)  # dropped, must not block
            self.assertEqual(mixpanel_utils._pending.qsize(), 1)

    def test_disabled_when_token_is_empty_or_placeholder(self):
        for token in ("", "test", "  "):
            with override_settings(MIXPANEL_TOKEN=token):
                self.assertFalse(mixpanel_utils.is_enabled())
        with override_settings(MIXPANEL_TOKEN="real-token"):
            self.assertTrue(mixpanel_utils.is_enabled())

    def test_consumer_has_timeout_and_no_retries(self):
        consumer = mixpanel_utils.mp._consumer
        self.assertEqual(consumer._request_timeout, mixpanel_utils.REQUEST_TIMEOUT_SECONDS)
        self.assertEqual(consumer._session.adapters["https://"].max_retries.total, 0)


@override_settings(MIXPANEL_TOKEN="real-token")
class PageViewTrackingTest(TestCase):
    """What PageMixin / track_user_activity enqueue for a page view."""

    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(
            username="mp_user@email.com",
            email="mp_user@email.com",
            password="testpass123",
            is_approved=True,
        )
        cls.url = reverse("investments:home_investments")

    def setUp(self):
        patcher = patch.object(mixpanel_utils, "_enqueue")
        self.enqueue = patcher.start()
        self.addCleanup(patcher.stop)
        self.client.force_login(self.user)

    def _enqueued(self):
        return [c.args[0].__name__ for c in self.enqueue.call_args_list]

    def test_first_page_view_sends_profile_and_event(self):
        self.client.get(self.url)
        self.assertEqual(self._enqueued(), ["people_set", "track"])
        track_args = self.enqueue.call_args_list[1].args
        self.assertEqual(track_args[1:3], (str(self.user.id), "Investments Page Viewed"))

    def test_profile_is_sent_once_per_session(self):
        self.client.get(self.url)
        self.enqueue.reset_mock()
        self.client.get(self.url)
        self.assertEqual(self._enqueued(), ["track"])

    def test_post_is_not_tracked_as_a_page_view(self):
        response = self.client.post(self.url, {"is-funded-filter": ["", "completed"]})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(self._enqueued(), [])

    def test_explicit_business_events_are_still_tracked(self):
        request = RequestFactory().post("/")
        request.user = self.user
        request.session = self.client.session
        mixpanel_utils.track_user_activity(request, "PackageSubmitted")
        self.assertIn("track", self._enqueued())

    @override_settings(MIXPANEL_TOKEN="test")
    def test_nothing_is_sent_with_placeholder_token(self):
        self.client.get(self.url)
        self.assertEqual(self._enqueued(), [])


@override_settings(MIXPANEL_TOKEN="real-token")
class PageDoesNotWaitForMixpanelTest(TestCase):
    def test_page_is_served_while_mixpanel_calls_are_slow(self):
        user = User.objects.create_user(
            username="mp_slow@email.com",
            email="mp_slow@email.com",
            password="testpass123",
            is_approved=True,
        )
        self.client.force_login(user)
        sent = threading.Event()

        def slow_call(*args, **kwargs):
            time.sleep(1)
            sent.set()

        with patch.object(mixpanel_utils.mp, "track", side_effect=slow_call), \
                patch.object(mixpanel_utils.mp, "people_set", side_effect=slow_call):
            start = time.perf_counter()
            response = self.client.get(reverse("investments:home_investments"))
            elapsed = time.perf_counter() - start
        self.assertEqual(response.status_code, 200)
        self.assertLess(elapsed, 1.0)  # the two calls alone would take 2s
        self.assertTrue(sent.wait(timeout=5))  # ...and they still go out
