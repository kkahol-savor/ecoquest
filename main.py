import logging
import json
from fastapi import FastAPI, Query, Request
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from query_openai import QueryOpenAi
from query_llama import QueryLlama
import os
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

app = FastAPI()

templates = Jinja2Templates(directory="templates")

query_openai_instance = QueryOpenAi()
llama_query_instance = QueryLlama()

app.mount("/static", StaticFiles(directory="static"), name="static")

def update_usage(mode, query, response):
    usage_file = 'usage.json'
    date_str = datetime.now().strftime('%Y-%m-%d')
    time_str = datetime.now().strftime('%H:%M:%S')
    
    if os.path.exists(usage_file):
        with open(usage_file, 'r') as file:
            usage_data = json.load(file)
    else:
        usage_data = {}

    if date_str not in usage_data:
        usage_data[date_str] = {
            'date': date_str,
            'time': time_str,
            'power_mode': 0,
            'eco_mode': 0
        }

    token_count = len(query.split()) + len(response.split())
    
    if mode == 'power_use':
        usage_data[date_str]['power_mode'] += token_count
    elif mode == 'eco_mode':
        usage_data[date_str]['eco_mode'] += token_count

    with open(usage_file, 'w') as file:
        json.dump(usage_data, file, indent=4)

def initialize_query_response():
    """Ensure that query_response.json is initialized properly with empty lists."""
    file_path = 'query_response.json'
    if not os.path.exists(file_path):
        # Initialize the file with the correct structure if it doesn't exist
        with open(file_path, 'w') as f:
            json.dump({"query": [], "response": []}, f)
    else:
        try:
            with open(file_path, 'r') as f:
                data = json.load(f)
            # Check if data is a dictionary and has 'query' and 'response' as lists
            if not isinstance(data, dict):
                raise ValueError("Malformed query_response.json, reinitializing.")
            
            # If query or response are strings, wrap them in a list
            if isinstance(data.get('query'), str):
                data['query'] = [data['query']]
            if isinstance(data.get('response'), str):
                data['response'] = [data['response']]

            # Check that both are lists
            if not isinstance(data['query'], list) or not isinstance(data['response'], list):
                raise ValueError("query and response should be lists. Reinitializing.")
            
        except (ValueError, json.JSONDecodeError):
            # Reinitialize the file if it's corrupted
            with open(file_path, 'w') as f:
                json.dump({"query": [], "response": []}, f)

@app.get("/", response_class=HTMLResponse)
async def get(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/stream")
async def stream(query: str, mode: str = Query(...)):
    def event_generator():
        final_response = ""
        initialize_query_response()  # Ensure the file is correctly initialized
        if mode == "power_use":
            for content in query_openai_instance.query_openai(query):
                logging.info(f"content is {repr(content)} and content type is {type(content)}")
                final_response += content
                yield f"data: {content}\n\n"
            yield "data: [DONE]\n\n"
        elif mode == "eco_mode":
            # Read the query_response.json file and get up to the last 10 queries and responses
            with open('query_response.json', 'r') as f:
                data = json.load(f)
                history = []
                # Store complete queries and responses instead of tokens
                for i in range(1, min(10, len(data['query']))):
                    history.append({
                        "request": data['query'][-i], 
                        "response": data['response'][-i]
                    })
                    logging.info("history updated")
            logging.info(f"history is {history}")
            accumulated_response = ''
            for content in llama_query_instance.query_llama(query, history=history):
                if isinstance(content, str) and content.strip():
                    accumulated_response += content
                    yield f"data: {content}\n\n"
                elif isinstance(content, str) and not content.strip():
                    logging.info("Empty content, skipping...")
                    continue  # Skip empty responses
            yield "data: [DONE]\n\n"
            
            # Safely update the query and response in the JSON file
            data['query'].append(query)
            data['response'].append(accumulated_response)
            with open('query_response.json', 'w') as f:
                json.dump(data, f, indent=4)
        
        # Update usage.json
        update_usage(mode, query, final_response if mode == "power_use" else accumulated_response)

    return StreamingResponse(event_generator(), media_type="text/event-stream")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")
