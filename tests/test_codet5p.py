import torch
from transformers import AutoModelForSeq2SeqLM, AutoTokenizer

checkpoint = "/data/ml/llm/codet5p-2b"
device = "cuda" # for GPU usage or "cpu" for CPU usage

tokenizer = AutoTokenizer.from_pretrained(checkpoint)

model = AutoModelForSeq2SeqLM.from_pretrained(checkpoint,
                                              torch_dtype=torch.float16,
                                              low_cpu_mem_usage=True,
                                              trust_remote_code=True).to(device)

encoding = tokenizer("def quick_sort():", return_tensors="pt").to(device)
encoding['decoder_input_ids'] = encoding['input_ids'].clone()
outputs = model.generate(**encoding, max_length=256)
print(outputs)
print(tokenizer.decode(outputs[0], skip_special_tokens=True))


print(tokenizer.pad_token_id)
print(tokenizer.eos_token_id)