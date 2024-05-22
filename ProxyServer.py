from fastapi import FastAPI, Request
import uvicorn
from langdetect import detect
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

            if response and detect(response) != "zh-cn":
                print("\nResponse model:", model)
                return response

        except Exception as e:
            print(e)

    return "Some error occurred :("


uvicorn.run(app, host="0.0.0.0", port=8989)
