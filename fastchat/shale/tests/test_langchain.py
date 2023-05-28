import os
os.environ['OPENAI_API_BASE'] = "http://dev.shale.live:30085/v1"
os.environ['OPENAI_API_KEY'] = "shale-lHH0EZBAZGzMS1"

from langchain.llms import OpenAI

llm = OpenAI(temperature=0.9)
prompt = "Write a poem about python and ai"
for i in range(2):
    result = llm(prompt)
    print(result)