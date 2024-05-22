from flask import Flask, request
from langdetect import detect
import g4f
import asyncio

app = Flask(__name__)


@app.route("/data", methods=["POST"])
async def get_data():
    data = request.json

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


app.run(port=8989, host="0.0.0.0")
