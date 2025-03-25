# WriteThisDown - Audio Transcription Tool

A simple tool to record audio and transcribe it to text using OpenAI's Whisper API.

## Setup Instructions

1. **Install dependencies**:
   ```powershell
   pip install -r requirements.txt
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

4. **Select your microphone** when prompted. The script will remember your choice for future sessions.

## Usage

1. Press **F8** to start recording (you'll see audio levels in real-time)
2. Speak or play audio content
3. Press **F8** again to stop recording and process the transcription
4. The transcription will be saved to a dated Markdown file in the `transcriptions` directory
5. Press **M** to access additional options (view saved transcriptions, toggle settings)
6. Press **ESC** to exit the program

## Features

- **Device Selection**: Automatically uses your preferred microphone
- **Global Hotkey**: F8 to start/stop recording
- **Audio Level Meter**: Visual indicator of audio levels during recording
- **Complete Recordings**: Records continuously, then processes the entire recording at once
- **Automatic Formatting**: Basic text formatting for improved readability
- **Markdown Output**: Saves transcriptions with titles and timestamps as Markdown files
- **Terminal Feedback**: Shows recording status, processing progress, and final transcription
- **File Management**: View and open saved transcriptions
- **Configurable Settings**: Toggle auto-open files and other options

## Menu Options

Press **M** during the program to access additional options:
1. Start/stop recording (same as F8)
2. View saved transcriptions
3. Toggle auto-open files when transcription completes
4. Exit the program

## Troubleshooting

If your microphone isn't working:
1. Run `python device_finder.py` to see all available audio devices
2. Delete `audio_config.json` to reset your device preference
3. Run the main script again to select a new input device

## Files

- `transcription.py`: Main transcription tool
- `device_finder.py`: Standalone utility to list and select audio devices
- `audio_config.json`: Stores your preferred audio device (created automatically)
- `transcription_config.json`: Contains configuration settings
- `.env`: Contains your OpenAI API key
- `requirements.txt`: List of Python dependencies

## Advanced Configuration

You can modify the settings in `transcription_config.json` to adjust behavior:

```json
{
  "format": 8,          // Audio format (8 = PyAudio.paInt16)
  "channels": 1,        // Mono audio
  "rate": 16000,        // Sample rate (Hz)
  "chunk": 1024,        // Processing chunk size
  "hotkey": "f8",       // Hotkey to start/stop recording
  "output_dir": "transcriptions", // Directory to save output files
  "language": "en",     // Language for transcription (default: English)
  "auto_open": false,   // Automatically open files when saved
  "min_duration": 1.0   // Minimum recording duration in seconds
}
```
