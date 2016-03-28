from unittest import TestCase


class TestBase(TestCase):
    @classmethod
    def setUpClass(cls):
        # todo: point config path to our fixture path
        # cls._original_path = config.aeriscloud_path
        # config.aeriscloud_path = os.path.join(
        #     os.path.dirname(__file__), 'fixtures')
        # config.config.load()
        pass

    @classmethod
    def tearDownClass(cls):
        # restore it on teardown
        # os.environ['AERISCLOUD_PATH'] = cls._original_path
        # config.load()
        pass
