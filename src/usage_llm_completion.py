# import logging
import asyncio

from config.logger import get_logger, setup_logging

# Make sure API keys are set in environment (e.g., from .env)
# from dotenv import load_dotenv
# load_dotenv()
# Example: Ensure OPENAI_API_KEY is set if using an OpenAI model

from llm import create_completion_client, CompletionError  # Use combined __init__


setup_logging()
# logging.getLogger("LiteLLM").setLevel(logging.WARNING)
# logging.getLogger("httpcore").setLevel(logging.WARNING)


async def run_completion_example():
    logger = get_logger(__name__)
    try:
        # Create client using the factory
        client = create_completion_client()
        model_used = client.get_model_name()
        logger.info(f"Using completion model: {model_used}")

        # --- Example 1: Simple prompt ---
        prompt = "Explain the concept of vector databases in simple terms."
        print(f"\n--- Running simple prompt completion for: '{prompt[:50]}...' ---")
        completion = await client.generate_completion(prompt=prompt, max_tokens=150)

        if completion:
            print("\nCompletion Result:")
            print(completion)
        else:
            print("\nFailed to get completion.")

        # --- Example 2: Chat messages ---
        messages = [
            {
                "role": "system",
                "content": "You are a helpful assistant explaining Python concepts.",
            },
            {
                "role": "user",
                "content": "What is the difference between a list and a tuple?",
            },
        ]
        print("\n--- Running chat completion ---")
        chat_completion = await client.generate_completion(
            messages=messages, temperature=0.5
        )

        if chat_completion:
            print("\nChat Completion Result:")
            print(chat_completion)
        else:
            print("\nFailed to get chat completion.")

    except CompletionError as e:
        logger.error(f"A completion error occurred: {e}", exc_info=True)
    except Exception as e:
        logger.error(f"An unexpected error occurred: {e}", exc_info=True)


if __name__ == "__main__":
    asyncio.run(run_completion_example())
