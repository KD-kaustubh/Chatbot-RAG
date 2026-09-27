from chatbot import answer_question



#   ---- MAIN EXECUTION BLOCK WITH INTERACTIVE CHAT -----
if __name__ == "__main__":
    print("AI Assistant: I'm ready! Ask me anything about your query.")
    print("               (Type 'exit' to end the chat)")
    print("-" * 50)

    while True:
        user_question = input("You: ")

        if user_question.lower() == "exit":
            print("AI Assistant: GoodBye! ")
            break

        ai_response = answer_question(user_question)

        print(f"\nAI Assistant:\n{ai_response}\n")
        print("-" * 150 )
