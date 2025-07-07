# services/openai_service.py
import openai
from config import OPENAI_API_KEY, SYSTEM_PROMPT, FORMATTED_ORBDENT_KNOWLEDGE

# Ensure API key is set for the OpenAI library
openai.api_key = OPENAI_API_KEY

def get_openai_chat_stream(user_input: str, model_name: str):
    """
    Generates a streaming response from the OpenAI Chat Completion API.
    """
    print(f"🔁 Using OpenAI model: {model_name}")
    try:
        response = openai.ChatCompletion.create(
            model=model_name,
            stream=True,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": FORMATTED_ORBDENT_KNOWLEDGE},
                {"role": "user", "content": user_input}
            ]
        )
        for chunk in response:
            delta = chunk['choices'][0]['delta']
            yield delta.get("content", "")
    except Exception as e:
        yield f"[Feil]: {str(e)}"
