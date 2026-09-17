"""
STEP 5: Streamlit UI.

REAL COPY BUTTON, NOT JUST A TEXT BOX
----------------------------------------
`st.text_area` lets a user manually select-and-copy, but that's not a real
one-click "Copy" button. Streamlit has no built-in clipboard-copy widget,
so we build a tiny, self-contained HTML/JS component with
`st.components.v1.html`: a styled button that calls the browser's
`navigator.clipboard.writeText()` API. This is a standard, well-supported
technique for adding small custom interactions Streamlit doesn't provide
natively, without needing a separate custom-component build pipeline.

WHY A SPINNER FOR THE LOADING INDICATOR
-------------------------------------------
`st.spinner(...)` blocks visually for exactly the duration of the LLM call
inside it — simple, built-in, and immediately understandable to a user,
which is all this needs.
"""

import html as html_module

import streamlit as st

from chain import generate_linkedin_post

LANGUAGE_OPTIONS = [
    "English",
    "Bengali",
    "Spanish",
    "French",
    "Arabic",
    "Hindi",
    "Other (type manually)",
]


def copy_button(text: str, key: str, label: str = "📋 Copy") -> None:
    """Renders a small button that copies `text` to the clipboard when
    clicked, using the browser's Clipboard API. `key` must be unique per
    button instance on the page (Streamlit doesn't auto-namespace raw HTML
    components the way it does native widgets)."""
    # Escape for safe embedding inside a JS template literal inside HTML.
    safe_text = html_module.escape(text).replace("`", "\\`").replace("</", "<\\/")
    component_html = f"""
    <div>
      <button id="copy-btn-{key}" style="
          background-color:#0A66C2; color:white; border:none;
          padding:8px 16px; border-radius:6px; cursor:pointer;
          font-size:14px; font-weight:600;">
        {label}
      </button>
      <span id="copy-status-{key}" style="margin-left:8px; font-size:13px; color:#22c55e;"></span>
    </div>
    <script>
      document.getElementById("copy-btn-{key}").addEventListener("click", function() {{
        const text = `{safe_text}`;
        navigator.clipboard.writeText(text).then(function() {{
          const status = document.getElementById("copy-status-{key}");
          status.innerText = "Copied!";
          setTimeout(() => {{ status.innerText = ""; }}, 2000);
        }});
      }});
    </script>
    """
    st.components.v1.html(component_html, height=45)


st.set_page_config(page_title="LinkedIn Post Generator", page_icon="📝", layout="centered")
st.title("📝 LinkedIn Post Generator")
st.caption(
    "Enter a topic and a language — powered by a LangChain LCEL chain "
    "(prompt → Groq LLM → parser). Free tier, no credit card needed."
)

topic = st.text_input("Topic", placeholder="e.g. AI in Healthcare, Remote Work Productivity")

language_choice = st.selectbox("Language", LANGUAGE_OPTIONS)
if language_choice == "Other (type manually)":
    language = st.text_input("Type the language name", placeholder="e.g. Portuguese")
else:
    language = language_choice

generate_clicked = st.button("Generate Post", type="primary")

if generate_clicked:
    with st.spinner("Generating your post..."):
        result = generate_linkedin_post(topic, language)

    if result["error"]:
        st.error(result["post"])
    else:
        st.subheader("Generated Post")
        st.text_area("Post content", value=result["post"], height=260, label_visibility="collapsed")
        copy_button(result["post"], key="post")

        if result["hashtags"]:
            st.subheader("Hashtags")
            # Render hashtags as small styled "chip" badges rather than
            # plain text, so they visually read as tags, not a sentence.
            chips_html = " ".join(
                f'<span style="background-color:#EEF3F8; color:#0A66C2; '
                f'padding:4px 10px; border-radius:14px; margin-right:6px; '
                f'font-size:13px; display:inline-block; margin-bottom:6px;">'
                f'{html_module.escape(tag)}</span>'
                for tag in result["hashtags"]
            )
            st.markdown(chips_html, unsafe_allow_html=True)
            copy_button(" ".join(result["hashtags"]), key="hashtags", label="📋 Copy hashtags")

        st.download_button(
            "⬇️ Download post + hashtags as .txt",
            data=result["post"] + "\n\n" + " ".join(result["hashtags"]),
            file_name="linkedin_post.txt",
            mime="text/plain",
        )
