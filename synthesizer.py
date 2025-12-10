import math
import os
import wave
import numpy as np
from typing import List, Dict, Union


class AudioSynthesizer:
    """Synthesizer for generating polyphonic music as WAV files using additive sine waves.

    Supports multiple overlapping notes mixed into a timeline.
    Uses a simple attack/release envelope for each note.

    Args:
        sample_rate: Number of samples per second (min 8000, default 44100 Hz).
    """

    SAMPLE_RATE_DEFAULT = 44100
    ATTACK_TIME_SEC = 0.005
    RELEASE_TIME_SEC = 0.1
    PADDING_SEC = 0.1
    MAX_DURATION_SEC = 600.0
    MAX_TOTAL_SAMPLES = int(1e8)
    MAX_NOTE_SAMPLES = int(1e7)
    MIN_SAMPLE_RATE = 8000
    MIN_TEMPO_BPM = 0.1
    MAX_MIDI_NOTE = 127
    MIN_MIDI_NOTE = 0

    def __init__(self, sample_rate: int = SAMPLE_RATE_DEFAULT) -> None:
        """
        Initialize the synthesizer.

        Args:
            sample_rate: Number of samples per second (default 44100 Hz).

        Raises:
            ValueError: If sample_rate <= 0.
        """
        if sample_rate <= 0:
            raise ValueError('Sample rate must be positive.')
        self.sample_rate: int = int(max(sample_rate, self.MIN_SAMPLE_RATE))

    def midi_to_freq(self, midi_note: int) -> float:
        """Convert a MIDI note number to its frequency in Hz (A4=440 Hz).

        Args:
            midi_note: MIDI note number (clamped 0-127).

        Returns:
            Frequency in Hz.
        """
        midi_note = max(self.MIN_MIDI_NOTE, min(int(midi_note), self.MAX_MIDI_NOTE))
        return 440.0 * (2.0 ** ((midi_note - 69) / 12.0))

    def _generate_note(self, freq: float, duration: float, volume: float = 1.0) -> np.ndarray:
        """Generate audio samples for a single note with envelope using vectorized numpy.

        Args:
            freq: Frequency in Hz.
            duration: Duration in seconds (clamped <=60s).
            volume: Amplitude multiplier (0.0 to 1.0).

        Returns:
            numpy float32 array of samples in [-1.0, 1.0].
        """
        duration = min(duration, 60.0)
        num_samples = int(duration * self.sample_rate)
        if num_samples <= 0:
            return np.array([], dtype=np.float32)
        num_samples = min(num_samples, self.MAX_NOTE_SAMPLES)

        i = np.arange(num_samples, dtype=np.float32)
        t = i / self.sample_rate
        wave_value = np.sin(2.0 * np.pi * freq * t)

        attack_samples = max(1, int(self.ATTACK_TIME_SEC * self.sample_rate))
        release_samples = max(1, int(self.RELEASE_TIME_SEC * self.sample_rate))

        attack_end = min(attack_samples, num_samples)
        release_start = max(0, num_samples - release_samples)

        env = np.ones(num_samples, dtype=np.float32)

        # Attack: linear 0 to 1
        if attack_end > 0:
            env[:attack_end] = i[:attack_end] / attack_end

        # Release: linear 1 to ~0 (safe division, handles release_samples==1)
        if release_start < num_samples:
            rel_i = i[release_start:] - release_start
            env[release_start:] = (release_samples - rel_i) / release_samples

        samples = np.clip(volume * env * wave_value, -1.0, 1.0)
        return samples.astype(np.float32)

    def synthesize_polyphonic(
        self, notes: List[Dict[str, Union[int, float]]], tempo_bpm: float
    ) -> np.ndarray:
        """Synthesize a polyphonic score into audio samples.

        Args:
            notes: List of note events with required keys 'midi'(int 0-127), 'start_beat'(float >=0),
                   'duration_beats'(float >0), optional 'velocity'(float 0-1).
            tempo_bpm: Tempo in beats per minute (>0, typical 40-200).

        Returns:
            numpy float32 array of mixed audio samples.

        Raises:
            ValueError: For invalid notes, tempo, or excessive length.
        """
        if not notes:
            return np.array([], dtype=np.float32)

        if tempo_bpm <= 0:
            raise ValueError('tempo_bpm must be positive.')

        # Validate all notes
        required_keys = {'midi', 'start_beat', 'duration_beats'}
        for idx, note in enumerate(notes):
            missing = required_keys - set(note.keys())
            if missing:
                raise ValueError(f'Note {idx} missing keys {missing}: {note}')
            try:
                sb = float(note['start_beat'])
                db = float(note['duration_beats'])
                if sb < 0 or db <= 0:
                    raise ValueError('start_beat >=0 and duration_beats >0 required')
                int(note['midi'])
                if 'velocity' in note:
                    v = float(note['velocity'])
                    if not 0 <= v <= 1:
                        raise ValueError('velocity 0-1 required')
            except (ValueError, TypeError) as ve:
                raise ValueError(f'Invalid note {idx}: {note}. {ve}')

        # Total duration
        max_end_beat = max(
            float(note['start_beat']) + float(note['duration_beats']) for note in notes
        )
        beat_sec = 60.0 / tempo_bpm
        total_sec = min(max_end_beat * beat_sec, self.MAX_DURATION_SEC)
        total_samples = int(total_sec * self.sample_rate) + int(self.PADDING_SEC * self.sample_rate)
        if total_samples > self.MAX_TOTAL_SAMPLES:
            raise ValueError('Score too long: exceeds max samples.')

        timeline: np.ndarray = np.zeros(total_samples, dtype=np.float32)

        for note in notes:
            start_beat = float(note['start_beat'])
            dur_beats = float(note['duration_beats'])
            velocity = float(note.get('velocity', 1.0))
            start_sec = start_beat * beat_sec
            dur_sec = dur_beats * beat_sec
            start_sample = max(0, int(start_sec * self.sample_rate))
            if start_sample >= total_samples:
                continue
            freq = self.midi_to_freq(note['midi'])
            note_samples = self._generate_note(freq, dur_sec, velocity)
            end_sample = min(total_samples, start_sample + len(note_samples))
            mix_len = end_sample - start_sample
            timeline[start_sample:end_sample] += note_samples[:mix_len]

        return timeline

    def save_to_wav(self, samples: np.ndarray, filename: str) -> None:
        """Save audio samples to a 16-bit mono WAV file.

        Normalizes amplitude to avoid clipping. Sanitizes filename to basename.

        Args:
            samples: numpy float32 array or list of float samples.
            filename: Output WAV file path (basename only).

        Raises:
            ValueError: If samples are empty or silent.
            FileNotFoundError: If cannot write to directory.
            RuntimeError: For other errors.
        """
        if hasattr(samples, 'dtype'):
            samples = np.asarray(samples, dtype=np.float32)
        filename = os.path.basename(filename)  # Sanitize: prevent path traversal
        if len(samples) == 0:
            raise ValueError('No samples to save.')
        if np.all(samples == 0):
            raise ValueError('All samples are zero (silent).')

        max_abs = float(np.max(np.abs(samples)))
        scale = 32760.0 / max_abs
        normalized = samples * scale
        int_samples = np.clip(normalized, -32767.0, 32767.0).astype(np.int16)

        try:
            with wave.open(filename, 'wb') as wav_file:
                wav_file.setnchannels(1)
                wav_file.setsampwidth(2)
                wav_file.setframerate(self.sample_rate)
                wav_file.writeframes(int_samples.tobytes())
        except OSError as e:
            if 'No such file or directory' in str(e):
                raise FileNotFoundError(f'Cannot write to directory of {filename}: {e}')
            raise RuntimeError(f'Failed to write WAV file {filename}: {e}')
