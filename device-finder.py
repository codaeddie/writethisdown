import pyaudio
import json
import os

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

if __name__ == "__main__":
    preferred_device = get_preferred_device()
    print(f"Preferred device ID: {preferred_device}")