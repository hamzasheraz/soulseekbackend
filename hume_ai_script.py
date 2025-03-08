# Install required packages
from dotenv import load_dotenv 
import asyncio
import base64
import os
import sys
from hume.client import AsyncHumeClient
from hume.empathic_voice.chat.socket_client import ChatConnectOptions, ChatWebsocketConnection
from hume.empathic_voice.chat.types import SubscribeEvent
from hume.core.api_error import ApiError
from hume import MicrophoneInterface, Stream
import sounddevice as sd
from datetime import datetime  # For timestamps

# Load environment variables from .env file
load_dotenv()
load_dotenv(encoding='utf-8')

# Get API keys from .env
HUME_API_KEY = os.getenv("HUME_API_KEY")
HUME_SECRET_KEY = os.getenv("HUME_SECRET_KEY")

# Get the mode from command line arguments
mode = "Calm"  # Default mode
if len(sys.argv) > 1:
    mode = sys.argv[1]

print(f"Starting with mode: {mode}")

# Map therapy modes to their respective config IDs
MODE_CONFIG_MAP = {
    "Calm": os.getenv("HUME_CONFIG_ID_CALM"),
    "Motivation": os.getenv("HUME_CONFIG_ID_MOTIVATION"),
    "Reflection": os.getenv("HUME_CONFIG_ID_REFLECTION"),
    "Crisis": os.getenv("HUME_CONFIG_ID_CRISIS"),
    "Sleep": os.getenv("HUME_CONFIG_ID_SLEEP"),
    "Breathing": os.getenv("HUME_CONFIG_ID_BREATHING"),
    "Grounding": os.getenv("HUME_CONFIG_ID_GROUNDING"),
    "Visualization": os.getenv("HUME_CONFIG_ID_GUIDED"),
    "Gratitude": os.getenv("HUME_CONFIG_ID_GRATITUDE"),
    "Meditation": os.getenv("HUME_CONFIG_ID_MEDITATION")
}

# Get the appropriate config ID based on the mode
HUME_CONFIG_ID = MODE_CONFIG_MAP.get(mode)

# If the specific mode config is not found, use the default
if not HUME_CONFIG_ID:
    HUME_CONFIG_ID = os.getenv("HUME_CONFIG_ID")
    print(f"Config ID for mode {mode} not found, using default: {HUME_CONFIG_ID}")
else:
    print(f"Using config ID for mode {mode}: {HUME_CONFIG_ID}")

# Define the log file path
LOG_FILE_PATH = "conversation_log.txt"

# WebSocketHandler class to manage WebSocket connection and audio stream
class WebSocketHandler:
    def __init__(self):
        self.socket = None
        self.byte_strs = Stream.new()

    def set_socket(self, socket: ChatWebsocketConnection):
        self.socket = socket

    async def on_open(self):
        print("WebSocket connection opened.")
        await log_message(f"Session started with mode: {mode}")

    async def on_message(self, message: SubscribeEvent):
        with open(LOG_FILE_PATH, "a", encoding="utf-8") as log_file:  # Open file in append mode
            if message.type == "chat_metadata":
                pass  # Handle metadata if needed
            elif message.type in ["user_message", "assistant_message"]:
                log_entry = f"{message.message.role.upper()}: {message.message.content}\n"
                log_file.write(log_entry)  # Save message immediately without timestamp
                print(log_entry.strip())
            elif message.type == "audio_output":
                message_bytes = base64.b64decode(message.data.encode("utf-8"))
                await self.byte_strs.put(message_bytes)
            elif message.type == "error":
                error_log = f"Error ({message.code}): {message.message}\n"
                log_file.write(error_log)  # Save error immediately without timestamp
                raise ApiError(error_log)

    async def on_close(self):
        print("WebSocket connection closed.")
        await log_message("Session ended")

    async def on_error(self, error):
        error_message = f"Error: {error}"
        print(error_message)
        await log_message(error_message)

# Function to log messages to the file
async def log_message(message: str):
    timestamp = datetime.now().strftime("[%Y-%m-%d %H:%M:%S]")
    log_entry = f"{timestamp} {message}\n"
    # Append the message to the log file
    with open(LOG_FILE_PATH, "a", encoding="utf-8") as log_file:
        log_file.write(log_entry)

# Main function to authenticate and establish connection
async def main():
    try:
        client = AsyncHumeClient(api_key=HUME_API_KEY)
        options = ChatConnectOptions(config_id=HUME_CONFIG_ID, secret_key=HUME_SECRET_KEY)
        websocket_handler = WebSocketHandler()

        async with client.empathic_voice.chat.connect_with_callbacks(
            options=options,
            on_open=websocket_handler.on_open,
            on_message=websocket_handler.on_message,
            on_close=websocket_handler.on_close,
            on_error=websocket_handler.on_error
        ) as socket:
            websocket_handler.set_socket(socket)
            
            # Start capturing audio from the default microphone and stream it to EVI
            await MicrophoneInterface.start(
                socket,
                allow_user_interrupt=True,
                byte_stream=websocket_handler.byte_strs
            )
    except Exception as e:
        print(f"Error in main function: {str(e)}")
        with open(LOG_FILE_PATH, "a", encoding="utf-8") as log_file:
            log_file.write(f"[ERROR] {str(e)}\n")

# Run the async main function
if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        print(f"Fatal error: {str(e)}")
        with open(LOG_FILE_PATH, "a", encoding="utf-8") as log_file:
            log_file.write(f"[FATAL ERROR] {str(e)}\n")