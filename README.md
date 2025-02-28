# WriteThisDown - Audio Transcription Tool

This tool automatically transcribes audio to text in your active text editor using OpenAI's Whisper API.

## Setup Instructions

1. **Install dependencies**:
   ```powershell
   pip install keyboard pyaudio wave pyautogui numpy pydub sounddevice soundfile python-dotenv openai
   ```
   
   If you encounter issues with PyAudio installation:
   ```powershell
   pip install pipwin
   pipwin install pyaudio
   ```

2. **Create a .env file** with your OpenAI API key:
   ```
   OPENAI_API_KEY=your_key_here
   ```

3. **Run the script**:
   ```powershell
   python transcription.py
   ```

4. **Select your HyperX microphone** when prompted. The script will remember your choice for future sessions.

## Usage

1. Open any text editor (Notepad, Typora, etc.)
2. Make sure the text editor window is active with the cursor where you want text to appear
3. Press **F10** to start recording
4. Speak or play audio content
5. Press **F10** again to stop recording
6. Press **ESC** to exit the program completely

## Features

- **Device Selection**: Automatically uses your preferred microphone (HyperX)
- **Global Hotkey**: Ctrl+Shift+J to start/stop recording
- **Real-time Processing**: Audio is captured and processed in chunks for low latency
- **Smart Silence Detection**: Identifies natural pauses to improve transcription
- **Automatic Formatting**: Basic text formatting for improved readability
- **Direct Input**: Types directly into your active window

## Troubleshooting

If your microphone isn't working:
1. Run `device-finder.py` to see all available audio devices
2. Delete `audio_config.json` to reset your device preference
3. Run the main script again to select a new input device

## Files

- `transcription.py`: Main transcription tool
- `device-finder.py`: Standalone utility to list and select audio devices
- `audio_config.json`: Stores your preferred audio device (created automatically)
- `.env`: Contains your OpenAI API key

## Advanced Configuration

You can modify these variables in the script to adjust behavior:

```python
# Audio recording settings
FORMAT = pyaudio.paInt16       # Audio format
CHANNELS = 1                   # Mono audio
RATE = 16000                   # Sample rate (Hz)
CHUNK = 1024                   # Processing chunk size
SILENCE_THRESHOLD = 300        # Amplitude threshold for silence
MIN_SILENCE_LEN = 500          # Min silence duration (ms)
```