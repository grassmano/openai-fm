import argparse
import configparser
import datetime
import os
import json
import subprocess # Added for playing audio
import tempfile # Added for temporary file for audio playback

from requests import Session

session = Session()

CONFIG_FILE = "config.ini"

def load_config():
    config = configparser.ConfigParser()
    config.read(CONFIG_FILE)
    return config

def display_choices(choices, choice_type):
    print(f"\nAvailable {choice_type}s:")
    for i, choice in enumerate(choices):
        print(f"{i+1}. {choice}")

def get_user_choice(choices, choice_type):
    while True:
        try:
            choice_index = int(input(f"Enter the number for your desired {choice_type}: ")) - 1
            if 0 <= choice_index < len(choices):
                return choices[choice_index]
            else:
                print(f"Invalid {choice_type} number. Please choose from the list.")
        except ValueError:
            print("Invalid input. Please enter a number.")

def format_vibe_prompt(vibe_name, vibes_data):
    vibe_content = vibes_data.get(vibe_name)
    if vibe_content:
        return "\\n\\n".join(vibe_content) # join vibe lines with double newline
    return None

def generate_filename():
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"output_{timestamp}.wav"

def send_request(text: str, voice: str, vibe_prompt: str, play_audio: bool = False, media_player_path: str = None):
    url = "https://www.openai.fm/api/generate"
    boundary = "----WebKitFormBoundarya027BOtfh6crFn7A"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36",
        "Content-Type": f"multipart/form-data; boundary={boundary}",
        "Accept": "*/*",
        "Origin": "https://www.openai.fm",
        "Sec-Fetch-Site": "same-origin",
        "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Dest": "empty",
        "Referer": "https://www.openai.fm/worker-444eae9e2e1bdd6edd8969f319655e70.js",
        "Accept-Encoding": "gzip, deflate, br",
        "Accept-Language": "en-US,en;q=0.9",
        "Priority": "u=1, i"
    }

    data = []
    for name, value in [
        ("input", text),
        ("prompt", vibe_prompt),
        ("voice", voice.lower()),
        ("vibe", "null")
    ]:
        data.append(f"--{boundary}")
        data.append(f'Content-Disposition: form-data; name="{name}"\r\n') # Added \r\n here
        data.append(value)
    data.append(f"--{boundary}--")
    body = "\r\n".join(data).encode('utf-8') # Join with \r\n and encode to utf-8

    try:
        response = session.post(url, headers=headers, data=body)
        response.raise_for_status()
        if "audio/wav" in response.headers["Content-Type"]:
            audio_content = response.content
            if play_audio:
                if media_player_path:
                    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp_audio_file:
                        tmp_audio_file.write(audio_content)
                        tmp_filename = tmp_audio_file.name
                    try:
                        print(f"Playing audio with {media_player_path}...")
                        subprocess.run([media_player_path, tmp_filename], check=True)
                    except FileNotFoundError:
                        print(f"Error: Media player '{media_player_path}' not found. Please check your config file or install it.")
                        # Fallback to saving
                        filename = generate_filename()
                        with open(filename, "wb") as f:
                            f.write(audio_content)
                        print(f"Audio saved to {filename} instead.")
                    except subprocess.CalledProcessError as e:
                        print(f"Error playing audio: {e}")
                         # Fallback to saving
                        filename = generate_filename()
                        with open(filename, "wb") as f:
                            f.write(audio_content)
                        print(f"Audio saved to {filename} instead.")
                    finally:
                        if os.path.exists(tmp_filename):
                            os.remove(tmp_filename)
                else:
                    print("Media player path not configured. Saving audio instead.")
                    filename = generate_filename()
                    with open(filename, "wb") as f:
                        f.write(audio_content)
                    print(f"Audio saved to {filename}")
            else:
                filename = generate_filename()
                with open(filename, "wb") as f:
                    f.write(audio_content)
                print(f"Audio saved to {filename}")
            return audio_content
        else:
            print("Received non-audio response.")
            if response.text:
                print(f"Response text: {response.text}")
            return None
    except Exception as e:
        print(f"An error occurred during the request: {e}")
        return None

def load_voices():
    try:
        with open("voices.json") as f:
            return json.load(f)["voices"]
    except FileNotFoundError:
        print("Error: voices.json not found.")
        return []
    except json.JSONDecodeError:
        print("Error: Could not decode voices.json.")
        return []

