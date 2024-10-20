import logging
import json
from fastapi import FastAPI, Query, Request
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import markdown
from query_openai import QueryOpenAi
from query_llama import QueryLlama

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

app = FastAPI()

templates = Jinja2Templates(directory="templates")

query_openai_instance = QueryOpenAi()
llama_query_instance = QueryLlama()

app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/", response_class=HTMLResponse)
async def get(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/stream")
async def stream(query: str, mode: str = Query(...)):
    def event_generator():
        if mode == "power_use":
            for content in query_openai_instance.query_openai(query):
                html_content = markdown.markdown(content)
                logging.info(html_content)
                yield f"data: {html_content}\n\n"
        elif mode == "eco_mode":
            for content in llama_query_instance.query_llama(query):
                logging.info(f"content is {repr(content)} and content type is {type(content)}")
                if isinstance(content, str) and content.strip():
                    html_content = markdown.markdown(content)  # Handle content as string
                    yield f"data: {content}\n\n"
                elif isinstance(content, str) and not content.strip():
                    logging.info("Empty content, skipping...")
                    continue  # Skip empty responses
            yield "data: [DONE]\n\n" 
            

    return StreamingResponse(event_generator(), media_type="text/event-stream")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")