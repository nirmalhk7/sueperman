"""Executable delivery contract: catches truncated, silent or wrong-format exports."""
import json
from pathlib import Path
import shutil
import subprocess
import unittest

ROOT = Path(__file__).resolve().parent

class DeliveryContract(unittest.TestCase):
    def test_delivery_has_full_hd_video_and_audio_for_ninety_seconds(self):
        video = ROOT / 'sueperman-90s.mp4'
        self.assertTrue(video.is_file(), '90-second MP4 delivery has not been rendered')
        self.assertGreater(video.stat().st_size, 1_000_000, 'delivery is empty or incomplete')
        probe = shutil.which('ffprobe')
        self.assertIsNotNone(probe, 'ffprobe required to verify actual encoded delivery')
        result = subprocess.run([probe, '-v', 'error', '-show_streams', '-show_format', '-of', 'json', str(video)], capture_output=True, text=True, check=True)
        data = json.loads(result.stdout)
        v = next(s for s in data['streams'] if s['codec_type'] == 'video')
        self.assertEqual((v['width'], v['height']), (1920, 1080))
        self.assertEqual(v['r_frame_rate'], '30/1')
        self.assertAlmostEqual(float(data['format']['duration']), 90, delta=0.2)
        a = [s for s in data['streams'] if s['codec_type'] == 'audio']
        self.assertTrue(a, 'delivery must contain synchronized dialogue, score and SFX')
        self.assertGreater(float(a[0]['duration']), 89)
        decode = subprocess.run([shutil.which('ffmpeg'), '-v', 'error', '-i', str(video), '-f', 'null', '-'], capture_output=True, text=True)
        self.assertEqual(decode.returncode, 0, decode.stderr)

if __name__ == '__main__':
    unittest.main()
