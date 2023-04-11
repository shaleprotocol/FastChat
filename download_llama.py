from transformers import LlamaTokenizer, LlamaForCausalLM

model = LlamaForCausalLM.from_pretrained('decapoda-research/llama-13b-hf')
tokenizer = LlamaTokenizer.from_pretrained('decapoda-research/llama-13b-hf')

prompt = "Hey, are you consciours? Can you talk to me?"
inputs = tokenizer(prompt, return_tensors="pt")

# Generate
generate_ids = model.generate(inputs.input_ids, max_length=30)
results = tokenizer.batch_decode(generate_ids, skip_special_tokens=True, clean_up_tokenization_spaces=False)
print(results)