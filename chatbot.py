import ollama

def get_response(prompt):
    print(f"User input: {prompt}")  # Debugging output
    try:
        response = ollama.chat(model="mistral", messages=[{"role": "user", "content": prompt}])
        print(f"Chatbot response: {response}")  # Debugging output
        return response["message"]["content"]
    except Exception as e:
        print(f"Error in getting response: {e}")  # Debugging output
        return "I'm having trouble responding right now."
# Simple chatbot loop
print("Chatbot: Hello! How can I assist you today? (Type 'exit' to stop)")

while True:
    user_input = input("You: ")
    if user_input.lower() == "exit":
        break
    print("Chatbot:", get_response(user_input))
