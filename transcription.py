import keyboard
import threading
import pyaudio
import wave
import time
import os
import pyautogui
import numpy as np
import json
from pydub import AudioSegment
from pydub.silence import split_on_silence
import sounddevice as sd
import soundfile as sf
import tempfile
import queue
import sys
from dotenv import load_dotenv
from openai import OpenAI

# Load environment variables from .env file
load_dotenv()

# Configure OpenAI API
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Audio recording settings
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 16000
CHUNK = 1024
SILENCE_THRESHOLD = 300  # Adjust based on your environment
MIN_SILENCE_LEN = 500  # Minimum silence length in ms

# Global variables
recording = False
audio_queue = queue.Queue()
processed_text = ""
preferred_device_id = None

def on_hotkey_press():
    """Handle hotkey press event"""
    global recording
    if not recording:
        start_recording()
    else:
        stop_recording()

def start_recording():
    """Start audio recording and transcription"""
    global recording
    recording = True
    print("Recording started...")
    
    # Start the recording thread
    threading.Thread(target=record_audio, daemon=True).start()
    
    # Start the processing thread
    threading.Thread(target=process_audio_queue, daemon=True).start()
    
    # Add a small delay before typing to prevent unexpected behavior
    time.sleep(0.3)
    # Flash indication that recording has started
    pyautogui.write("[Recording]")

def stop_recording():
    """Stop audio recording"""
    global recording
    recording = False
    print("Recording stopped.")
    
    # Add a small delay before typing to prevent unexpected behavior
    time.sleep(0.3)
    # Flash indication that recording has stopped
    pyautogui.write("\n[Stopped]")

def record_audio():
    """Record audio and add chunks to the queue"""
    global recording, preferred_device_id
    
    p = pyaudio.PyAudio()
    
    stream = p.open(
        format=FORMAT,
        channels=CHANNELS,
        rate=RATE,
        input=True,
        input_device_index=preferred_device_id,
        frames_per_buffer=CHUNK
    )
    
    frames = []
    silence_frames = 0
    
    try:
        while recording:
            data = stream.read(CHUNK, exception_on_overflow=False)
            frames.append(data)
            
            # Add to queue for real-time processing
            audio_queue.put(data)
            
            # Check if we should do an intermediate processing
            audio_array = np.frombuffer(data, dtype=np.int16)
            if np.abs(audio_array).mean() < SILENCE_THRESHOLD:
                silence_frames += 1
            else:
                silence_frames = 0
                
            # If silence is detected for a sufficient duration, process what we have
            if silence_frames > (RATE / CHUNK) * (MIN_SILENCE_LEN / 1000):
                process_frames = frames.copy()
                frames = []
                silence_frames = 0
                threading.Thread(target=transcribe_frames, args=(process_frames,), daemon=True).start()
            
    finally:
        stream.stop_stream()
        stream.close()
        p.terminate()
        
        # Process any remaining audio
        if frames:
            threading.Thread(target=transcribe_frames, args=(frames,), daemon=True).start()

def process_audio_queue():
    """Process audio chunks from the queue"""
    global recording
    
    buffer = []
    last_process_time = time.time()
    
    while recording or not audio_queue.empty():
        try:
            # Get data from queue with timeout
            data = audio_queue.get(timeout=0.5)
            buffer.append(data)
            
            # Process if buffer is large enough or enough time has passed
            current_time = time.time()
            if len(buffer) > (RATE * 3) // CHUNK or current_time - last_process_time > 3:
                process_buffer = buffer.copy()
                buffer = []
                last_process_time = current_time
                threading.Thread(target=transcribe_frames, args=(process_buffer,), daemon=True).start()
                
        except queue.Empty:
            # Queue timeout, check if we should process buffer
            if buffer and (time.time() - last_process_time > 1):
                process_buffer = buffer.copy()
                buffer = []
                last_process_time = time.time()
                threading.Thread(target=transcribe_frames, args=(process_buffer,), daemon=True).start()

