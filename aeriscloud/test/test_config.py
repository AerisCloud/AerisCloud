import os

# not supported in 2.6 :(
# from unittest import skip

from .test_base import TestBase
from ..config import config

FIXTURE_PATH = os.path.join(os.path.dirname(__file__), 'fixtures')


class TestConfig(TestBase):
    def test_aeriscloud_path(self):
        # assert aeriscloud_path == FIXTURE_PATH
        assert config is not None

#    @skip
#    def test_projects_path(self):
#        assert projects_path() == os.path.join(FIXTURE_PATH, 'projects')
