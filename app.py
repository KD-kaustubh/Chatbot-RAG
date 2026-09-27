import gradio as gr
from chatbot import answer_question



# --- THE MAIN CHAT FUNCTION FOR GRADIO ---
def chat_with_agent(user_question, history):
    """
    This is the main function that Gradio's ChatInterface will call.
    It takes the user's question and the chat so far, and returns the AI's response.
    """
    print(f"User Query: {user_question}")
    return answer_question(user_question, history)




# --- PAGE CONTENT ---
BOT_AVATAR = "assets/bot.svg"

HEADER_HTML = """
<div class="iitm-header">
  <div class="iitm-badge">BS</div>
  <div class="iitm-heading">
    <div class="iitm-kicker">IIT Madras &middot; BS in Data Science and Applications</div>
    <h1>Degree Assistant</h1>
    <p>Ask about courses, levels, exams, eligibility and fees. Answers come from the student handbook and course documents.</p>
  </div>
  <span class="iitm-pill">Unofficial student project</span>
</div>
"""

PROGRAM_HTML = """
<div class="iitm-card">
  <h3>Program at a glance</h3>
  <ul class="iitm-levels">
    <li><span class="lvl">Foundation</span><span class="cr">32 credits</span><small>8 courses: English, Maths, Stats, CT, Python</small></li>
    <li><span class="lvl">Diploma</span><span class="cr">54 credits</span><small>Diploma in Programming + Diploma in Data Science</small></li>
    <li><span class="lvl">BSc degree</span><span class="cr">114 credits</span><small>Total credits to graduate with a BSc</small></li>
    <li><span class="lvl">BS degree</span><span class="cr">142 credits</span><small>Total credits to graduate with a BS</small></li>
  </ul>
</div>
"""

TIPS_HTML = """
<div class="iitm-card">
  <h3>Tips</h3>
  <ul class="iitm-tips">
    <li>Name the course for detailed answers, e.g. <em>"What is taught in PDSA?"</em></li>
    <li>Ask follow-ups naturally, e.g. <em>"How is it graded?"</em></li>
    <li>Compare up to 3 courses at once.</li>
  </ul>
</div>
"""

WELCOME_MD = """
<div class="iitm-welcome">
  <h2>Hi! How can I help you today?</h2>
  <p>I can answer questions about the IITM BS program using the official handbook and course documents.</p>
</div>
"""

FOOTER_HTML = """
<div class="iitm-footer">
  Answers are generated only from the student handbook and course documents and may be incomplete or out of date.
  Always check official IITM BS announcements before making decisions. Not affiliated with or endorsed by IIT Madras.
</div>
"""

EXAMPLES = [
    "What will I learn in the Computational Thinking course?",
    "Tell me about the foundational level subjects",
    "What are the eligibility rules to write the end term exam?",
    "What is the difference between MLF and MLT?",
]


# --- LOOK AND FEEL ---
THEME = gr.themes.Soft(
    primary_hue=gr.themes.colors.red,
    neutral_hue=gr.themes.colors.stone,
    font=[gr.themes.GoogleFont("Inter"), "system-ui", "sans-serif"],
).set(
    body_background_fill="#F6F1EA",  # warm off-white so the white cards stand out
    block_background_fill="#FFFFFF",
    button_primary_background_fill="#8B1E1E",
    button_primary_background_fill_hover="#6E1616",
    button_primary_background_fill_dark="#A83232",
    button_primary_background_fill_hover_dark="#8B1E1E",
    button_primary_text_color="#FFFFFF",
    button_primary_text_color_dark="#FFFFFF",
)

