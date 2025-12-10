from synthesizer import AudioSynthesizer
from score import get_moonlight_sonata_score


def main() -> None:
    """Generate and save the Moonlight Sonata as a WAV file."""
    try:
        synth = AudioSynthesizer(sample_rate=44100)
        score = get_moonlight_sonata_score()
        if not score:
            raise ValueError('Score is empty.')

        print('Synthesizing Moonlight Sonata...')
        samples = synth.synthesize_polyphonic(score, tempo_bpm=66.0)

        output_file = 'moonlight_sonata.wav'
        synth.save_to_wav(samples, output_file)

        duration_sec = len(samples) / synth.sample_rate
        print(f'Successfully generated {output_file} ({duration_sec:.1f} seconds).')
    except Exception as e:
        print(f'Error generating Moonlight Sonata: {e}')
        raise


if __name__ == '__main__':
    main()
