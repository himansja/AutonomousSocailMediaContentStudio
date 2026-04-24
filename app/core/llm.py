import os
from dotenv import load_dotenv
from langchain_openai import AzureChatOpenAI

load_dotenv()

_REQUIRED = {
    "AZURE_OPENAI_ENDPOINT": os.getenv("AZURE_OPENAI_ENDPOINT"),
    "AZURE_OPENAI_API_KEY": os.getenv("AZURE_OPENAI_API_KEY"),
    "AZURE_OPENAI_DEPLOYMENT_NAME": os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME"),
    "AZURE_OPENAI_API_VERSION": os.getenv("AZURE_OPENAI_API_VERSION"),
}

_missing = [key for key, val in _REQUIRED.items() if not val]
if _missing:
    raise EnvironmentError(
        f"Missing required environment variable(s): {', '.join(_missing)}. "
        "Set them in your .env file or shell environment before starting the app."
    )

llm = AzureChatOpenAI(
    azure_endpoint=_REQUIRED["AZURE_OPENAI_ENDPOINT"],
    api_key=_REQUIRED["AZURE_OPENAI_API_KEY"],
    azure_deployment=_REQUIRED["AZURE_OPENAI_DEPLOYMENT_NAME"],
    api_version=_REQUIRED["AZURE_OPENAI_API_VERSION"],
    temperature=0.7,
    max_retries=3,
)
