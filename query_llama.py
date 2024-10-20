import requests
import json

class QueryLlama:
    def __init__(self, url="http://localhost:11434/api/generate", model="llama3.2"):
        self.url = url
        self.model = model
    
    def query_llama(self, prompt: str):
        '''Function to query Llama's API with streaming response'''
        payload = {
            "model": self.model,
            "prompt": prompt
        }
        response = requests.post(self.url, json=payload, stream=True)
        
        for line in response.iter_lines():
            if line:
                data = json.loads(line.decode('utf-8'))
                yield data['response']
                if data.get('done'):
                    break

if __name__ == "__main__":
    llama_query = QueryLlama()
    for chunk in llama_query.query_llama("Why is the sky blue?"):
        print(chunk, end='')  # Print each chunk as it arrives