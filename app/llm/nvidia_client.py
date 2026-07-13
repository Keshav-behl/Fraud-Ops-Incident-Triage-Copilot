from openai import OpenAI

from app.config import settings

_client = OpenAI(
    base_url=settings.NVIDIA_BASE_URL,
    api_key=settings.NVIDIA_API_KEY,
    timeout=60.0,
    max_retries=2,
)


def chat(messages: list[dict], **kwargs) -> str:
    response = _client.chat.completions.create(
        model=settings.NVIDIA_CHAT_MODEL,
        messages=messages,
        **kwargs,
    )
    return response.choices[0].message.content


def embed(texts: list[str], input_type: str = "passage") -> list[list[float]]:
    """Embed a batch of texts via the NVIDIA NIM embedding endpoint.

    input_type is "passage" for documents being indexed and "query" for
    incoming search text — NV-embedQA models use this to pick the right
    encoder head.
    """
    response = _client.embeddings.create(
        model=settings.NVIDIA_EMBED_MODEL,
        input=texts,
        encoding_format="float",
        extra_body={"input_type": input_type, "truncate": "END"},
    )
    return [item.embedding for item in response.data]
