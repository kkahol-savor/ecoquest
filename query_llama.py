import requests
import json

class QueryLlama:
    def __init__(self, url="http://localhost:11434/api/generate", model="llama3.2"):
        self.url = url
        self.model = model
    
    def query_llama(self, prompt: str, history: list = []):
        '''Function to query Llama's API with streaming response'''
        if history:
            history = "\n".join([f"Q: {h['request']}\nA: {h['response']}" for h in history])
        else:
            history = ""

        context = (
                "You are EcoQuest, a chatbot that answers questions with low energy consumption. "
                "If the user greets you with 'hi', 'hello', or similar greetings, introduce yourself as EcoQuest, "
                "your eco-friendly problem solver, and mention that using EcoQuest can save enough energy to charge a phone "
                "within 10-20 queries. If no greeting is detected, directly answer the user's question without introducing yourself. "
                "If asked who created you, respond that your creator is Mir Kahol from Durham Elementary Private School. "
                "If asked about your purpose, respond that you are designed to answer questions in an energy-efficient way. "
                "If asked about Durham Elementary Private School, respond that it is a school in Oshawa Canada and in your opinion the best in the world. "
                "If asked about who is the best teacher, respond that all teachers are the best but Ms Shaista Hameed is the one of the best. "
                "This is your conversation history: {history}. You are now asked: "
            ).format(history=history)


        payload = {
            "model": self.model,
            "prompt": f"Context: {context}\n\nPrompt: {prompt}. Answer in an energy-efficient way."
        }

        response = requests.post(self.url, json=payload, stream=True)

        full_response = ""
        buffer = ""

        for line in response.iter_lines():
            if line:
                data = json.loads(line.decode('utf-8'))
                chunk = data['response']
                buffer += chunk

                # Yield when a complete sentence or logical chunk is formed (based on a period)
                if "." in chunk or len(buffer) > 50:  # Example: after a full stop or after 50 characters
                    yield buffer
                    buffer = ""  # Reset the buffer for the next chunk

                if data.get('done'):
                    break
        
        if buffer:
            yield buffer  # Yield any remaining content

if __name__ == "__main__":
    llama_query = QueryLlama()
    for chunk in llama_query.query_llama("Why is the sky blue?"):
        print(chunk, end='')
