import logging

import pytest

from disco.utils.failing_test_bisector import FailingTestBisector, NoPassingIndex


logger = logging.getLogger(__name__)


def test_bisect():
    count = 100
    for i in range(0, count):
        for highest_passing_index in range(i):
            func = lambda x: x <= highest_passing_index
            logger.info(
                "Run test with count=%s highest_passing_index=%s", i, highest_passing_index
            )
            assert run_test(i, highest_passing_index, func) == highest_passing_index

    with pytest.raises(NoPassingIndex):
        run_test(count, -1, lambda x: False)


def run_test(count, highest_passing_index, func):
    bisector = FailingTestBisector(count)
    index = bisector.get_first_index()
    done = False
    indices_run = set()
    for i in range(count):
        indices_run.add(index)
        index, done = bisector.get_next_index(index, func(index))
        if done:
            break
        if index in indices_run:
            raise Exception(
                f"index={index} has already been run. count={count}, high={highest_passing_index}"
            )

    if not done:
        raise Exception("failed to find index")
    return index