def transcribe_frames(frames):
    """Transcribe audio frames using OpenAI Whisper API"""
    if not frames:
        return
    
    # Save frames to a temporary WAV file
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_wav:
        temp_filename = temp_wav.name
        
    wf = wave.open(temp_filename, 'wb')
    wf.setnchannels(CHANNELS)
    wf.setsampwidth(pyaudio.PyAudio().get_sample_size(FORMAT))
    wf.setframerate(RATE)
    wf.writeframes(b''.join(frames))
    wf.close()
    
    try:
        # Transcribe with Whisper API (using new SDK syntax)
        with open(temp_filename, "rb") as audio_file:
            transcript = client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file
            )
        
        # Post-process the text
        transcribed_text = format_text(transcript.text)
        
        # Type the processed text into the active window
        if transcribed_text.strip():
            # Add a small pause before typing to ensure window focus is correct
            time.sleep(0.1)
            pyautogui.write(transcribed_text + " ")
    
    except Exception as e:
        print(f"Transcription error: {e}")
    
    finally:
        # Clean up the temporary file
        try:
            os.unlink(temp_filename)
        except:
            pass

def format_text(text):
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

def get_preferred_device():
    """Get the preferred input device from saved config or prompt user to select one."""
    if os.path.exists('audio_config.json'):
        try:
            with open('audio_config.json', 'r') as f:
                config = json.load(f)
                device_id = config.get('preferred_input_device')
                device_name = config.get('device_name', 'Unknown device')
                
                # Verify device still exists
                p = pyaudio.PyAudio()
                try:
                    device_info = p.get_device_info_by_host_api_device_index(0, device_id)
                    if device_info['maxInputChannels'] > 0:
                        print(f"Using saved input device: {device_name} (ID: {device_id})")
                        p.terminate()
                        return device_id
                except:
                    print(f"Saved device ID {device_id} is no longer available. Please select a new device.")
                p.terminate()
        except:
            print("Error reading config file.")
    
    # If we get here, we need to select a new device
    return list_audio_devices()

def list_audio_devices():
    """List all available audio input devices and save preferences."""
    p = pyaudio.PyAudio()
    info = p.get_host_api_info_by_index(0)
    num_devices = info.get('deviceCount')
    
    devices = []
    
    print("\n=== AVAILABLE AUDIO INPUT DEVICES ===")
    print("ID  | Channels | Device Name")
    print("---------------------------------")
    
    for i in range(0, num_devices):
        device_info = p.get_device_info_by_host_api_device_index(0, i)
        if device_info['maxInputChannels'] > 0:  # Only show input devices
            devices.append({
                'id': i,
                'name': device_info['name'],
                'channels': device_info['maxInputChannels']
            })
            print(f"{i:3} | {device_info['maxInputChannels']:8} | {device_info['name']}")
    
    p.terminate()
    
    # Ask user to select preferred device
    if devices:
        print("\nEnter the ID of your preferred device (e.g., your HyperX mic):")
        try:
            device_id = int(input("> "))
            
            # Validate selection
            valid_ids = [d['id'] for d in devices]
            if device_id not in valid_ids:
                print(f"Invalid selection. Please choose from: {valid_ids}")
                return None
            
            # Find selected device
            selected_device = next(d for d in devices if d['id'] == device_id)
            
            # Save preference to config file
            config = {'preferred_input_device': device_id, 'device_name': selected_device['name']}
            with open('audio_config.json', 'w') as f:
                json.dump(config, f)
            
            print(f"Successfully set {selected_device['name']} as your preferred input device.")
            return device_id
        except ValueError:
            print("Please enter a valid number.")
            return None
    else:
        print("No input devices found.")
        return None

def main():
    print("Real-time Transcription Tool")
    print("Press F10 to start/stop recording")
    print("The transcribed text will be typed into your active window")
    
    # Get preferred audio device
    global preferred_device_id
    preferred_device_id = get_preferred_device()
    
    if preferred_device_id is None:
        print("No audio input device selected. Exiting.")
        return
    
    # Register the hotkey (using F10 as it's unlikely to conflict with other applications)
    keyboard.add_hotkey('f10', on_hotkey_press)
    
    try:
        # Keep the program running
        print("\nTranscription tool is running. Press ESC to exit.")
        keyboard.wait('esc')  # Wait until ESC is pressed to exit
    except KeyboardInterrupt:
        print("Program terminated.")
    finally:
        # Clean up
        keyboard.unhook_all()

if __name__ == "__main__":
    main()