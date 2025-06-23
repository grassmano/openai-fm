import argparse
import configparser
import datetime
import os
import json
import re # Added for text splitting
import subprocess # Added for playing audio
import tempfile # Added for temporary file for audio playback

from requests import Session

session = Session()

CONFIG_FILE = "config.ini"

def load_config():
    config = configparser.ConfigParser()
    config.read(CONFIG_FILE)
    return config

def split_text_into_chunks(text: str, max_length: int = 990) -> list[str]:
    """
    Splits a long text into chunks, each less than max_length,
    splitting at sentence boundaries.
    """
    if len(text) <= max_length:
        return [text]

    sentences = re.split(r'(?<=[.!?])\s+', text.strip())
    if not sentences:
        return [] # Should not happen with non-empty text

    chunks = []
    current_chunk = ""

    for sentence in sentences:
        if not sentence.strip(): # Skip empty strings that might result from multiple spaces after delimiters
            continue

        # Check if adding the current sentence (plus a space if current_chunk is not empty) exceeds max_length
        # The +1 accounts for a potential space separator when joining sentences.
        if len(current_chunk) + len(sentence) + (1 if current_chunk else 0) > max_length:
            if current_chunk: # If current_chunk has content, add it to chunks
                chunks.append(current_chunk.strip())
                current_chunk = sentence # Start new chunk with current sentence
            else: # Current sentence itself is too long
                # This is a fallback: if a single sentence is longer than max_length,
                # we'll split it hard. This is not ideal but necessary.
                # A more sophisticated approach might try to split at commas or other punctuation.
                # For now, we take the whole sentence as one chunk, exceeding the limit,
                # or we could truncate/error. Let's take it as one chunk.
                # The API will likely fail for this chunk.
                # A better strategy for very long sentences would be to split them further.
                # For now, we'll just add it. User should be warned.
                # Or, if the sentence is truly massive, we might want to split it by words.
                # For simplicity now, if a single sentence is longer than max_length, add it as is.
                # This part of the logic might need refinement based on how the API handles >1000 char inputs for single "sentences".
                # Assuming the API just errors out, it's better to send it and let it error than to mangle the sentence excessively without good rules.

                # If current_chunk is empty and this sentence is too long, it must be added.
                # If it's the *only* sentence, it would have been caught by the initial len(text) check.
                # So, this implies previous sentences fit, but this one doesn't, and current_chunk was just flushed.
                chunks.append(sentence.strip())
                current_chunk = "" # Reset current_chunk as this long sentence forms its own chunk
                continue


        if current_chunk:
            current_chunk += " " + sentence
        else:
            current_chunk = sentence

    if current_chunk: # Add the last remaining chunk
        chunks.append(current_chunk.strip())

    # Post-processing: Check if any chunk is empty and remove.
    # Also, if a chunk was formed by a sentence that itself was too long, it might still be too long.
    # The API limit is 1000.
    # A very long sentence might still exceed this. The current logic adds it as a single chunk.
    # This is a known limitation of this simple splitting.
    # For example: "This is a sentence that is extremely long, much longer than one thousand characters all by itself without any periods or question marks until the very end."
    # The above logic would put this whole thing into one chunk.
    # The problem asks to split at the end of sentences. If a sentence itself is > 1000, we have an issue.
    # The prompt says "split at the end of the sentences and never in the middle of them."
    # This implies if a sentence is > 1000 chars, it's an unsolvable constraint by this rule alone.
    # For now, such a sentence will be a chunk on its own.

    return [c for c in chunks if c]


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

def generate_filename(extension: str = ".wav"):
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"output_{timestamp}{extension}"

