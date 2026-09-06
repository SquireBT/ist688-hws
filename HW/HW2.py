import streamlit as st
import requests
from bs4 import BeautifulSoup
from openai import OpenAI
import anthropic


def read_url_content(url):
    try:
        response = requests.get(url)
        response.raise_for_status()  # Raise an exception for HTTP errors
        soup = BeautifulSoup(response.content, 'html.parser')
        return soup.get_text()
    except requests.RequestException as e:
        print(f"Error reading {url}: {e}")
        return None


# Show title and description.
st.title("HW2 - URL Summarizer")
st.write(
    "Enter a URL below and the selected LLM will summarize the page. "
    "Choose the type of summary, the output language, and the model in the sidebar."
)

# Sidebar options.
summary_options = [
    "Summarize the document in 100 words",
    "Summarize the document in 2 connecting paragraphs",
    "Summarize the document in 5 bullet points",
]
summary_type = st.sidebar.selectbox("Type of summary", summary_options)

output_language = st.sidebar.selectbox(
    "Output language", ["English", "French", "Spanish", "German"]
)

llm_choice = st.sidebar.selectbox("Which LLM?", ["OpenAI", "Anthropic"])

use_advanced = st.sidebar.checkbox("Use advanced model")

# Get the key for whichever LLM was selected.
if llm_choice == "OpenAI":
    api_key = st.secrets.get("OPENAI_API_KEY", "")
    model = "gpt-5" if use_advanced else "gpt-5-nano"
else:
    api_key = st.secrets.get("ANTHROPIC_API_KEY", "")
    model = "claude-sonnet-5" if use_advanced else "claude-haiku-4-5-20251001"

if not api_key or api_key.startswith("sk-proj-REPLACE"):
    st.info(f"No {llm_choice} API key detected. Add your key to `.streamlit/secrets.toml`")
else:
    # Ask the user for a URL at the top of the page.
    url = st.text_input("Enter a URL to summarize", placeholder="https://example.com")

    if url:
        document = read_url_content(url)

        if document is None:
            st.error(f"Could not read {url}. Check the URL and try again.")
        else:
            # Build the prompt, including the language instruction.
            instruction = (
                f"{summary_type}. Write the summary in {output_language}."
            )
            prompt = f"Here's a document: {document} \n\n---\n\n {instruction}"

            st.subheader(f"Summary ({output_language})")

            if llm_choice == "OpenAI":
                client = OpenAI(api_key=api_key)
                stream = client.chat.completions.create(
                    model=model,
                    messages=[{"role": "user", "content": prompt}],
                    stream=True,
                )
                st.write_stream(stream)
            else:
                client = anthropic.Anthropic(api_key=api_key)
                with client.messages.stream(
                    model=model,
                    max_tokens=1024,
                    messages=[{"role": "user", "content": prompt}],
                ) as stream:
                    st.write_stream(stream.text_stream)