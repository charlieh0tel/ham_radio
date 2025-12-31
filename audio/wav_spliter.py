#!/usr/bin/env python3
"""
WAV File Splitter
Splits WAV audio files into multiple segments by duration or number of parts.
"""

import wave
import os
import argparse
from pathlib import Path


def get_wav_info(wav_file):
    with wave.open(wav_file, "rb") as wav:
        params = wav.getparams()
        n_channels = params.nchannels
        sampwidth = params.sampwidth
        framerate = params.framerate
        n_frames = params.nframes
        duration = n_frames / float(framerate)

        print(f"WAV File Info:")
        print(f"  Channels: {n_channels}")
        print(f"  Sample Width: {sampwidth} bytes")
        print(f"  Frame Rate: {framerate} Hz")
        print(f"  Total Frames: {n_frames}")
        print(f"  Duration: {duration:.2f} seconds")

        return params, duration


def split_wav_by_duration(input_file, segment_duration, output_dir=None):
    """
    Split a WAV file into segments of specified duration.

    Args:
        input_file: Path to input WAV file
        segment_duration: Duration of each segment in seconds
        output_dir: Output directory (defaults to same as input file)
    """
    input_path = Path(input_file)
    if output_dir is None:
        output_dir = input_path.parent
    else:
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

    with wave.open(str(input_path), "rb") as wav:
        params = wav.getparams()
        framerate = params.framerate
        n_frames = params.nframes

        frames_per_segment = int(segment_duration * framerate)
        total_segments = (n_frames + frames_per_segment - 1) // frames_per_segment

        print(
            f"\nSplitting into {total_segments} segments of"
            f"{segment_duration}s each..."
        )

        for i in range(total_segments):
            start_frame = i * frames_per_segment
            wav.setpos(start_frame)

            frames_to_read = min(frames_per_segment, n_frames - start_frame)
            frames = wav.readframes(frames_to_read)

            base_name = input_path.stem
            output_file = output_dir / f"{base_name}_part{i+1:03d}.wav"

            with wave.open(str(output_file), "wb") as output_wav:
                output_wav.setparams(params)
                output_wav.writeframes(frames)

            actual_duration = frames_to_read / float(framerate)
            print(f"  Created: {output_file.name} ({actual_duration:.2f}s)")


def split_wav_by_count(input_file, num_parts, output_dir=None):
    """
    Split a WAV file into a specified number of parts.

    Args:
        input_file: Path to input WAV file
        num_parts: Number of parts to split into
        output_dir: Output directory (defaults to same as input file)
    """
    input_path = Path(input_file)
    if output_dir is None:
        output_dir = input_path.parent
    else:
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

    with wave.open(str(input_path), "rb") as wav:
        params = wav.getparams()
        framerate = params.framerate
        n_frames = params.nframes

        frames_per_part = n_frames // num_parts

        print(f"\nSplitting into {num_parts} parts...")

        for i in range(num_parts):
            start_frame = i * frames_per_part
            wav.setpos(start_frame)

            if i == num_parts - 1:
                frames_to_read = n_frames - start_frame
            else:
                frames_to_read = frames_per_part

            frames = wav.readframes(frames_to_read)

            base_name = input_path.stem
            output_file = output_dir / f"{base_name}_part{i+1:03d}.wav"

            with wave.open(str(output_file), "wb") as output_wav:
                output_wav.setparams(params)
                output_wav.writeframes(frames)

            duration = frames_to_read / float(framerate)
            print(f"  Created: {output_file.name} ({duration:.2f}s)")


def main():
    parser = argparse.ArgumentParser(
        description="Split WAV audio files into multiple segments",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Split into 30-second segments
  python wav_splitter.py input.wav -d 30
  
  # Split into 5 equal parts
  python wav_splitter.py input.wav -n 5
  
  # Split with custom output directory
  python wav_splitter.py input.wav -d 60 -o output_folder/
  
  # Show file info only
  python wav_splitter.py input.wav -i
        """,
    )

    parser.add_argument("input_file", help="Input WAV file to split")
    parser.add_argument(
        "-d", "--duration", type=float, help="Duration of each segment in seconds"
    )
    parser.add_argument(
        "-n", "--num-parts", type=int, help="Number of parts to split into"
    )
    parser.add_argument(
        "-o",
        "--output-dir",
        help="Output directory for split files (default: same as input)",
    )
    parser.add_argument(
        "-i", "--info", action="store_true", help="Show file info only, do not split"
    )

    args = parser.parse_args()

    if not os.path.exists(args.input_file):
        print(f"Error: File '{args.input_file}' not found")
        return 1

    params, duration = get_wav_info(args.input_file)

    if args.info:
        return 0

    if not args.duration and not args.num_parts:
        print("\nError: Must specify either --duration (-d) or --num-parts (-n)")
        parser.print_help()
        return 1

    if args.duration and args.num_parts:
        print("\nError: Cannot specify both --duration and --num-parts")
        return 1

    if args.duration:
        if args.duration <= 0:
            print("Error: Duration must be positive")
            return 1
        split_wav_by_duration(args.input_file, args.duration, args.output_dir)
    else:
        if args.num_parts <= 0:
            print("Error: Number of parts must be positive")
            return 1
        split_wav_by_count(args.input_file, args.num_parts, args.output_dir)

    return 0


if __name__ == "__main__":
    exit(main())
