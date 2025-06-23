# OpenAI FM API

A Python implementation for interacting with the unofficial OpenAI FM text-to-speech service. This project provides a command-line interface to generate audio from text using a variety of voices and emotional vibes, with support for configuration files and direct audio playback.

## Features

- **Voice Selection**: Choose from a list of available voices dynamically loaded from `voices.json`. Can be set via command-line or `config.ini`.
- **Vibe Customization**: Select from a wide range of vibes or emotional styles, loaded from `vibes.json`. Can be set via command-line or `config.ini`.
- **Flexible Text Input**: Provide text via command-line argument (`-t`), from a file (`--text-file`), or through interactive input.
- **Audio Output Options**:
    - **Save to WAV**: Saves the generated audio directly to a WAV file.
    - **Direct Playback**: Play the audio using a configured media player (`--play`).
- **Configuration File**: Use `config.ini` to set default voice, vibe, and media player.
- **Dynamic Prompt Formatting**: Utilizes vibe descriptions to format the prompt sent to the API.
- **User-Friendly Interface**: Supports both command-line automation and interactive fallback.

## File Structure

- `main.py`: The main Python script for interacting with the OpenAI FM API.
- `voices.json`: Lists available voice options.
- `vibes.json`: Contains configurations for voice vibes.
- `config.ini`: Configuration file for default settings (voice, vibe, media player).
- `README.md`: This documentation file.
- `LICENSE`: Project license.

## Installation

1.  **Clone the repository:**
    ```bash
    git clone <repository-url>
    cd <repository-directory>
    ```
2.  **Install dependencies:**
    The script requires the `requests` library.
    ```bash
    pip install requests
    ```

## Configuration (`config.ini`)

Create a `config.ini` file in the same directory as `main.py` to set your preferences:

```ini
[Defaults]
# Specify the default voice if not provided via command line.
# Must match a name in voices.json (e.g., Default, Aurora)
voice = Default

# Specify the default vibe if not provided via command line.
# Must match a key in vibes.json (e.g., Default Vibe, Cheerful)
vibe = Default Vibe

[Player]
# Command or path to your media player for the --play option.
# Examples: vlc, "C:\Program Files\VideoLAN\VLC\vlc.exe", /usr/bin/cvlc, "ffplay -autoexit -nodisp"
# If empty or player not found, audio will be saved instead.
media_player =
```

## Usage

The script can be run with various command-line arguments for automation or without arguments for an interactive session.

### Command-Line Arguments

*   `-h, --help`: Show help message and exit.
*   `-v VOICE, --voice VOICE`: Specify the voice to use (e.g., "Aurora"). Overrides `config.ini`.
*   `-f VIBE, --vibe VIBE`: Specify the vibe to use (e.g., "Cheerful"). Overrides `config.ini`.
*   `-t TEXT, --text TEXT`: Specify the input text directly.
*   `--text-file TEXT_FILE`: Specify a file path to read input text from.
*   `--play`: Play the audio using the configured media player instead of saving to a file.

### Examples

1.  **Interactive Mode** (prompts for voice, vibe, and text if not set by args or config):
    ```bash
    python main.py
    ```

2.  **Specify Voice, Vibe, and Text:**
    ```bash
    python main.py -v Aurora -f Cheerful -t "Hello world, this is a test!"
    ```

3.  **Use Default Voice/Vibe from `config.ini` and Provide Text:**
    ```bash
    python main.py -t "Using default settings for voice and vibe."
    ```

4.  **Read Text from a File:**
    ```bash
    python main.py --text-file input.txt
    ```

5.  **Play Audio Directly (requires `media_player` in `config.ini`):**
    ```bash
    python main.py -t "Play this message for me." --play
    ```
    If `media_player` in `config.ini` is set to `vlc`, this would attempt to play the audio using VLC.

6.  **Combine Options:**
    ```bash
    python main.py -v "Shimmer" --text-file "story.txt" --play
    ```

## Implementation Details

- **Request Format**:
  - The script sends POST requests to the `https://www.openai.fm/api/generate` endpoint.
  - It uses `multipart/form-data` to send text input, voice, and prompt information to the API.

