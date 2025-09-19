import validators
import streamlit as st
from langchain.prompts import PromptTemplate
from langchain_groq import ChatGroq
from langchain.chains.summarize import load_summarize_chain
from langchain_community.document_loaders import YoutubeLoader, UnstructuredURLLoader
import traceback
import pkg_resources

st.set_page_config(page_title="LangChain: Summarize Text From YT or Website", page_icon="🦜")
st.title("🦜 LangChain: Summarize Text From YT or Website")

# Check pytube version
try:
    pytube_version = pkg_resources.get_distribution("pytube").version
    st.info(f"pytube version: {pytube_version}")
    # Recommend upgrade if version is below 15.0.0 (latest as of 2024)
    from packaging import version
    if version.parse(pytube_version) < version.parse("15.0.0"):
        st.warning("Your pytube version is outdated. Please run 'pip install --upgrade pytube' to avoid YouTube errors.")
except Exception:
    st.warning("Could not determine pytube version. If you encounter YouTube errors, try upgrading pytube.")
st.subheader('Summarize URL')

# Load Groq API key
groq_api_key = st.secrets.get("GROQ_API_KEY", "").strip()
generic_url = st.text_input("URL", label_visibility="collapsed")

# Initialize LLM if API key exists
llm = None
if groq_api_key:
    llm = ChatGroq(model="llama-3.1-8b-instant", groq_api_key=groq_api_key)

# Prompt template
prompt_template = """
Provide a summary of the following content in 300 words:
Content:{text}
"""
prompt = PromptTemplate(template=prompt_template, input_variables=["text"])

if st.button("Summarize the Content from YT or Website"):
    # Basic checks
    if not groq_api_key:
        st.error("Groq API key is missing. Please add it to secrets.toml")
    elif not generic_url.strip():
        st.error("Please provide a URL to summarize")
    elif not validators.url(generic_url):
        st.error("Please enter a valid URL. It can be a YouTube video or website URL")
    else:
        docs = []
        try:
            with st.spinner("Loading content..."):
                if "youtube.com" in generic_url or "youtu.be" in generic_url:
                    try:
                        loader = YoutubeLoader.from_youtube_url(generic_url, add_video_info=True)
                        docs = loader.load()
                    except Exception as yt_err:
                        st.error(
                            "Failed to load YouTube video. It may be private, removed, age-restricted, or pytube needs updating."
                        )
                        st.text(traceback.format_exc())
                else:
                    try:
                        loader = UnstructuredURLLoader(
                            urls=[generic_url],
                            ssl_verify=False,
                            headers={"User-Agent": "Mozilla/5.0"}
                        )
                        docs = loader.load()
                    except Exception as web_err:
                        st.error("Failed to load website content.")
                        st.text(traceback.format_exc())

            if not docs or not any(getattr(doc, 'page_content', None) for doc in docs):
                st.error("No content could be loaded from the provided URL. Please check the link.")
            else:
                st.write(f"Loaded {len(docs)} document(s). Preview of first doc:")
                st.write(docs[0].page_content[:500])  # show first 500 chars

                try:
                    with st.spinner("Generating summary..."):
                        chain = load_summarize_chain(llm, chain_type="stuff", prompt=prompt)
                        output_summary = chain.run(docs)
                        st.success("Summary generated:")
                        st.write(output_summary)
                except Exception as llm_err:
                    st.error("Error during summarization (Groq LLM):")
                    st.text(traceback.format_exc())

        except Exception as e:
            st.error("Unexpected error while processing the URL:")
            st.text(traceback.format_exc())
