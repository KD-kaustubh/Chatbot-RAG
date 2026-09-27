import gradio as gr
from chatbot import answer_question
from ui_content import (
    EXAMPLES, HEADER_HTML, WELCOME_HTML, FOOTER_HTML, BRAND_CSS,
    program_card_html, tips_card_html,
)



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

CSS = BRAND_CSS + """
.gradio-container { max-width: 1200px !important; margin: 0 auto !important; }

#iitm-chat { border-top: 3px solid #8B1E1E; border-radius: 12px; }
#iitm-input { border: 1px solid var(--border-color-primary); border-radius: 12px; background: var(--block-background-fill); }
#iitm-input .submit-button {
  background: #8B1E1E !important; color: #FFFFFF !important;
  border-radius: 8px; padding: 0 18px; font-weight: 600;
}
#iitm-input .submit-button:hover { background: #6E1616 !important; }

.dark .iitm-levels .cr { background: #3A1A1A; color: #F3B4B4; }
.dark .iitm-welcome h2 { color: #F3B4B4; }

/* On phones show the chat first and the info cards below it */
@media (max-width: 768px) {
  #iitm-sidebar { order: 2; }
}
"""




# --- CREATE AND LAUNCH THE GRADIO INTERFACE ---
with gr.Blocks(title="IITM BS Degree Assistant") as demo:
    gr.HTML(HEADER_HTML)

    with gr.Row(equal_height=False):
        with gr.Column(scale=1, min_width=260, elem_id="iitm-sidebar"):
            gr.HTML(program_card_html())
            gr.HTML(tips_card_html())

        with gr.Column(scale=3, min_width=320):
            gr.ChatInterface(
                fn=chat_with_agent,
                chatbot=gr.Chatbot(
                    elem_id="iitm-chat",
                    height=560,
                    placeholder=WELCOME_HTML,
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
