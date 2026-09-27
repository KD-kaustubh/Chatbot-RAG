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




# --- CREATE AND LAUNCH THE GRADIO INTERFACE ---
demo = gr.ChatInterface(
    fn=chat_with_agent,
    title="BS in Data Science - RAG Assistant",
    description="Ask me any question about the BS in Data Science degree program, its courses, or its rules.",
    examples=[
        "What will I learn in the Computational Thinking course?",
        "What are the rules for the final exam?",
        "Tell me about the foundational level subjects"
    ]
)


if __name__ == "__main__":
    demo.launch()
