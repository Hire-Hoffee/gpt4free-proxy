from fastapi import FastAPI, Request
from langdetect import detect
from datetime import datetime
import uvicorn
import g4f
import asyncio

app = FastAPI()

@app.post("/data")
async def get_data(request: Request):
    data = await request.json()

    for model in g4f.models._all_models:
        try:
            response = await asyncio.wait_for(
                g4f.ChatCompletion.create_async(
                    model=model,
                    messages=data.get("messages"),
                ),
                timeout=10,
            )

            if response and detect(response) != "zh-cn" and response != '**NETWORK ERROR DUE TO HIGH TRAFFIC. PLEASE REGENERATE OR REFRESH THIS PAGE.**':
                print(f"\nModel: {model}, Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
                return response

        except Exception as e:
            print(e)

    return "Some error occurred :("

uvicorn.run(app, host="0.0.0.0", port=8989)
