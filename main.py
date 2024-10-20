import logging
import json
from fastapi import FastAPI, Query, Request
from fastapi.responses import HTMLResponse, StreamingResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import markdown
from query_openai import QueryOpenAi
from query_llama import QueryLlama
import os
from datetime import datetime, timedelta

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

def calculate_footprint_and_energy(data):
    carbon_footprint = {
        'eco_mode': data['eco_mode'] * 0.0198 * 0.1 / 100,
        'power_mode': data['power_mode'] * 0.0198 / 100
    }
    energy_burn = {
        'eco_mode': data['eco_mode'] * 0.0000417 * 0.1 / 100,
        'power_mode': data['power_mode'] * 0.0000417 / 100
    }
    return carbon_footprint, energy_burn

def get_usage_data():
    usage_file = 'usage.json'
    if os.path.exists(usage_file):
        with open(usage_file, 'r') as file:
            usage_data = json.load(file)
    else:
        usage_data = {}

    now = datetime.now()
    one_day_ago = now - timedelta(days=1)
    seven_days_ago = now - timedelta(days=7)
    one_month_ago = now - timedelta(days=30)

    data_1day = {'eco_mode': 0, 'power_mode': 0}
    data_7days = {'eco_mode': 0, 'power_mode': 0}
    data_1month = {'eco_mode': 0, 'power_mode': 0}
    cumulative_mobile_phones_charged = []

    for date_str, usage in usage_data.items():
        date = datetime.strptime(date_str, '%Y-%m-%d')
        if date >= one_day_ago:
            data_1day['eco_mode'] += usage['eco_mode']
            data_1day['power_mode'] += usage['power_mode']
        if date >= seven_days_ago:
            data_7days['eco_mode'] += usage['eco_mode']
            data_7days['power_mode'] += usage['power_mode']
        if date >= one_month_ago:
            data_1month['eco_mode'] += usage['eco_mode']
            data_1month['power_mode'] += usage['power_mode']

        total_tokens = usage['eco_mode'] + usage['power_mode']
        if total_tokens > 0:
            percentage_eco_mode = usage['eco_mode'] / total_tokens
            percentage_power_mode = usage['power_mode'] / total_tokens
        else:
            percentage_eco_mode = 0
            percentage_power_mode = 0

        energy_savings = 37.53 - (percentage_eco_mode * 0.32 + percentage_power_mode * 1.251) * 30
        mobile_phones_charged = energy_savings / (0.01*30)
        cumulative_mobile_phones_charged.append({
            'date': date_str,
            'mobile_phones_charged': mobile_phones_charged
        })

    cumulative_mobile_phones_charged.sort(key=lambda x: x['date'])

    # Filter for the last 7 days
    cumulative_mobile_phones_charged_last_7days = [entry for entry in cumulative_mobile_phones_charged if datetime.strptime(entry['date'], '%Y-%m-%d') >= seven_days_ago]

    carbon_footprint_1day, energy_burn_1day = calculate_footprint_and_energy(data_1day)
    carbon_footprint_7days, energy_burn_7days = calculate_footprint_and_energy(data_7days)
    carbon_footprint_1month, energy_burn_1month = calculate_footprint_and_energy(data_1month)

    total_tokens_1month = data_1month['eco_mode'] + data_1month['power_mode']
    if total_tokens_1month > 0:
        percentage_eco_mode = data_1month['eco_mode'] / total_tokens_1month
        percentage_power_mode = data_1month['power_mode'] / total_tokens_1month
    else:
        percentage_eco_mode = 0
        percentage_power_mode = 0

    energy_savings = 37.53 - (percentage_eco_mode * 0.32 + percentage_power_mode * 1.251) * 30
    mobile_phones_charged = energy_savings / (0.01*30)

    return {
        '1day': data_1day,
        '7days': data_7days,
        '1month': data_1month,
        'carbon_footprint': {
            '1day': carbon_footprint_1day,
            '7days': carbon_footprint_7days,
            '1month': carbon_footprint_1month
        },
        'energy_burn': {
            '1day': energy_burn_1day,
            '7days': energy_burn_7days,
            '1month': energy_burn_1month
        },
        'energy_savings': energy_savings,
        'mobile_phones_charged': mobile_phones_charged,
        'cumulative_mobile_phones_charged': cumulative_mobile_phones_charged_last_7days
    }

@app.get("/", response_class=HTMLResponse)
async def get(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/analysis", response_class=HTMLResponse)
async def analysis(request: Request):
    return templates.TemplateResponse("analysis.html", {"request": request})

@app.get("/analysis-data")
async def analysis_data():
    data = get_usage_data()
    return JSONResponse(content=data)

@app.get("/stream")
async def stream(query: str, mode: str = Query(...)):
    def event_generator():
        final_response = ""
        if mode == "power_use":
            for content in query_openai_instance.query_openai(query):
                logging.info(f"content is {repr(content)} and content type is {type(content)}")
                final_response += content
                yield f"data: {content}\n\n"
            yield "data: [DONE]\n\n"
        elif mode == "eco_mode":
            # Read the query_response.json file and get up to the last 10 queries and responses
            try:
                with open('query_response.json', 'r') as f:
                    data = json.load(f)
                    history = []
                    for i in range(1, min(10, len(data['query']))):
                        history.append({"request": data['query'][-i], "response": data['response'][-i]})
            except (FileNotFoundError, json.JSONDecodeError):
                data = {'query': [], 'response': []}
                history = []
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
            # Write the query and response to a json file
            data['query'].append(query)
            data['response'].append(accumulated_response)
            with open('query_response.json', 'w') as f:
                json.dump(data, f, indent=4)
        
        # Update usage.json
        update_usage(mode, query, final_response if mode == "power_use" else accumulated_response)

    return StreamingResponse(event_generator(), media_type="text/event-stream")

@app.on_event("shutdown")
async def shutdown_event():
    query_response_file = 'query_response.json'
    if os.path.exists(query_response_file):
        with open(query_response_file, 'w') as f:
            json.dump({'query': [], 'response': []}, f)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")