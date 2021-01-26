from datetime import date

from django.conf import settings
from django.utils.crypto import constant_time_compare, salted_hmac
from django.utils.http import base36_to_int, int_to_base36

from django_camunda.camunda_models import Task


class ExecuteTaskTokenGenerator:
    """
    Strategy object used to generate and check tokens for the task execute mechanism.

    Implementation pattern borrowed
    :class:`from django.contrib.auth.tokens.PasswordResetTokenGenerator` and adapted
    to the Camunda User Task domain.
    """

    key_salt = "zac_lite.user_tasks.tokens.ExecuteTaskTokenGenerator"
    secret = settings.SECRET_KEY

    def make_token(self, task: Task) -> str:
        """
        Return a token that can be used once to execute the given task.
        """
        return self._make_token_with_timestamp(task, self._num_days(date.today()))

    def check_token(self, task: Task, token: str) -> bool:
        """
        Check that the execute task token is correct for a given task.
        """
        if not (task and token):
            return False

        # parse the token
        try:
            ts_b36, _ = token.split("-")
        except ValueError:
            return False

        try:
            ts = base36_to_int(ts_b36)
        except ValueError:
            return False

        # Check that the timestamp/uid has not been tampered with
        valid_token = self._make_token_with_timestamp(task, ts)
        if not constant_time_compare(valid_token, token):
            return False

        # Check the timestamp is within limit. Timestamps are rounded to
        # midnight (server time) providing a resolution of only 1 day. If a
        # link is generated 5 minutes before midnight and used 6 minutes later,
        # that counts as 1 day. Therefore, EXECUTE_TASK_TOKEN_TIMEOUT_DAYS = 1 means
        # "at least 1 day, could be up to 2."
        if (
            self._num_days(date.today()) - ts
        ) > settings.EXECUTE_TASK_TOKEN_TIMEOUT_DAYS:
            return False

        return True

    def _make_token_with_timestamp(self, task: Task, timestamp: int) -> str:
        # timestamp is number of days since 2001-1-1.  Converted to
        # base 36, this gives us a 3 digit string until about 2121
        ts_b36 = int_to_base36(timestamp)
        hash_string = salted_hmac(
            self.key_salt,
            self._make_hash_value(task, timestamp),
            secret=self.secret,
        ).hexdigest()[
            ::2
        ]  # Limit to 20 characters to shorten the URL.
        return "%s-%s" % (ts_b36, hash_string)

    def _make_hash_value(self, task: Task, timestamp: int) -> str:
        """
        Hash the task ID and some state properties.

        After task execution, the task no longer exists in Camunda, so it will
        no longer validate. Any relevant state change in the task between token
        generation and usage will also invalidate the token.

        Failing that, eventually settings.EXECUTE_TASK_TOKEN_TIMEOUT_DAYS will
        invalidate the token.

        TODO: possibly the expiry should be a parameter when the link is being
        generated.
        """
        attributes = (
            "id",
            "due",
            "assignee",
            "delegation_state",
            "owner",
            "suspended",
            "form_key",
        )
        bits = (str(getattr(task, attribute) or "") for attribute in attributes)
        return "".join(bits)

    def _num_days(self, dt):
        return (dt - date(2001, 1, 1)).days


token_generator = ExecuteTaskTokenGenerator()
