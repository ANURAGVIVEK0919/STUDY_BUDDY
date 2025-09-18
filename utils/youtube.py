# utils/youtube.py

from youtubesearchpython import VideosSearch

def find_youtube_video(video_title):
    """
    Searches YouTube for a given title and returns the URL of the top result.
    """
    try:
        # We only need the top result, so we limit the search to 1
        search = VideosSearch(video_title, limit=1)
        results = search.result()

        # Check if any videos were found
        if results and 'result' in results and len(results['result']) > 0:
            # Return the link of the first video
            return results['result'][0]['link']
        else:
            return None # Return None if no video was found
    except Exception as e:
        # Print an error for debugging but don't crash the app
        print(f"An error occurred during YouTube search: {e}")
        return None