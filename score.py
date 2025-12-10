from typing import List, Dict, Union


def get_moonlight_sonata_score() -> List[Dict[str, Union[int, float]]]:
    """
    Returns note events approximating the first movement (Adagio sostenuto)
    of Beethoven's Piano Sonata No. 14 Op. 27 No. 2 "Moonlight Sonata".

    Left hand: Iconic C♯ minor arpeggio (C♯2-G♯2-C♯3) in successive staggered triplets
    over TOTAL_BARS bars.

    Right hand: Simple descending melody line inspired by the original theme,
    repeated to fit TOTAL_BEATS.

    Returns:
        List[Dict[str, Union[int, float]]]: Note events with:
            'midi': MIDI note number (int),
            'start_beat': Start time in beats from 0 (float),
            'duration_beats': Duration in beats (float),
            'velocity': Volume 0.0-1.0 (float).
    """
    TOTAL_BARS = 32
    BEATS_PER_BAR = 4.0
    TOTAL_BEATS = TOTAL_BARS * BEATS_PER_BAR
    TRIPLET_DURATION_BEATS = 1.0 / 3.0
    MELODY_PATTERN_SPAN_BEATS = 24.0
    num_melody_repeats = int(TOTAL_BEATS / MELODY_PATTERN_SPAN_BEATS)  # 5

    notes: List[Dict[str, Union[int, float]]] = []

    # Left hand arpeggio: TOTAL_BARS bars, 4 triplets per bar (4 beats/bar)
    for bar in range(TOTAL_BARS):
        base_beat = bar * BEATS_PER_BAR
        for triplet_idx in range(4):
            t = base_beat + triplet_idx * 1.0
            # Staggered successive notes for arpeggio roll effect
            # C♯2 (37), G♯2 (44), C♯3 (49)
            notes.append({
                'midi': 37,
                'start_beat': t + 0.0,
                'duration_beats': TRIPLET_DURATION_BEATS,
                'velocity': 0.7
            })
            notes.append({
                'midi': 44,
                'start_beat': t + TRIPLET_DURATION_BEATS,
                'duration_beats': TRIPLET_DURATION_BEATS,
                'velocity': 0.8
            })
            notes.append({
                'midi': 49,
                'start_beat': t + 2 * TRIPLET_DURATION_BEATS,
                'duration_beats': TRIPLET_DURATION_BEATS,
                'velocity': 0.9
            })

    # Right hand melody approximation (descending line)
    melody_pattern = [
        {'midi': 68, 'start_beat': 0.0, 'duration_beats': 8.0, 'velocity': 0.5},   # G♯4
        {'midi': 66, 'start_beat': 8.0, 'duration_beats': 4.0, 'velocity': 0.5},   # F♯4
        {'midi': 65, 'start_beat': 12.0, 'duration_beats': 2.0, 'velocity': 0.6},  # F4
        {'midi': 64, 'start_beat': 14.0, 'duration_beats': 2.0, 'velocity': 0.6},  # E4
        {'midi': 63, 'start_beat': 16.0, 'duration_beats': 4.0, 'velocity': 0.4},  # D♯4 approx
        {'midi': 61, 'start_beat': 20.0, 'duration_beats': 4.0, 'velocity': 0.5},  # C♯4
    ]
    # Repeat pattern to fit total beats
    for i in range(num_melody_repeats):
        offset = i * MELODY_PATTERN_SPAN_BEATS
        for m in melody_pattern:
            notes.append({
                'midi': m['midi'],
                'start_beat': m['start_beat'] + offset,
                'duration_beats': m['duration_beats'],
                'velocity': m['velocity']
            })

    return notes
