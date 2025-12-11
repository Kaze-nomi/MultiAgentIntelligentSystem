import unittest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from music_composer_agent.models import MusicalComposition
from music_composer_agent.server import MusicComposerAgent
from music_composer_agent.interfaces import IMusicComposer
from music_composer_agent.services import OpenRouterMCPService
from music_composer_agent.exceptions import CompositionGenerationError


class TestMusicalComposition(unittest.TestCase):
    """Test cases for the MusicalComposition."""

    def test_initialization_valid(self):
        """Test valid initialization of MusicalComposition."""
        composition = MusicalComposition(
            title="Test Waltz",
            composer="Test Composer",
            notes=["C4", "D4", "E4"],
            tempo=120,
            key="C major"
        )
        self.assertEqual(composition.title, "Test Waltz")
        self.assertEqual(composition.composer, "Test Composer")
        self.assertEqual(composition.notes, ["C4", "D4", "E4"])
        self.assertEqual(composition.tempo, 120)
        self.assertEqual(composition.key, "C major")

    def test_initialization_invalid_tempo(self):
        """Test invalid tempo raises ValueError."""
        with self.assertRaises(ValueError):
            MusicalComposition(
                title="Test",
                composer="Test",
                notes=["C4"],
                tempo=-10,
                key="C"
            )

    def test_to_dict(self):
        """Test to_dict method."""
        composition = MusicalComposition(
            title="Waltz",
            composer="Schubert",
            notes=["E4", "G4", "B4"],
            tempo=100,
            key="E minor"
        )
        expected = {
            "title": "Waltz",
            "composer": "Schubert",
            "key": "E minor",
            "tempo": 100,
            "genre": None,
            "notes": ["E4", "G4", "B4"],
            "metadata": {},
        }
        self.assertEqual(composition.to_dict(), expected)

    def test_from_dict(self):
        """Test from_dict class method."""
        data = {
            "title": "Waltz",
            "composer": "Schubert",
            "notes": ["E4", "G4", "B4"],
            "tempo": 100,
            "key": "E minor",
        }
        composition = MusicalComposition.from_dict(data)
        self.assertEqual(composition.title, "Waltz")
        self.assertEqual(composition.composer, "Schubert")
        self.assertEqual(composition.notes, ["E4", "G4", "B4"])
        self.assertEqual(composition.tempo, 100)
        self.assertEqual(composition.key, "E minor")


class TestMusicComposerAgent(unittest.TestCase):
    """Test cases for the MusicComposerAgent."""

    def setUp(self):
        """Set up test fixtures."""
        self.mock_llm = Mock(spec=OpenRouterMCPService)
        self.agent = MusicComposerAgent(llm_service=self.mock_llm, api_key="test_key")

    @patch('music_composer_agent.server.OpenRouterMCPService.generate', new_callable=AsyncMock)
    def test_generate_composition(self, mock_generate):
        """Test generate_composition method."""
        mock_generate.return_value = {
            "title": "Schubert's Waltz in E minor",
            "composer": "Franz Schubert",
            "notes": ["E4", "G4", "B4", "E5", "G5", "B5"],
            "tempo": 120,
            "key": "E minor",
            "genre": "Waltz",
        }
        async def run_test():
            composition = await self.agent.generate_composition("Write a waltz in E minor by Schubert", key="E minor")
            self.assertIsInstance(composition, MusicalComposition)
            self.assertEqual(composition.title, "Schubert's Waltz in E minor")
            self.assertEqual(composition.key, "E minor")
        asyncio.run(run_test())

    def test_validate_composition_valid(self):
        """Test validate_composition with valid composition."""
        composition = MusicalComposition(
            title="Valid Waltz",
            composer="Composer",
            notes=["C4", "D4", "E4"],
            tempo=100,
            key="C major"
        )
        self.assertTrue(self.agent.validate_composition(composition))

    def test_validate_composition_invalid(self):
        """Test validate_composition with invalid composition."""
        with self.assertRaises(TypeError):
            self.agent.validate_composition("invalid")


class TestIMusicComposer(unittest.TestCase):
    """Test cases for the IMusicComposer interface."""

    def setUp(self):
        """Set up test fixtures with a mock implementation."""
        self.mock_composer = Mock(spec=IMusicComposer)

    def test_generate_composition_interface(self):
        """Test that generate_composition is called correctly."""
        prompt = "Compose a melody"
        self.mock_composer.generate_composition = AsyncMock(return_value=Mock(spec=MusicalComposition))
        async def run_test():
            result = await self.mock_composer.generate_composition(prompt)
            self.mock_composer.generate_composition.assert_called_once_with(prompt, key="C minor")
            self.assertIsInstance(result, Mock)
        asyncio.run(run_test())

    def test_validate_composition_interface(self):
        """Test that validate_composition is called correctly."""
        composition = Mock(spec=MusicalComposition)
        self.mock_composer.validate_composer.validate_composition.return_value = True
        result = self.mock_composer.validate_composition(composition)
        self.mock_composer.validate_composition.assert_called_once_with(composition)
        self.assertTrue(result)


if __name__ == '__main__':
    unittest.main()
