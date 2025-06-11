# quick_transcribe.py - Handle your failed recording locally

import os
import sys
import subprocess
from datetime import datetime

def transcribe_with_local_whisper(audio_file_path):
    """Transcribe using local faster-whisper"""
    try:
        print("Installing faster-whisper if not already installed...")
        subprocess.check_call([sys.executable, '-m', 'pip', 'install', 'faster-whisper'])
        
        from faster_whisper import WhisperModel
        
        print("Loading Whisper model (this might take a moment on first run)...")
        model = WhisperModel("base", device="cpu")  # Change to "cuda" if you have GPU
        
        print("Transcribing...")
        segments, info = model.transcribe(audio_file_path, language="en")
        
        transcription = " ".join([segment.text for segment in segments])
        
        # Save the transcription
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = f"transcription_local_{timestamp}.md"
        
        content = f"# Local Transcription {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
        content += f"Source: {os.path.basename(audio_file_path)}\n\n"
        content += transcription
        
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(content)
        
        print(f"\n✅ Transcription saved to: {output_file}")
        print("\nTranscription:")
        print("-" * 60)
        print(transcription)
        print("-" * 60)
        
        return transcription
        
    except Exception as e:
        print(f"❌ Local transcription failed: {e}")
        return None

if __name__ == "__main__":
    # Look for the most recent failed recording
    transcriptions_dir = "transcriptions"
    
    if not os.path.exists(transcriptions_dir):
        print("No transcriptions directory found!")
        sys.exit(1)
    
    failed_recordings = [f for f in os.listdir(transcriptions_dir) 
                        if f.startswith('failed_recording_') and f.endswith('.wav')]
    
    if not failed_recordings:
        print("No failed recordings found!")
        sys.exit(1)
    
    # Get the most recent failed recording
    failed_recordings.sort(reverse=True)
    latest_recording = os.path.join(transcriptions_dir, failed_recordings[0])
    
    print(f"Found failed recording: {latest_recording}")
    print("Attempting local transcription...")
    
    transcribe_with_local_whisper(latest_recording)
