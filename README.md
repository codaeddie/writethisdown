# WriteThisDown

Audio capture → OpenAI Whisper → Markdown. That's it.

## What it actually does

This code records audio from your mic when you hit F8, stops when you hit F8 again, then sends the audio to OpenAI's Whisper API to transcribe it. The transcription gets saved as a markdown file with a timestamp. Pretty straightforward.

## Setup

```bash
# Install the dependencies 
pip install -r requirements.txt

# If PyAudio fails on Windows (it often does)
pip install pipwin
pipwin install pyaudio

# Add your OpenAI API key to a .env file
echo "OPENAI_API_KEY=your_actual_key_here" > .env

# Run it
python transcription.py
```

First time you run it, you'll need to pick your mic. It'll remember your choice in `audio_config.json`.

## Controls

- **F8**: Start/stop recording (you'll see audio levels in real-time)
- **M**: Show menu options 
- **ESC**: Quit

The menu (press M) lets you:
1. Start/stop recording (same as F8)
2. View your saved transcriptions 
3. Toggle auto-opening files when done
4. Exit

## Files that matter

- `transcription.py`: The actual program
- `device_finder.py`: Detects/selects audio input devices
- `audio_config.json`: Saves which mic you're using
- `transcription_config.json`: Audio settings and preferences
- `.env`: Your OpenAI API key
- `transcriptions/`: Where your markdown files go

## Config options

Edit `transcription_config.json` if you want to change settings:

```json
{
  "format": 8,          // Audio format (8 = PyAudio.paInt16)
  "channels": 1,        // Mono audio
  "rate": 16000,        // Sample rate (Hz) 
  "chunk": 1024,        // Processing chunk size
  "hotkey": "f8",       // Key to start/stop recording
  "output_dir": "transcriptions", // Where files get saved
  "language": "en",     // Language for transcription
  "auto_open": false,   // Automatically open files when saved
  "min_duration": 1.0   // Minimum recording duration in seconds
}
```

## Troubleshooting

If your mic isn't working:
1. Run `python device_finder.py` to see all available audio devices
2. Delete `audio_config.json` to reset your device preference
3. Run the main script again and pick a different mic

## How it works

1. Records audio frames when F8 is pressed
2. Shows audio levels while recording
3. When F8 is pressed again, saves audio to temp WAV file
4. Sends the WAV to OpenAI Whisper API
5. Formats the returned text and saves as markdown
6. Shows transcription in terminal and saves to file

That's literally it. No magic.
