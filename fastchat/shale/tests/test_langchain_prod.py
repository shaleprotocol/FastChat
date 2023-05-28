import os

os.environ['OPENAI_API_BASE'] = "https://shale.live/v1"
os.environ['OPENAI_API_KEY'] = "shale-IcLnUMpmnIoVeJ"

from langchain.llms import OpenAI

llm = OpenAI(temperature=0.9)
prompt = "Write me a python that parse json and sort first entry."
for i in range(2):
    result = llm(prompt)
    print(result)