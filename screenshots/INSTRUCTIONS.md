# Screenshots

I can't generate real screenshots of a live Streamlit session — this
folder is set up so the README displays your own screenshots once you add
them, using these **exact filenames**:

| Filename | What to capture |
|---|---|
| `app.png` | The main app screen, right after `streamlit run app.py`, before generating anything — shows the topic input, language dropdown, and "Generate Post" button. |
| `loading.png` | The screen mid-generation, showing the `st.spinner` loading indicator (click "Generate Post" and screenshot quickly before it finishes). |
| `output.png` | A fully generated post, showing the post text box, the 📋 Copy button, and the hashtag chips underneath it. |
| `error.png` | The error-handling UI — easiest way to trigger this on demand is to click "Generate Post" with an empty topic field, which shows the friendly validation message. |

## How to capture

1. Run the app: `streamlit run app.py` (or `make run`).
2. Take each screenshot at the browser window (not the terminal).
3. Save each one directly into this `screenshots/` folder using the exact
   filename from the table above (case-sensitive).
4. That's it — `README.md` already references these filenames with
   markdown image syntax, so they'll display automatically once added.

Delete this `INSTRUCTIONS.md` file once you've added your real screenshots
(it's just for you, not meant to ship in the final submission).