def load_vibes():
    try:
        with open("vibes.json") as f:
            return json.load(f)
    except FileNotFoundError:
        print("Error: vibes.json not found.")
        return {} # Return empty dict for vibes
    except json.JSONDecodeError:
        print("Error: Could not decode vibes.json.")
        return {} # Return empty dict for vibes

def main():
    parser = argparse.ArgumentParser(description="Generate speech using an unofficial OpenAI FM API.")
    parser.add_argument("-v", "--voice", type=str, help="Specify the voice to use.")
    parser.add_argument("-f", "--vibe", type=str, help="Specify the vibe to use.")
    parser.add_argument("-t", "--text", type=str, help="Specify the input text directly.")
    parser.add_argument("--text-file", type=str, help="Specify a file path to read input text from.")
    parser.add_argument("--play", action="store_true", help="Play the audio instead of saving it to a file.")
    args = parser.parse_args()

    config = load_config()
    default_voice = config.get("Defaults", "voice", fallback=None)
    default_vibe = config.get("Defaults", "vibe", fallback=None)
    media_player = config.get("Player", "media_player", fallback=None)

    voices = load_voices()
    if not voices:
        print("No voices available. Exiting.")
        return

    vibes_data = load_vibes()
    if not vibes_data:
        print("No vibes available. Exiting.")
        return
    vibe_choices = list(vibes_data.keys())


    # Determine selected voice
    selected_voice = args.voice
    if not selected_voice and default_voice and default_voice in voices:
        selected_voice = default_voice
        print(f"Using default voice from config: {selected_voice}")
    if not selected_voice or selected_voice not in voices:
        if args.voice and selected_voice not in voices: # User specified an invalid voice
             print(f"Voice '{args.voice}' not found in available voices.")
        display_choices(voices, "voice")
        selected_voice = get_user_choice(voices, "voice")

    # Determine selected vibe
    selected_vibe_name = args.vibe
    if not selected_vibe_name and default_vibe and default_vibe in vibe_choices:
        selected_vibe_name = default_vibe
        print(f"Using default vibe from config: {selected_vibe_name}")
    if not selected_vibe_name or selected_vibe_name not in vibe_choices:
        if args.vibe and selected_vibe_name not in vibe_choices: # User specified an invalid vibe
            print(f"Vibe '{args.vibe}' not found in available vibes.")
        display_choices(vibe_choices, "vibe")
        selected_vibe_name = get_user_choice(vibe_choices, "vibe")

    vibe_prompt = format_vibe_prompt(selected_vibe_name, vibes_data)
    if vibe_prompt is None: # Should ideally not happen if selected_vibe_name is valid
        print(f"Vibe prompt for '{selected_vibe_name}' not found. Using default system prompt.")
        vibe_prompt = "Voice Affect: Calm, composed, and reassuring; project quiet authority and confidence.\\n\\nTone: Sincere, empathetic, and gently authoritative—express genuine apology while conveying competence.\\n\\nPacing: Steady and moderate; unhurried enough to communicate care, yet efficient enough to demonstrate professionalism.\\n\\nEmotion: Genuine empathy and understanding; speak with warmth, especially during apologies (\\\"I'm very sorry for any disruption...\\\").\\n\\nPronunciation: Clear and precise, emphasizing key reassurances (\\\"smoothly,\\\" \\\"quickly,\\\" \\\"promptly\\\") to reinforce confidence.\\n\\nPauses: Brief pauses after offering assistance or requesting details, highlighting willingness to listen and support."

    # Determine text input
    text_to_speak = args.text
    if args.text_file:
        if text_to_speak:
            print("Warning: Both --text and --text-file provided. Using --text-file.")
        try:
            with open(args.text_file, "r", encoding="utf-8") as f:
                text_to_speak = f.read().strip()
            if not text_to_speak:
                print(f"File '{args.text_file}' is empty.")
        except FileNotFoundError:
            print(f"Error: Text file '{args.text_file}' not found.")
            text_to_speak = None # Ensure we prompt if file not found
        except Exception as e:
            print(f"Error reading text file '{args.text_file}': {e}")
            text_to_speak = None

    if not text_to_speak:
        text_to_speak = input("Enter text: ")

    if text_to_speak:
        send_request(text_to_speak, selected_voice, vibe_prompt, args.play, media_player)
    else:
        print("No text provided. Exiting.")

if __name__ == "__main__":
    main()
