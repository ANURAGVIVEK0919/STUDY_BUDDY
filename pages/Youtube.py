import streamlit as st
from youtube_transcript_api import YouTubeTranscriptApi
from rpunct import RestorePuncts
from groq import Groq
import traceback

st.set_page_config(page_title="Summarize YouTube Videos", page_icon="🎥")
st.title("🎥 Summarize YouTube Videos with Groq LLaMA")

# Load Groq API key
groq_api_key = st.secrets.get("GROQ_API_KEY", "").strip()
if not groq_api_key:
    st.error("Groq API key is missing. Please add it to secrets.toml")
    st.stop()

# Initialize Groq client
client = Groq(api_key=groq_api_key)

# Function to extract video_id
def get_video_id(url_link: str) -> str:
    if "watch?v=" in url_link:
        return url_link.split("watch?v=")[-1].split("&")[0]
    elif "youtu.be/" in url_link:
        return url_link.split("youtu.be/")[-1].split("?")[0]
    elif "embed/" in url_link:
        return url_link.split("embed/")[-1].split("?")[0]
    return url_link

# Function to check if transcript is available
def check_transcript_availability(video_id: str) -> bool:
    try:
        # List available transcripts
        transcripts = YouTubeTranscriptApi.list_transcripts(video_id)
        available_languages = [t.language_code for t in transcripts]
        print(f"Available transcripts for video ID {video_id}: {available_languages}")
        
        if not available_languages:
            st.error("No transcripts available for this video.")
            return False
        
        # Check if English transcript is available
        if 'en' in available_languages:
            return True
        else:
            st.error("No English transcript available. Available languages: " + ", ".join(available_languages))
            return False
    except Exception as e:
        st.error(f"Error checking transcript availability: {e}")
        st.text(traceback.format_exc())
        return False

# Function to load transcript and restore punctuation
def load_youtube_transcript(video_url: str):
    try:
        video_id = get_video_id(video_url)
        print(f"Fetching transcript for video ID: {video_id}")
        
        if not check_transcript_availability(video_id):
            return None

        # Fetch the transcript in English if available
        transcript = YouTubeTranscriptApi.get_transcript(video_id, languages=['en'])
        print(f"Transcript fetched successfully for video ID: {video_id}")
        transcript_text = " ".join([line["text"] for line in transcript])

        # Restore punctuation
        rpunct = RestorePuncts()
        results = rpunct.punctuate(transcript_text)
        return results
    except Exception as e:
        st.error(f"Failed to fetch transcript: {e}")
        st.text(traceback.format_exc())
        return None

# UI input
video_url = st.text_input("Enter YouTube Video URL")

if st.button("Summarize"):
    if not video_url.strip():
        st.error("Please provide a YouTube video URL")
    else:
        with st.spinner("Fetching transcript..."):
            transcript = load_youtube_transcript(video_url)

        if transcript:
            st.success("Transcript loaded successfully. Generating summary...")

            try:
                # Call Groq LLM directly (no LangChain)
                completion = client.chat.completions.create(
                    messages=[
                        {
                            "role": "user",
                            "content": f"Summarize the following text in 300 words:\n\n{transcript}"
                        }
                    ],
                    model="llama-3.1-8b-instant",
                    temperature=1,
                    max_tokens=512,
                    top_p=1,
                    frequency_penalty=0,
                    presence_penalty=0
                )

                summary = completion.choices[0].message.content
                st.subheader("Generated Summary")
                st.write(summary)

            except Exception as e:
                st.error("Error during summarization with Groq LLM")
                st.text(traceback.format_exc())