def _send_single_request(text: str, voice: str, vibe_prompt: str, play_audio: bool = False, media_player_path: str = None, save_to_file: bool = True):
    # save_to_file parameter added to control file saving, useful for chunk processing
    # play_audio is kept, but for chunks, we'd typically not play individual ones.
    # It returns audio_content if successful, None otherwise.
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
            if play_audio: # Note: play_audio is usually False when called for chunks
                if media_player_path:
                    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp_audio_file:
                        tmp_audio_file.write(audio_content)
                        tmp_filename = tmp_audio_file.name
                    try:
                        print(f"Playing audio with {media_player_path}...")
                        subprocess.run([media_player_path, tmp_filename], check=True)
                    except FileNotFoundError:
                        print(f"Error: Media player '{media_player_path}' not found. Please check your config file or install it.")
                        if save_to_file: # Fallback to saving if play fails and save_to_file is true
                            filename = generate_filename()
                            with open(filename, "wb") as f:
                                f.write(audio_content)
                            print(f"Audio saved to {filename} instead.")
                    except subprocess.CalledProcessError as e:
                        print(f"Error playing audio: {e}")
                        if save_to_file: # Fallback to saving if play fails and save_to_file is true
                            filename = generate_filename()
                            with open(filename, "wb") as f:
                                f.write(audio_content)
                            print(f"Audio saved to {filename} instead.")
                    finally:
                        if os.path.exists(tmp_filename):
                            os.remove(tmp_filename)
                else:
                    print("Media player path not configured. Saving audio instead.")
                    if save_to_file:
                        filename = generate_filename()
                        with open(filename, "wb") as f:
                            f.write(audio_content)
                        print(f"Audio saved to {filename}")
            elif save_to_file: # If not playing, but save_to_file is true
                filename = generate_filename()
                with open(filename, "wb") as f:
                    f.write(audio_content)
                print(f"Audio saved to {filename}")
            return audio_content # Always return audio_content if successful
        else:
            print("Received non-audio response.")
            if response.text:
                print(f"Response text: {response.text}")
            return None
    except Exception as e:
        print(f"An error occurred during the request: {e}")
        return None

def merge_wav_to_opus(wav_files: list[str], opus_output_path: str):
    """
    Merges multiple WAV files into a single Opus file using ffmpeg.
    Placeholder implementation: ffmpeg is required.
    """
    if not wav_files:
        print("No WAV files to merge.")
        return False

    print(f"Attempting to merge {len(wav_files)} WAV file(s) to Opus: {opus_output_path}")
    print("INFO: This step requires ffmpeg. If not installed, this will fail.")

    if len(wav_files) == 1:
        # Just convert this single file to Opus
        input_wav = wav_files[0]
        try:
            subprocess.run(
                ["ffmpeg", "-i", input_wav, "-c:a", "libopus", "-y", opus_output_path],
                check=True, capture_output=True
            )
            print(f"Successfully converted {input_wav} to {opus_output_path}")
            return True
        except FileNotFoundError:
            print("Error: ffmpeg not found. Please install ffmpeg to merge audio.")
            return False
        except subprocess.CalledProcessError as e:
            print(f"Error during ffmpeg conversion: {e}")
            print(f"ffmpeg stdout: {e.stdout.decode()}")
            print(f"ffmpeg stderr: {e.stderr.decode()}")
            return False
    else:
        # Merge multiple WAV files then convert to Opus
        # Create a temporary file list for ffmpeg's concat demuxer
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".txt") as tmp_list_file:
            for wav_file in wav_files:
                tmp_list_file.write(f"file '{os.path.abspath(wav_file)}'\n")
            list_filename = tmp_list_file.name

        merged_wav_temp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
        merged_wav_filename = merged_wav_temp.name
        merged_wav_temp.close() # Close it so ffmpeg can write to it

        try:
            # Concatenate WAV files
            subprocess.run(
                ["ffmpeg", "-f", "concat", "-safe", "0", "-i", list_filename, "-c", "copy", "-y", merged_wav_filename],
                check=True, capture_output=True
            )
            print(f"Successfully concatenated WAV files to {merged_wav_filename}")

            # Convert merged WAV to Opus
            subprocess.run(
                ["ffmpeg", "-i", merged_wav_filename, "-c:a", "libopus", "-y", opus_output_path],
                check=True, capture_output=True
            )
            print(f"Successfully converted merged WAV to {opus_output_path}")
            return True
        except FileNotFoundError:
            print("Error: ffmpeg not found. Please install ffmpeg to merge/convert audio.")
            return False
        except subprocess.CalledProcessError as e:
            print(f"Error during ffmpeg operation: {e}")
            print(f"ffmpeg stdout: {e.stdout.decode()}")
            print(f"ffmpeg stderr: {e.stderr.decode()}")
            return False
        finally:
            if os.path.exists(list_filename):
                os.remove(list_filename)
            if os.path.exists(merged_wav_filename):
                os.remove(merged_wav_filename)


