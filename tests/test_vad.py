"""Unit tests for EnergyVAD and AutoStopDetector."""
from __future__ import annotations

import struct
from remi.speech.vad import AutoStopDetector, EnergyVAD


def test_energy_vad_silence():
    vad = EnergyVAD(energy_threshold=300.0)
    # 512 samples of digital zero silence
    silent_pcm = struct.pack("<512h", *([0] * 512))
    score = vad.is_speech(silent_pcm)
    assert score == 0.0


def test_energy_vad_loud_speech():
    vad = EnergyVAD(energy_threshold=300.0)
    # 512 samples of loud sine-wave / amplitude
    loud_samples = [1500 if i % 2 == 0 else -1500 for i in range(512)]
    loud_pcm = struct.pack("<512h", *loud_samples)
    score = vad.is_speech(loud_pcm)
    assert score > 0.5


def test_autostop_detector_cycle():
    detector = AutoStopDetector(
        speech_threshold=0.5,
        min_speech_duration_s=0.05,
        silence_duration_s=0.10,
        sample_rate=16000,
    )

    loud_samples = [2000 if i % 2 == 0 else -2000 for i in range(512)]
    loud_pcm = struct.pack("<512h", *loud_samples)
    silent_pcm = struct.pack("<512h", *([0] * 512))

    # Feed loud speech (approx 32ms per chunk)
    for _ in range(3):
        res = detector.process_chunk(loud_pcm)
        assert not res["is_finished"]

    assert detector._has_spoken is True

    # Feed silence to trigger auto-finish (100ms threshold)
    finished = False
    for _ in range(5):
        res = detector.process_chunk(silent_pcm)
        if res["is_finished"]:
            finished = True
            break

    assert finished is True
