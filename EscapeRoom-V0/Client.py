import asyncio
import logging
import os
import sys

from mcp.client.sse import sse_client
from mcp import ClientSession
from google import genai

# Configure logging to file and console
logging.basicConfig(
    level=logging.INFO,
    format=r'%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler("client.log"),
        logging.StreamHandler(stream=sys.stdout)
    ]
)

# Initialize Gemini client
client = genai.Client(api_key="")  # Replace with your actual API key


async def play_locked_room(server_url: str):
    """
    Play the locked room escape game using the Gemini client and MCP server.
    :param server_url: the URL of the MCP server providing the SSE endpoint
    :return: None | This function runs the game loop until the agent escapes or fails.
    """
    async with sse_client(server_url) as (read_stream, write_stream):
        async with ClientSession(read_stream, write_stream) as session:
            # Initialize the session

            await session.initialize()

            # List available tools
            tools = (await session.list_tools()).tools
            logging.info("Available tools:")
            for t in tools:
                logging.info(r"- %s: %s", t.name, t.description)

            # Simplified chat storage: list of dicts
            chat = []
            chat.append({"role": "user", "content": "You are a game-playing agent in a locked-room escape. Use the available tools to escape. **IMP : Before you are to open the door use the `log_thought(message)` <make sure you only call this function once> with a concise description of your reasoning so far. Then open the door thus winning the game.**"})
            logging.info("Initial chat: %s", chat)

            while True:
                # Convert to Content objects
                contents = [genai.types.Content(role=msg["role"], parts=[{"text": msg["content"]}]) for msg in chat]

                response = await client.aio.models.generate_content(
                    model="gemini-2.5-flash",
                    contents=contents,
                    config=genai.types.GenerateContentConfig(
                        temperature=0.2,
                        tools=[session]
                    )
                )

                # Log tool calls
                if response.function_calls:
                    for call in response.function_calls:
                        logging.info("Tool Call: %s(%s)", call.name, call.arguments)
                else:
                    logging.info("No tool calls in this response.")

                # Append model reply to simplified chat
                msg = response.candidates[0].content
                logging.info("Gemini: %s", msg)
                chat.append({"role": "model", "content": msg})

                # Check for completion and log
                if "You open the door" in str(msg).lower() or "escaped" in str(msg).lower():
                    logging.info("Game Over: Agent escaped the room.")
                    break


if __name__ == "__main__":
    # Get server URL from environment variable or use default
    SERVER_URL = os.getenv("MCP_SERVER_URL", "http://localhost:8050/sse")
    asyncio.run(play_locked_room(SERVER_URL))
