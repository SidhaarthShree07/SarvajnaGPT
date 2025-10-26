import os
import subprocess
import tempfile

def generate_voice(text, model_name, voices_dir, output_dir):
    """
    Generate TTS audio using piper.exe directly.
    Args:
        text (str): Text to synthesize.
        model_name (str): Model filename (e.g., 'en_US-lessac-medium.onnx').
        voices_dir (str): Path to voices directory containing piper.exe and models.
        output_dir (str): Path to output directory for wav files.
    Returns:
        output_path (str): Path to generated wav file.
    """
    # Prepare input and output paths
    output_wav = os.path.join(output_dir, f"tts_{abs(hash(text))}.wav")
    piper_exe = os.path.join(voices_dir, "piper.exe")
    model_path = os.path.join(voices_dir, model_name)
    cmd = [
        piper_exe,
        "--model", model_path,
        "--output_file", output_wav
    ]
    # Run command, send text via stdin
    result = subprocess.run(cmd, input=text, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"Piper failed: {result.stderr}")
    return output_wav

if __name__ == "__main__":
    # Example test
    voices_dir = os.path.join(os.path.dirname(__file__), "voices")
    output_dir = tempfile.gettempdir()
    text = "Hello, this is a test of Piper TTS using piper.exe."
    model_name = "en_US-amy-medium.onnx"  # Change as needed
    try:
        wav_path = generate_voice(text, model_name, voices_dir, output_dir)
        print(f"Audio generated: {wav_path}")
    except Exception as e:
        print(f"Error: {e}")
