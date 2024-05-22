from flask import Flask, request
import g4f
from langdetect import detect

app = Flask(__name__)


@app.route("/data", methods=["POST"])
async def get_data():
    data = request.json

    for model in g4f.models._all_models:
        try:
            response = await g4f.ChatCompletion.create_async(
                model=model,
                messages=data.get("messages"),
            )

            if response and detect(response) != "zh-cn":
                print("\nResponse model:", model)
                return response

        except Exception as e:
            print(e)

    return "Some error occurred :("


app.run(port=8989, host="0.0.0.0")
