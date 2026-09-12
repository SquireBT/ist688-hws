import streamlit as st
from openai import OpenAI
from bs4 import BeautifulSoup
import requests

# Show title and description.
st.title("HW3 - URL Reader and Chatbot")

st.write("This is a chatbot that can read and answer questions about the content of one or two URLs. " \
"It was designed to have a limited memory buffer of 6 messages or 3 user-agent " \
"exchanges, so it won't remember anything after 3 questions. " \
"This chatbot will answer questions based on the content of the URLs provided, "\
"and will indicate which document it used to answer the question.")
# ------------------------------------------------------------ sidebar: model selector
 
llm_choice = st.sidebar.selectbox("Which LLM?", ["OpenAI", "Google Gemini"])
 
if llm_choice == "OpenAI":
    api_key = st.secrets.get("OPENAI_API_KEY", "")
    model = "gpt-5"
    base_url = None
elif llm_choice == "Google Gemini":
    api_key = st.secrets.get("GOOGLE_API_KEY", "")
    model = "gemini-3.7-flash"
    base_url = "https://generativelanguage.googleapis.com/v1beta/openai/"
 
if not api_key:
    st.error(f"Missing API key for {llm_choice}. Add it to your Streamlit secrets.")
    st.stop()
 
client = OpenAI(api_key=api_key, base_url=base_url)
st.sidebar.caption(f"Model: `{model}`")

# ------------------------------------------------------------ sidebar: url inputs

url_1 = st.sidebar.text_input("Enter the first URL to read", placeholder="https://example1.com")
url_2 = st.sidebar.text_input("Enter the second URL to read", placeholder="https://example2.com")
def read_url_content(url):
    try:
        response = requests.get(url)
        response.raise_for_status()  # Raise an exception for HTTP errors
        soup = BeautifulSoup(response.content, 'html.parser')
        return soup.get_text(separator=" ", strip=True)[:20000]
    except requests.RequestException as e:
        print(f"Error reading {url}: {e}")
        return None
    
def read_urls(urls):
    documents = []
    for i, url in enumerate(urls, start=1):
        if url:
            content = read_url_content(url)
            if content:
                documents.append((f"Document {i}", url, content))
            else:
                st.warning(f"Could not read content from {url}")
    return documents

docs = read_urls([url_1, url_2])
# ------------------------------------------------------------ prompt
BASE_PROMPT = (
    "You are a helpful assistant that answers questions using the reference documents "
    "below. Base your answers on those documents whenever they contain the answer, and "
    "say which document you used. If the documents do not cover the question, say so "
    "plainly before offering any general knowledge, and make clear that the extra "
    "information did not come from the documents. Keep answers clear and concise."
)

def build_system_prompt(docs):
    if not docs:
        return (
            BASE_PROMPT
            + "\n\nNo reference documents have been provided yet. Tell the user to add "
            "a URL in the sidebar before asking document questions."
        )
    parts = [BASE_PROMPT, "\n\nReference documents:"]
    for label, url, content in docs:
        parts.append(f"\n=== {label} (source: {url}) ===\n{content}")
    return "\n".join(parts)
 
 
system_prompt = build_system_prompt(docs)

# ------------------------------------------------------------ buffer
MAX_TURNS = 6
def message_buffer(messages, keep=MAX_TURNS):
    kept = messages[-keep:]
    while kept and kept[0]["role"] != "user":
        kept.pop(0)
    return kept

# ------------------------------------------------------------ chat loop
if "messages" not in st.session_state:
    st.session_state["messages"] = [{"role": "assistant", "content": "How can I help you?"}]

for msg in st.session_state.messages:
    chat_msg = st.chat_message(msg["role"])
    chat_msg.write(msg["content"])

if prompt := st.chat_input("What is up?"):
    st.session_state.messages.append({"role": "user", "content": prompt})

    with st.chat_message("user"):
        st.markdown(prompt)

    context = [{"role": "system", "content": system_prompt}] + message_buffer(st.session_state.messages)
    stream = client.chat.completions.create(
        model=model,
        messages=context,
        stream=True)

    with st.chat_message("assistant"):
        response = st.write_stream(stream)
    st.session_state.messages.append({"role": "assistant", "content": response})