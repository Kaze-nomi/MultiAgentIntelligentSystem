import unittest
from arbuz_speaker.arbuz_speaker import ArbuzSpeaker
from arbuz_speaker.interfaces import ISpeaker
from arbuz_speaker.models import ArbuzSpeakerModel


class TestArbuzSpeaker(unittest.TestCase):
    """Test cases for the ArbuzSpeaker class."""

    def setUp(self):
        """Set up test fixtures before each test method."""
        self.speaker = ArbuzSpeaker()

    def tearDown(self):
        """Clean up after each test to reset singleton for isolation."""
        # Reset singleton instance for test isolation
        ArbuzSpeaker._instance = None

    def test_say_arbuz_returns_arbuz(self):
        """Test that say_arbuz method returns the string 'arbuz'."""
        result = self.speaker.say_arbuz()
        self.assertEqual(result, 'arbuz')

    def test_singleton_behavior(self):
        """Test that ArbuzSpeaker follows singleton pattern."""
        another_speaker = ArbuzSpeaker()
        self.assertIs(self.speaker, another_speaker)

    def test_implements_ispeaker(self):
        """Test that ArbuzSpeaker implements ISpeaker interface."""
        self.assertIsInstance(self.speaker, ISpeaker)


class TestArbuzSpeakerModel(unittest.TestCase):
    """Test cases for the ArbuzSpeakerModel class."""

    def test_default_word(self):
        """Test that the model has default word 'arbuz'."""
        model = ArbuzSpeakerModel()
        self.assertEqual(model.word, 'arbuz')

    def test_custom_word(self):
        """Test setting a custom word."""
        model = ArbuzSpeakerModel(word="custom")
        self.assertEqual(model.word, 'custom')


class TestISpeaker(unittest.TestCase):
    """Test cases for the ISpeaker interface."""

    def test_interface_has_say_arbuz_method(self):
        """Test that ISpeaker has the say_arbuz method."""
        # Check if the method exists
        self.assertTrue(hasattr(ISpeaker, 'say_arbuz'))
        # Check if it's a callable method
        self.assertTrue(callable(getattr(ISpeaker, 'say_arbuz')))

    def test_arbuz_speaker_implements_interface(self):
        """Test that ArbuzSpeaker properly implements ISpeaker."""
        speaker = ArbuzSpeaker()
        # Ensure it has the method
        self.assertTrue(hasattr(speaker, 'say_arbuz'))
        # Ensure the method returns a string
        result = speaker.say_arbuz()
        self.assertIsInstance(result, str)


if __name__ == '__main__':
    unittest.main()