def send_request_and_process_audio(text: str, voice: str, vibe_prompt: str, play_audio: bool, media_player_path: str, output_filename_base: str):
    """
    Handles TTS generation, including splitting long text, generating audio for chunks,
    and merging them into a single Opus file.
    """
    MAX_CHARS = 990 # Max chars per chunk for the API

    if len(text) <= MAX_CHARS:
        print("Input text is short. Processing as a single chunk.")
        audio_content = _send_single_request(text, voice, vibe_prompt, play_audio=False, save_to_file=False) # We handle saving/playing post-conversion
        if audio_content:
            temp_wav_file = None
            try:
                with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp_f:
                    tmp_f.write(audio_content)
                    temp_wav_file = tmp_f.name

                opus_output_path = output_filename_base + ".opus"
                if merge_wav_to_opus([temp_wav_file], opus_output_path):
                    print(f"Successfully generated Opus file: {opus_output_path}")
                    if play_audio:
                        if media_player_path:
                            try:
                                print(f"Playing audio with {media_player_path}...")
                                subprocess.run([media_player_path, opus_output_path], check=True)
                            except FileNotFoundError:
                                print(f"Error: Media player '{media_player_path}' not found. Cannot play Opus file.")
                            except subprocess.CalledProcessError as e:
                                print(f"Error playing Opus file: {e}")
                        else:
                            print("Media player path not configured. Cannot play Opus file.")
                else:
                    print(f"Failed to generate Opus file. Saving original WAV instead.")
                    wav_output_path = output_filename_base + ".wav" # Fallback to WAV
                    os.rename(temp_wav_file, wav_output_path)
                    print(f"Audio saved as WAV: {wav_output_path}")
                    temp_wav_file = None # Avoid double deletion

            finally:
                if temp_wav_file and os.path.exists(temp_wav_file):
                    os.remove(temp_wav_file)
        else:
            print("Failed to retrieve audio for the single chunk.")
    else:
        print(f"Input text is long ({len(text)} chars). Splitting into chunks...")
        chunks = split_text_into_chunks(text, MAX_CHARS)
        if not chunks:
            print("Text splitting resulted in no chunks. Aborting.")
            return

        print(f"Split into {len(chunks)} chunk(s).")
        temp_wav_files = []
        success_all_chunks = True

        for i, chunk in enumerate(chunks):
            print(f"Processing chunk {i+1}/{len(chunks)} ({len(chunk)} chars)...")
            audio_content = _send_single_request(chunk, voice, vibe_prompt, play_audio=False, save_to_file=False)
            if audio_content:
                try:
                    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp_f:
                        tmp_f.write(audio_content)
                        temp_wav_files.append(tmp_f.name)
                    print(f"Chunk {i+1} processed and saved to temporary WAV: {temp_wav_files[-1]}")
                except Exception as e:
                    print(f"Error saving temporary WAV for chunk {i+1}: {e}")
                    success_all_chunks = False
                    break # Stop processing if a temp file can't be saved
            else:
                print(f"Failed to retrieve audio for chunk {i+1}. Aborting further processing.")
                success_all_chunks = False
                break

        if success_all_chunks and temp_wav_files:
            opus_output_path = output_filename_base + ".opus"
            if merge_wav_to_opus(temp_wav_files, opus_output_path):
                print(f"Successfully merged chunks into Opus file: {opus_output_path}")
                # Playing merged audio is not implemented for long texts in this version for simplicity.
                if play_audio:
                    print("Note: Direct playback of long, merged audio is not automatically initiated. Please play the saved Opus file.")
            else:
                print(f"Failed to merge chunks into Opus. Individual WAV chunks (if any) might remain in temp directory or not be saved.")
                print("As a fallback, attempting to save the first chunk if available and others failed, or no merging possible.")
                if temp_wav_files: # Check if there's at least one temp file
                    first_chunk_wav = temp_wav_files[0]
                    fallback_wav_path = output_filename_base + "_chunk1.wav"
                    try:
                        os.rename(first_chunk_wav, fallback_wav_path)
                        print(f"First chunk saved as WAV: {fallback_wav_path}")
                        # Mark it as "moved" so it's not deleted in finally
                        temp_wav_files[0] = None
                    except Exception as e_fallback:
                        print(f"Could not save fallback WAV for the first chunk: {e_fallback}")


        elif not temp_wav_files:
            print("No audio chunks were successfully processed.")

        # Clean up temporary WAV files
        for tmp_f_path in temp_wav_files:
            if tmp_f_path and os.path.exists(tmp_f_path):
                try:
                    os.remove(tmp_f_path)
                    print(f"Cleaned up temporary WAV: {tmp_f_path}")
                except Exception as e_clean:
                    print(f"Error cleaning up temporary file {tmp_f_path}: {e_clean}")


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
        # Generate the base filename without extension
        output_filename_base = generate_filename(extension="") # Get "output_timestamp"
        # Remove the dot if generate_filename still adds one by mistake with empty extension
        if output_filename_base.endswith('.'):
            output_filename_base = output_filename_base[:-1]

        send_request_and_process_audio(
            text_to_speak,
            selected_voice,
            vibe_prompt,
            args.play,
            media_player,
            output_filename_base
        )
    else:
        print("No text provided. Exiting.")

if __name__ == "__main__":
    main()