- **Headers**:
  - The following headers are included in the requests:
    ```
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36",
    "Content-Type": "multipart/form-data; boundary=----WebKitFormBoundarya027BOtfh6crFn7A",
    "Accept": "*/*",
    "Origin": "https://www.openai.fm",
    "Sec-Fetch-Site": "same-origin",
    "Sec-Fetch-Mode": "cors",
    "Sec-Fetch-Dest": "empty",
    "Referer": "https://www.openai.fm/worker-444eae9e2e1bdd6edd8969f319655e70.js",
    "Accept-Encoding": "gzip, deflate, br",
    "Accept-Language": "en-US,en;q=0.9",
    "Priority": "u=1, i"
    ```

- **Response Handling**:
  - The script checks the `Content-Type` in the response headers for `audio/wav` to ensure that a WAV audio file is returned.
  - If the response is a WAV file, it saves the content to a file.
  - Errors during the API request are caught and printed to the console.

- **File Saving Functionality**:
  - Audio files are saved with a timestamped filename (e.g., `output_YYYYMMDD_HHMMSS.wav`) in the same directory as the script.
  - The filename is generated using the `datetime` module to ensure uniqueness.

## Usage Examples

1. **Basic Usage**:
   Run `python main.py` from your terminal. The script will guide you through voice and vibe selection, and prompt you to enter text for speech generation.

2. **Voice Selection**:
   The script displays a numbered list of voices from `voices.json`. Enter the number corresponding to your desired voice when prompted.

3. **Vibe Customization**:
   Similarly, the script lists available vibes from `vibes.json`. Choose a vibe by entering its corresponding number to apply a specific emotional tone to the voice.

4. **Output Handling**:
   After successful audio generation, the script saves the audio as a `.wav` file and prints a confirmation message to the console, indicating the filename and successful save.

## Technical Details

- **API Endpoint**: `https://www.openai.fm/api/generate`
- **Request/Response Format**: `multipart/form-data` for requests, `audio/wav` for successful responses.
- **Headers Required**: Specific headers are needed to mimic browser requests to the OpenAI FM API (see 'Headers' section above).
- **File Handling**: Utilizes Python's `requests` library for API calls, `configparser` for INI files, `subprocess` for media player interaction, and standard file operations.

## Key Functions (in `main.py`)

- **`load_config()`**: Reads `config.ini` to get default settings.
- **`display_choices(choices, choice_type)`**: Shows available voices or vibes.
- **`get_user_choice(choices, choice_type)`**: Handles interactive selection of voice/vibe.
- **`format_vibe_prompt(vibe_name, vibes_data)`**: Prepares the vibe prompt for the API.
- **`generate_filename()`**: Creates unique filenames for saved audio.
- **`send_request(text, voice, vibe_prompt, play_audio, media_player_path)`**:
  - Manages the API call to OpenAI FM.
  - Handles audio content: either saves it to a file or plays it using the specified `media_player_path` via a temporary file.
- **`load_voices()`**: Loads voices from `voices.json`.
- **`load_vibes()`**: Loads vibes from `vibes.json`.
- **`main()`**:
  - Parses command-line arguments (`argparse`).
  - Manages the overall workflow:
    - Determines voice, vibe, and text input (from args, config, or interactive prompts).
    - Calls `send_request` to generate and handle audio.

## Dependencies

- **Python**: 3.6 or higher.
- **requests**: Install using `pip install requests`.

## Legal Disclaimer

This project is intended for educational and personal use only. It is not affiliated with, endorsed by, or officially supported by OpenAI. Use of the OpenAI FM API is subject to their terms of service. Reverse engineering was employed to understand the API for the purpose of creating this tool. Please ensure your usage complies with all applicable terms and legal standards.

---

## Donation

Your support is appreciated:

- **USDt (TRC20)**: `TGCVbSSJbwL5nyXqMuKY839LJ5q5ygn2uS`
- **BTC**: `13GS1ixn2uQAmFQkte6qA5p1MQtMXre6MT`
- **ETH (ERC20)**: `0xdbc7a7dafbb333773a5866ccf7a74da15ee654cc`
- **LTC**: `Ldb6SDxUMEdYQQfRhSA3zi4dCUtfUdsPou`

## Author and Contact

- **GitHub**: [FairyRoot](https://github.com/fairy-root)
- **Telegram**: [@FairyRoot](https://t.me/FairyRoot)

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.

## Contributing

Contributions are welcome! Please open an issue or submit a pull request for any improvements or features.

