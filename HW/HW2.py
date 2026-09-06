"""
HW2 — URL Summarizer with Multiple LLMs.

The user enters a web page URL at the top of the page. The sidebar controls
the summary type (from Lab 2), the output language, which LLM vendor to call,
and whether to use that vendor's advanced model.

API keys are read from .streamlit/secrets.toml:

    OPENAI_API_KEY    = "sk-..."
    ANTHROPIC_API_KEY = "sk-ant-..."
    GOOGLE_API_KEY    = "AIza..."
"""

import requests
import streamlit as st
from bs4 import BeautifulSoup

# --------------------------------------------------------------------------
# Configuration
# --------------------------------------------------------------------------

# Model IDs move fast. If a call 404s, check the vendor's model list and edit
# the two strings for that vendor here — nothing else in the file changes.
MODELS = {
    "OpenAI": {
        "basic": "gpt-4o-mini",
        "advanced": "gpt-4o",
        "secret": "OPENAI_API_KEY",
        "keys_url": "https://platform.openai.com/account/api-keys",
    },
    "Anthropic (Claude)": {
        "basic": "claude-haiku-4-5-20251001",
        "advanced": "claude-sonnet-5",
        "secret": "ANTHROPIC_API_KEY",
        "keys_url": "https://console.anthropic.com/settings/keys",
    },
    "Google (Gemini)": {
        "basic": "gemini-3.5-flash",
        "advanced": "gemini-3-pro",
        "secret": "GOOGLE_API_KEY",
        "keys_url": "https://aistudio.google.com/app/apikey",
    },
}

SUMMARY_TYPES = {
    "Summarize in 100 words": "Summarize the document in about 100 words.",
    "Summarize in 2 connecting paragraphs": (
        "Summarize the document in exactly 2 connecting paragraphs."
    ),
    "Summarize in 5 bullet points": (
        "Summarize the document in exactly 5 bullet points."
    ),
}

LANGUAGES = ["English", "French", "Spanish", "German", "Hindi", "Japanese"]

# Rough character cap so a huge page can't blow past the context window.
MAX_CHARS = 40_000


# --------------------------------------------------------------------------
# URL reading
# --------------------------------------------------------------------------


@st.cache_data(show_spinner=False)
def read_url_content(url):
    """Fetch a web page and return its visible text, or None on failure."""
    try:
        response = requests.get(
            url,
            timeout=15,
            headers={"User-Agent": "Mozilla/5.0 (compatible; HW2-Summarizer/1.0)"},
        )
        response.raise_for_status()  # Raise an exception for HTTP errors
        soup = BeautifulSoup(response.content, "html.parser")

        # Drop non-content nodes so the model isn't fed JS and CSS.
        for tag in soup(["script", "style", "noscript"]):
            tag.decompose()

        return soup.get_text(separator=" ", strip=True)
    except requests.RequestException as e:
        st.error(f"Error reading {url}: {e}")
        return None


# --------------------------------------------------------------------------
# One streaming generator per vendor
# --------------------------------------------------------------------------


def stream_openai(api_key, model, system_prompt, user_prompt):
    from openai import OpenAI

    client = OpenAI(api_key=api_key)
    stream = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        stream=True,
    )
    for chunk in stream:
        if chunk.choices and chunk.choices[0].delta.content:
            yield chunk.choices[0].delta.content


def stream_anthropic(api_key, model, system_prompt, user_prompt):
    import anthropic

    client = anthropic.Anthropic(api_key=api_key)
    with client.messages.stream(
        model=model,
        max_tokens=1024,
        system=system_prompt,  # Claude takes the system prompt as its own field
        messages=[{"role": "user", "content": user_prompt}],
    ) as stream:
        for text in stream.text_stream:
            yield text


def stream_gemini(api_key, model, system_prompt, user_prompt):
    from google import genai
    from google.genai import types

    client = genai.Client(api_key=api_key)
    stream = client.models.generate_content_stream(
        model=model,
        contents=user_prompt,
        config=types.GenerateContentConfig(system_instruction=system_prompt),
    )
    for chunk in stream:
        if chunk.text:
            yield chunk.text


STREAMERS = {
    "OpenAI": stream_openai,
    "Anthropic (Claude)": stream_anthropic,
    "Google (Gemini)": stream_gemini,
}


# --------------------------------------------------------------------------
# Sidebar
# --------------------------------------------------------------------------

st.sidebar.header("Options")

summary_label = st.sidebar.radio("Type of summary", list(SUMMARY_TYPES.keys()))

language = st.sidebar.selectbox("Output language", LANGUAGES, index=0)

vendor = st.sidebar.selectbox("LLM provider", list(MODELS.keys()), index=0)

use_advanced = st.sidebar.checkbox("Use advanced model")

config = MODELS[vendor]
model_name = config["advanced"] if use_advanced else config["basic"]
st.sidebar.caption(f"Model: `{model_name}`")


# --------------------------------------------------------------------------
# Main page
# --------------------------------------------------------------------------

st.title("🔗 URL Summarizer")
st.write("Enter a web page URL and pick your options in the sidebar.")

url = st.text_input("URL to summarize", placeholder="https://example.com/article")

api_key = st.secrets.get(config["secret"], "")
if not api_key:
    st.warning(
        f"No `{config['secret']}` found in secrets.toml. "
        f"Get a key [here]({config['keys_url']}) and add it to "
        "`.streamlit/secrets.toml`, or paste it below.",
        icon="🗝️",
    )
    api_key = st.text_input(f"{vendor} API key", type="password")

go = st.button("Summarize", disabled=not (url and api_key), type="primary")

if go:
    with st.spinner("Reading the page…"):
        document = read_url_content(url)

    if not document:
        st.stop()

    if len(document) > MAX_CHARS:
        st.info(f"Page is long — using the first {MAX_CHARS:,} characters.")
        document = document[:MAX_CHARS]

    system_prompt = (
        "You are a careful summarizer. Base your answer only on the document "
        "the user provides; do not invent facts. "
        f"Write your entire response in {language}, including any headings or "
        "bullet labels, regardless of the language the document is written in."
    )

    user_prompt = (
        f"Here is the text of a web page:\n\n{document}\n\n---\n\n"
        f"{SUMMARY_TYPES[summary_label]}\n"
        f"Write the summary in {language}."
    )

    st.subheader(f"{summary_label} — in {language}")

    try:
        st.write_stream(
            STREAMERS[vendor](api_key, model_name, system_prompt, user_prompt)
        )
    except Exception as e:
        st.error(f"{vendor} request failed: {e}")