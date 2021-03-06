# *****************************************************************************
#
# Copyright (c) 2019, the nbcelltests authors.
#
# This file is part of the nbcelltests library, distributed under the terms of
# the Apache License 2.0.  The full license can be found in the LICENSE file.
#
import tempfile
import os
import sys
import unittest

from nbcelltests.test import run

# TODO: we should generate the notebooks rather than having them as files
# (same for lint ones)
CUMULATIVE_RUN = os.path.join(os.path.dirname(__file__), '_cumulative_run.ipynb')
CELL_ERROR = os.path.join(os.path.dirname(__file__), '_cell_error.ipynb')
TEST_ERROR = os.path.join(os.path.dirname(__file__), '_test_error.ipynb')
TEST_FAIL = os.path.join(os.path.dirname(__file__), '_test_fail.ipynb')

# Hack. We want to test expected behavior in distributed situation,
# which we are doing via pytest --forked.
FORKED = '--forked' in sys.argv


def _assert_x_undefined(t):
    """
    Convenience method to assert that x is not already defined in the kernel.
    """
    t.run_test("""
    try:
        x
    except NameError:
        pass
    else:
        raise Exception('x was already defined')
    """)

# TODO: This test file's manual use of unittest is brittle

# TODO: generated test methods are 0 based, but jupyter is typically 1
# based. To be fixed in
# https://github.com/jpmorganchase/nbcelltests/issues/99.


def _import_from_path(path, module_name):
    """
    Import and return a python module at the given path, with
    module_name setting __name__.

    See e.g. https://stackoverflow.com/a/67692.
    """
    # TODO: need to test over multiple python versions
    # (https://github.com/jpmorganchase/nbcelltests/issues/106)
    import importlib.util
    spec = importlib.util.spec_from_file_location(module_name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class _TestCellTests(unittest.TestCase):
    # abstract :)

    @classmethod
    def setUpClass(cls):
        """
        Generate test file from notebook, then import it, and make the
        resulting module available as "generated_tests" class attribute.
        """
        tf = tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False, encoding='utf8')
        tf_name = tf.name
        try:
            # the module name (__name__) doesn't really matter, but
            # will be nbcelltests.tests.test_tests.X, where X is
            # whatever concrete subclass is this method belongs to.
            cls.generated_tests = _import_from_path(path=run(cls.NBNAME, filename=tf_name), module_name="nbcelltests.tests.%s.%s" % (__name__, cls.__name__))
            tf.close()
        finally:
            os.remove(tf_name)


class TestCumulativeRun(_TestCellTests):

    NBNAME = CUMULATIVE_RUN

    def test_state(self):
        """In the expected case, the five cells of the notebook should work
        out as follows:

             cell    test   state
        1:    -       -       -
        2:   x=0      -      x=0
        3:   x+=1     -      x=1
        4:   x+=1     -      x=2
        5:    -      x+=1    x=3

        However, these tests originally detected repeated execution of
        cells in the same kernel. Cell 2 actually only sets x to 0 if
        x is not already defined; if x is already defined, cell 2 does
        not change x's value. If for some reason each test results in
        multiple executions of the cells, the results will look like
        this:

             cell    test   state
        1:    -       -       -
        2:    -       -      x>0   (bad; x was previously defined in kernel)
        3:   x+=1     -      x>1   (bad)
        4:   x+=1     -      x>2   (bad)
        5:    -      x+=1    x>3   (bad)
        """
        t = self.generated_tests.TestNotebook()
        t.setUpClass()

        # check cell did not run
        # (no %cell in test)
        t.setUp()
        _assert_x_undefined(t)
        t.test_cell_0()
        _assert_x_undefined(t)
        t.tearDown()
        if FORKED:
            t.tearDownClass()

        # check cell ran
        # (%cell in test)
        if FORKED:
            t.setUpClass()
        t.setUp()
        t.test_cell_1()
        t.run_test("""
        assert x == 0, x
        """)
        t.tearDown()
        if FORKED:
            t.tearDownClass()

        # check cumulative cells ran
        if FORKED:
            t.setUpClass()
        t.setUp()
        t.test_cell_2()
        t.run_test("""
        assert x == 1, x
        """)
        t.tearDown()
        if FORKED:
            t.tearDownClass()

        # check cumulative cells ran (but not multiple times!)
        if FORKED:
            t.setUpClass()
        t.setUp()
        t.test_cell_3()
        t.run_test("""
        assert x == 2, x
        """)
        t.tearDown()
        if FORKED:
            t.tearDownClass()

        # check test affects state
        if FORKED:
            t.setUpClass()
        t.setUp()
        t.test_cell_4()
        t.run_test("""
        assert x == 3, x
        """)
        t.tearDown()

        t.tearDownClass()


class TestExceptionInCell(_TestCellTests):

    NBNAME = CELL_ERROR

    def test_exception_in_cell_is_detected(self):
        t = self.generated_tests.TestNotebook()

        t.setUpClass()
        t.setUp()

        # cell should error out
        try:
            t.test_cell_0()
        except Exception as e:
            assert e.args[0].startswith("Cell execution caused an exception")
            assert e.args[0].endswith("My code does not even run")
        else:
            raise Exception("Cell should have errored out")
        finally:
            t.tearDown()
            t.tearDownClass()


class TestExceptionInTest(_TestCellTests):

    NBNAME = TEST_ERROR

    def test_exception_in_test_is_detected(self):
        t = self.generated_tests.TestNotebook()
        t.setUpClass()
        t.setUp()

        # caught cell error
        t.test_cell_0()

        t.tearDown()
        if FORKED:
            t.tearDownClass()

        if FORKED:
            t.setUpClass()
        t.setUp()

        _assert_x_undefined(t)

        # test should error out
        try:
            t.test_cell_1()
        except Exception as e:
            assert e.args[0].startswith("Cell execution caused an exception")
            assert e.args[0].endswith("My test is bad too")
        else:
            raise Exception("Test should have failed")
        finally:
            t.tearDown()
            t.tearDownClass()


class TestFailureInTest(_TestCellTests):

    NBNAME = TEST_FAIL

    def test_failure_is_detected(self):
        t = self.generated_tests.TestNotebook()
        t.setUpClass()
        t.setUp()

        # caught cell error
        try:
            t.test_cell_0()
        except Exception as e:
            assert e.args[0].startswith("Cell execution caused an exception")
            assert e.args[0].endswith("x should have been -1 but was 1")
        else:
            raise Exception("Test should have failed")
        finally:
            t.tearDown()
            t.tearDownClass()
