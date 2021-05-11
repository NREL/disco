import logging

logger = logging.getLogger(__name__)


class FailingTestBisector:
    """Helper class to find the highest index of a sequence that passes a test."""

    def __init__(self, count):
        self._count = count
        self._highest_pass = -1
        self._lowest_fail = count
        self._num_iterations = 0

    def get_first_index(self):
        """Return the first index to test."""
        first_index = self._count // 2
        logger.debug("first_index=%s", first_index)
        return first_index

    def get_next_index(self, last_index, last_result_passed):
        """Return the next index to test and a bool to indicate whether that index is final.

        Parameters
        ----------
        last_index : int
        last_result_passed : bool

        Returns
        -------
        tuple
            next index to test, True if done

        Raises
        ------
        NoPassingIndex
            Raised if there is no passing index.

        """
        self._num_iterations += 1
        if last_result_passed:
            index, done = self._get_next_index_after_pass(last_index)
        else:
            index, done = self._get_next_index_after_failure(last_index)
        logger.debug(
            "last_index=%s passed=%s next_index=%s done=%s",
            last_index,
            last_result_passed,
            index,
            done,
        )

        if done:
            logger.info(
                "Highest passing index %s num_iterations=%s", last_index, self._num_iterations
            )

        return index, done

    def _get_next_index_after_pass(self, last_index):
        if last_index == self._lowest_fail:
            return last_index, True
        if last_index == self._count - 1:
            return last_index, True
        if last_index > self._highest_pass:
            self._highest_pass = last_index

        next_index = (last_index + self._lowest_fail) // 2
        if next_index == last_index:
            next_index += 1
        if next_index == self._lowest_fail:
            return last_index, True
        return next_index, False

    def _get_next_index_after_failure(self, last_index):
        if last_index == self._highest_pass:
            return last_index, True
        if last_index < self._lowest_fail:
            self._lowest_fail = last_index

        next_index = (self._highest_pass + last_index) // 2
        if next_index == -1:
            raise NoPassingIndex(f"no passing index count={self._count}")
        if next_index == self._highest_pass:
            return next_index, True
        return next_index, False


class NoPassingIndex(Exception):
    """Raised when there is no passing index."""