CSS = """
.gradio-container { max-width: 1200px !important; margin: 0 auto !important; }

/* Header banner */
.iitm-header {
  display: flex; align-items: center; gap: 18px; flex-wrap: wrap;
  padding: 22px 26px; border-radius: 14px; color: #FFFFFF;
  background: linear-gradient(120deg, #6E1616 0%, #8B1E1E 55%, #A83232 100%);
  border-bottom: 4px solid #E0B84C;
}
.iitm-badge {
  flex: none; width: 58px; height: 58px; border-radius: 50%;
  display: grid; place-items: center;
  background: #FFFFFF; color: #8B1E1E; border: 3px solid #E0B84C;
  font: 700 22px Georgia, "Times New Roman", serif;
}
.iitm-heading { flex: 1; min-width: 220px; }
.iitm-kicker { font-size: 13px; letter-spacing: .04em; text-transform: uppercase; color: #F3D98B; }
.iitm-header h1 { margin: 2px 0 4px; font-size: 28px; color: #FFFFFF; }
.iitm-header p { margin: 0; font-size: 14px; color: #F5E9E9; }
.iitm-pill {
  font-size: 12px; padding: 5px 12px; border-radius: 999px;
  border: 1px solid rgba(255,255,255,.55); color: #FFFFFF; white-space: nowrap;
}

/* Sidebar cards */
.iitm-card {
  padding: 16px 18px; margin-bottom: 14px; border-radius: 12px;
  background: var(--block-background-fill); border: 1px solid var(--border-color-primary);
  border-top: 3px solid #8B1E1E;
}
.iitm-card h3 { margin: 0 0 10px; font-size: 15px; color: var(--body-text-color); }
.iitm-levels, .iitm-tips { list-style: none; margin: 0; padding: 0; }
.iitm-levels li {
  display: grid; grid-template-columns: 1fr auto; gap: 2px 8px;
  padding: 8px 0; border-bottom: 1px dashed var(--border-color-primary);
}
.iitm-levels li:last-child { border-bottom: none; }
.iitm-levels .lvl { font-weight: 600; color: var(--body-text-color); }
.iitm-levels .cr { font-size: 12px; font-weight: 600; color: #8B1E1E; background: #F8ECEC; padding: 1px 8px; border-radius: 999px; }
.iitm-levels small { grid-column: 1 / -1; color: var(--body-text-color-subdued); }
.iitm-tips li { padding: 6px 0; font-size: 13px; color: var(--body-text-color-subdued); }

/* Chat */
.iitm-welcome { text-align: center; padding: 10px 20px; }
.iitm-welcome h2 { margin: 0 0 6px; color: #8B1E1E; }
.iitm-welcome p { margin: 0; color: var(--body-text-color-subdued); }
#iitm-chat { border-top: 3px solid #8B1E1E; border-radius: 12px; }
#iitm-input { border: 1px solid var(--border-color-primary); border-radius: 12px; background: var(--block-background-fill); }
#iitm-input .submit-button {
  background: #8B1E1E !important; color: #FFFFFF !important;
  border-radius: 8px; padding: 0 18px; font-weight: 600;
}
#iitm-input .submit-button:hover { background: #6E1616 !important; }

/* Footer */
.iitm-footer {
  margin-top: 8px; padding: 12px 16px; font-size: 12px; text-align: center;
  color: var(--body-text-color-subdued); border-top: 1px solid var(--border-color-primary);
}

.dark .iitm-levels .cr { background: #3A1A1A; color: #F3B4B4; }
.dark .iitm-welcome h2 { color: #F3B4B4; }

/* On phones show the chat first and the info cards below it */
@media (max-width: 768px) {
  #iitm-sidebar { order: 2; }
}

@media (max-width: 640px) {
  .iitm-header { padding: 16px; }
  .iitm-header h1 { font-size: 22px; }
}
"""




# --- CREATE AND LAUNCH THE GRADIO INTERFACE ---
with gr.Blocks(title="IITM BS Degree Assistant") as demo:
    gr.HTML(HEADER_HTML)

    with gr.Row(equal_height=False):
        with gr.Column(scale=1, min_width=260, elem_id="iitm-sidebar"):
            gr.HTML(PROGRAM_HTML)
            gr.HTML(TIPS_HTML)

        with gr.Column(scale=3, min_width=320):
            gr.ChatInterface(
                fn=chat_with_agent,
                chatbot=gr.Chatbot(
                    elem_id="iitm-chat",
                    height=560,
                    placeholder=WELCOME_MD,
                    avatar_images=(None, BOT_AVATAR),
                    show_label=False,
                ),
                textbox=gr.Textbox(
                    elem_id="iitm-input",
                    placeholder="Ask about courses, exams, fees, eligibility...",
                    show_label=False,
                    submit_btn="Ask",
                ),
                examples=EXAMPLES,
            )

    gr.HTML(FOOTER_HTML)


if __name__ == "__main__":
    demo.launch(theme=THEME, css=CSS)
