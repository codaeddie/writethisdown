import keyboard
import pyaudio
import wave
import time
import os
import numpy as np
import json
import tempfile
import sys
import subprocess
from datetime import datetime
from dotenv import load_dotenv
from openai import OpenAI
import logging
import threading

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger("transcription")

# Load environment variables from .env file
load_dotenv()

class TranscriptionTool:
    # Default configuration
    DEFAULT_CONFIG = {
        'format': pyaudio.paInt16,
        'channels': 1,
        'rate': 16000,
        'chunk': 1024,
        'hotkey': 'f8',
        'output_dir': 'transcriptions',  # Directory to save transcriptions
        'language': 'en',                # Default language for transcription
        'auto_open': False,              # Auto-open transcription file when done
        'min_duration': 1.0              # Minimum recording duration in seconds
    }
    
    def __init__(self):
        # Initialize configuration
        self.config = self.DEFAULT_CONFIG.copy()
        self.load_config()
        
        # Initialize OpenAI client
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        if not os.getenv("OPENAI_API_KEY"):
            logger.error("OpenAI API key not found! Please add it to your .env file.")
            sys.exit(1)
        
        # Initialize state variables
        self.recording = False
        self.preferred_device_id = None
        self.frames = []  # Store all audio frames
        self.recording_thread = None
        self.status_thread = None
        self.audio_levels = []  # Store audio levels for display
        
        # Create output directory if it doesn't exist
        os.makedirs(self.config['output_dir'], exist_ok=True)
        
        # Audio processing resources
        self.pyaudio_instance = None
        self.stream = None
    
    def load_config(self):
        """Load configuration from file if it exists"""
        try:
            if os.path.exists('transcription_config.json'):
                with open('transcription_config.json', 'r') as f:
                    user_config = json.load(f)
                    # Update config with user values
                    self.config.update(user_config)
                    logger.info("Configuration loaded successfully")
        except Exception as e:
            logger.error(f"Error loading configuration: {e}")
    
    def save_config(self):
        """Save current configuration to file"""
        try:
            with open('transcription_config.json', 'w') as f:
                json.dump(self.config, f, indent=2)
            logger.info("Configuration saved successfully")
        except Exception as e:
            logger.error(f"Error saving configuration: {e}")
    
    def on_hotkey_press(self):
        """Handle hotkey press event"""
        if not self.recording:
            self.start_recording()
        else:
            self.stop_recording()

    def show_audio_level(self, level):
        """Convert audio level to a visual indicator"""
        max_bars = 20
        level_normalized = min(1.0, level / 10000)  # Normalize level to 0.0-1.0
        bars = int(level_normalized * max_bars)
        return f"[{'█' * bars}{' ' * (max_bars - bars)}] {int(level)}"

    def show_status(self):
        """Show recording status and audio level in the terminal"""
        dots = 0
        max_dots = 3
        update_interval = 0.1  # Update faster for responsive audio meter
        
        while self.recording:
            dots = (dots % max_dots) + 1
            
            # Get the current audio level (or use 0 if no recent levels)
            current_level = 0
            if self.audio_levels:
                current_level = self.audio_levels[-1]
            
            # Create status line with both recording indicator and audio level
            rec_status = f"RECORDING{'.' * dots}{' ' * (max_dots - dots)}"
            level_display = self.show_audio_level(current_level)
            status = f"\r{rec_status} {level_display}"
            
            # Clear line and print status
            print(status, end="", flush=True)
            time.sleep(update_interval)
        
        # Clear status line when done
        print("\r" + " " * 60 + "\r", end="", flush=True)
    
    def start_recording(self):
        """Start audio recording"""
        if self.recording:
            return
        
        self.recording = True
        self.frames = []  # Reset frames
        self.audio_levels = []  # Reset audio levels
        
        print("\n" + "=" * 60)
        print("RECORDING STARTED")
        print("=" * 60)
        logger.info("Recording started...")
        
        # Initialize PyAudio if needed
        if not self.pyaudio_instance:
            self.pyaudio_instance = pyaudio.PyAudio()
        
        # Open audio stream
        try:
            self.stream = self.pyaudio_instance.open(
                format=self.config['format'],
                channels=self.config['channels'],
                rate=self.config['rate'],
                input=True,
                input_device_index=self.preferred_device_id,
                frames_per_buffer=self.config['chunk']
            )
            
            # Start the recording thread
            self.recording_thread = threading.Thread(target=self.record_audio)
            self.recording_thread.daemon = True
            self.recording_thread.start()
            
            # Start the status thread
            self.status_thread = threading.Thread(target=self.show_status)
            self.status_thread.daemon = True
            self.status_thread.start()
            
        except Exception as e:
            self.recording = False
            logger.error(f"Failed to start recording: {e}")
            print(f"ERROR: Failed to start recording: {e}")
    
    def stop_recording(self):
        """Stop audio recording and process the full recording"""
        if not self.recording:
            return
        
        self.recording = False
        print("\n" + "=" * 60)
        print("RECORDING STOPPED")
        print("=" * 60)
        
        # Calculate recording duration
        recording_duration = len(self.frames) * (self.config['chunk'] / self.config['rate'])
        logger.info(f"Recording stopped. Duration: {recording_duration:.2f} seconds ({len(self.frames)} frames)")
        
        # Wait for recording thread to finish
        if self.recording_thread and self.recording_thread.is_alive():
            self.recording_thread.join(timeout=1.0)
        
        # Wait for status thread to finish
        if self.status_thread and self.status_thread.is_alive():
            self.status_thread.join(timeout=1.0)
        
        # Close audio stream
        if self.stream:
            try:
                self.stream.stop_stream()
                self.stream.close()
                self.stream = None
            except Exception as e:
                logger.error(f"Error closing audio stream: {e}")
                print(f"Error closing audio stream: {e}")
        
        # Process the entire recording
        if not self.frames:
            logger.warning("No audio was recorded!")
            print("WARNING: No audio was recorded!")
            return
            
        # Check if recording is too short
        if recording_duration < self.config['min_duration']:
            logger.warning(f"Recording too short ({recording_duration:.2f}s). Minimum duration: {self.config['min_duration']}s")
            print(f"WARNING: Recording too short ({recording_duration:.2f}s). Minimum duration: {self.config['min_duration']}s")
            print("The recording was not processed.")
            return
            
        print("\nProcessing the recording...\n")
        self.process_recording()
    
    def record_audio(self):
        """Record audio and store all frames"""
        try:
            while self.recording and self.stream:
                try:
                    data = self.stream.read(self.config['chunk'], exception_on_overflow=False)
                    self.frames.append(data)
                    
                    # Calculate and store audio level for display
                    audio_array = np.frombuffer(data, dtype=np.int16)
                    audio_level = np.abs(audio_array).mean()
                    self.audio_levels.append(audio_level)
                    
                    # Keep only the last few audio levels to avoid memory bloat
                    if len(self.audio_levels) > 10:
                        self.audio_levels = self.audio_levels[-10:]
                        
                except Exception as e:
                    logger.error(f"Error during recording: {e}")
                    print(f"Error during recording: {e}")
                    break
        except Exception as e:
            logger.error(f"Recording thread error: {e}")
            print(f"Recording thread error: {e}")
    
    def transcribe_locally(self, audio_file_path):
        """Fallback local transcription using faster-whisper"""
        try:
            print("Attempting local transcription with faster-whisper...")
            
            # Check if faster-whisper is installed
            result = subprocess.run([sys.executable, '-c', 'import faster_whisper'], 
                                  capture_output=True, text=True)
            
            if result.returncode != 0:
                print("Installing faster-whisper...")
                subprocess.check_call([sys.executable, '-m', 'pip', 'install', 'faster-whisper'])
            
            # Import after ensuring it's installed
            from faster_whisper import WhisperModel
            
            # Initialize local model (downloads on first use)
            model = WhisperModel("base", device="cpu")  # Use "cuda" if you have GPU
            
            segments, info = model.transcribe(audio_file_path, language=self.config['language'])
            
            # Combine all segments
            transcription = " ".join([segment.text for segment in segments])
            
            logger.info("Local transcription completed successfully")
            return transcription
            
        except Exception as e:
            logger.error(f"Local transcription failed: {e}")
            print(f"Local transcription failed: {e}")
            return None
    
    def process_recording(self):
        """Process the entire recording with smart fallback"""
        temp_filename = None
        self._transcription_successful = False
        
        try:
            # Create a temporary WAV file
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_wav:
                temp_filename = temp_wav.name
            
            logger.info(f"Saving recording to temporary file: {temp_filename}")
            print(f"Saving recording to temporary file...")
            
            # Save all frames to the temporary WAV file
            wf = wave.open(temp_filename, 'wb')
            wf.setnchannels(self.config['channels'])
            wf.setsampwidth(self.pyaudio_instance.get_sample_size(self.config['format']))
            wf.setframerate(self.config['rate'])
            wf.writeframes(b''.join(self.frames))
            wf.close()
            
            # Check file size and warn if too large
            file_size = os.path.getsize(temp_filename)
            if file_size > 25 * 1024 * 1024:  # 25MB limit
                print(f"WARNING: File size ({file_size / 1024 / 1024:.1f}MB) exceeds OpenAI limit (25MB)")
                print("Falling back to local transcription...")
                transcript_text = self.transcribe_locally(temp_filename)
            else:
                # Try OpenAI API first
                logger.info("Sending audio to OpenAI Whisper API...")
                print("Sending audio to OpenAI for transcription...")
                
                try:
                    with open(temp_filename, "rb") as audio_file:
                        transcript = self.client.audio.transcriptions.create(
                            model="whisper-1",
                            file=audio_file,
                            language=self.config['language']
                        )
                    
                    transcript_text = transcript.text
                    
                except Exception as api_error:
                    logger.error(f"OpenAI API error: {api_error}")
                    print(f"OpenAI API failed: {api_error}")
                    print("Falling back to local transcription...")
                    transcript_text = self.transcribe_locally(temp_filename)
            
            # Process the transcription result
            if transcript_text and transcript_text.strip():
                self._transcription_successful = True
                saved_file = self.save_transcription(transcript_text)
                
                if self.config['auto_open'] and saved_file and os.path.exists(saved_file):
                    self.open_file(saved_file)
            else:
                logger.warning("Received empty transcription")
                print("WARNING: Received empty transcription")
                self._transcription_successful = False
        
        except Exception as e:
            logger.error(f"Error processing recording: {e}")
            print(f"ERROR: Error processing recording: {e}")
        
        finally:
            # Cleanup logic
            if temp_filename and os.path.exists(temp_filename):
                if hasattr(self, '_transcription_successful') and self._transcription_successful:
                    try:
                        os.unlink(temp_filename)
                        logger.info("Cleaned up temporary file after successful transcription")
                    except Exception as e:
                        logger.error(f"Error deleting temporary file: {e}")
                else:
                    # Save failed recording to transcriptions directory for manual processing
                    failed_filename = os.path.join(self.config['output_dir'], f"failed_recording_{datetime.now().strftime('%Y%m%d_%H%M%S')}.wav")
                    try:
                        import shutil
                        shutil.move(temp_filename, failed_filename)
                        logger.info(f"Saved failed recording to: {failed_filename}")
                        print(f"\nRecording saved for manual processing: {failed_filename}")
                        print("You can try transcribing this file manually or with other tools.")
                    except Exception as e:
                        logger.error(f"Error saving failed recording: {e}")
                        print(f"ERROR: Could not save recording file: {e}")
                        print(f"Temp file location: {temp_filename}")
    
    def save_transcription(self, text):
        """Save the transcribed text to a file"""
        try:
            # Format the text
            formatted_text = self.format_text(text)
            
            # Create filename with current date and time
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = os.path.join(self.config['output_dir'], f"transcription_{timestamp}.md")
            
            # Format the content
            content = "# Transcription " + datetime.now().strftime("%Y-%m-%d %H:%M:%S") + "\n\n"
            content += formatted_text
            
            # Save to file
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(content)
            
            logger.info(f"Transcription saved to: {filename}")
            
            # Show output in terminal
            print("\n" + "=" * 60)
            print("TRANSCRIPTION COMPLETE")
            print("=" * 60)
            print(f"\nFile saved to: {os.path.abspath(filename)}")
            print("\nTranscription content:")
            print("-" * 60)
            print(formatted_text)
            print("-" * 60 + "\n")
            
            # Ask if user wants to open the file
            if not self.config['auto_open']:
                print("Would you like to open this file? (y/n): ", end="", flush=True)
                response = input().strip().lower()
                if response == 'y':
                    self.open_file(filename)
            
            return filename
            
        except Exception as e:
            logger.error(f"Error saving transcription: {e}")
            print(f"ERROR: Failed to save transcription: {e}")
            return None
    
    def open_file(self, filepath):
        """Open a file with the default application"""
        try:
            # Cross-platform way to open a file
            if sys.platform == 'win32':
                os.startfile(filepath)
            elif sys.platform == 'darwin':  # macOS
                subprocess.run(['open', filepath], check=True)
            else:  # Linux
                subprocess.run(['xdg-open', filepath], check=True)
                
            logger.info(f"Opened file: {filepath}")
        except Exception as e:
            logger.error(f"Error opening file: {e}")
            print(f"ERROR: Could not open file: {e}")
    
    def format_text(self, text):
        """Format the transcribed text for better readability"""
        if not text or not isinstance(text, str):
            return ""
        
        # Basic formatting improvements
        text = text.strip()
        
        # Ensure proper sentence capitalization
        sentences = []
        for sentence in text.split('. '):
            if sentence:
                sentence = sentence[0].upper() + sentence[1:] if len(sentence) > 1 else sentence.upper()
                sentences.append(sentence)
        
        formatted_text = '. '.join(sentences)
        
        # Add period at the end if missing
        if formatted_text and formatted_text[-1] not in ['.', '!', '?']:
            formatted_text += '.'
            
        return formatted_text
    
    def get_preferred_device(self):
        """Get the preferred input device from saved config or prompt user to select one."""
        from device_finder import get_preferred_device
        return get_preferred_device()
    
    def cleanup(self):
        """Clean up resources before exiting"""
        # Stop recording if active
        if self.recording:
            self.stop_recording()
        
        # Close PyAudio instance
        if self.pyaudio_instance:
            self.pyaudio_instance.terminate()
            self.pyaudio_instance = None
        
        # Unhook keyboard
        keyboard.unhook_all()
        
        logger.info("Cleanup completed")
    
    def display_menu(self):
        """Display the menu with options"""
        print("\nOptions:")
        print("  1. Start/stop recording (F8)")
        print("  2. View saved transcriptions")
        print("  3. Toggle auto-open files")
        print("  4. Exit (ESC)")
        print("\nEnter option (1-4): ", end="", flush=True)
        
        choice = input().strip()
        if choice == '1':
            self.on_hotkey_press()
        elif choice == '2':
            self.list_transcriptions()
        elif choice == '3':
            self.toggle_auto_open()
        elif choice == '4':
            return False
        return True
    
    def toggle_auto_open(self):
        """Toggle auto-open setting"""
        self.config['auto_open'] = not self.config['auto_open']
        status = "ON" if self.config['auto_open'] else "OFF"
        print(f"Auto-open files: {status}")
        self.save_config()
    
    def list_transcriptions(self):
        """List and optionally open saved transcriptions"""
        transcriptions = []
        
        for file in os.listdir(self.config['output_dir']):
            if file.startswith('transcription_') and file.endswith('.md'):
                filepath = os.path.join(self.config['output_dir'], file)
                stats = os.stat(filepath)
                transcriptions.append((file, filepath, stats.st_mtime))
        
        if not transcriptions:
            print("\nNo transcriptions found.")
            return
        
        # Sort by modification time (newest first)
        transcriptions.sort(key=lambda x: x[2], reverse=True)
        
        print("\nSaved Transcriptions:")
        print("-" * 60)
        for i, (file, path, mtime) in enumerate(transcriptions, 1):
            time_str = datetime.fromtimestamp(mtime).strftime("%Y-%m-%d %H:%M:%S")
            print(f"{i}. {file} - {time_str}")
        
        print("\nEnter number to open, or 0 to return: ", end="", flush=True)
        choice = input().strip()
        
        if choice == '0':
            return
        
        try:
            index = int(choice) - 1
            if 0 <= index < len(transcriptions):
                self.open_file(transcriptions[index][1])
            else:
                print("Invalid selection.")
        except ValueError:
            print("Please enter a number.")
    
    def run(self):
        """Main function to run the transcription tool"""
        print("\n" + "=" * 60)
        print("WRITE THIS DOWN - AUDIO TRANSCRIPTION TOOL")
        print("=" * 60)
        print(f"\nPress {self.config['hotkey'].upper()} to start/stop recording")
        print(f"Transcriptions will be saved to the '{self.config['output_dir']}' directory")
        print("Press ESC to exit or M to show menu")
        
        logger.info("Real-time Transcription Tool started")
        
        # Get preferred audio device
        self.preferred_device_id = self.get_preferred_device()
        
        if self.preferred_device_id is None:
            logger.error("No audio input device selected. Exiting.")
            print("ERROR: No audio input device selected. Exiting.")
            return
        
        # Register the hotkeys
        keyboard.add_hotkey(self.config['hotkey'], self.on_hotkey_press)
        keyboard.add_hotkey('m', self.display_menu)
        
        try:
            # Keep the program running
            keyboard.wait('esc')  # Wait until ESC is pressed to exit
        except KeyboardInterrupt:
            logger.info("Program terminated by user.")
            print("\nProgram terminated by user.")
        finally:
            # Clean up resources
            self.cleanup()
            print("\nCleanup completed. Goodbye!")

if __name__ == "__main__":
    tool = TranscriptionTool()
    tool.run()