import sys
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig

class Phi3Chat():

    def __init__(self, model_name='microsoft/Phi-3-mini-128k-instruct', **config) -> None:
        self.model_name = model_name
        self.model = AutoModelForCausalLM.from_pretrained( 
            'microsoft/Phi-3-mini-128k-instruct',  
            device_map="auto",  
            torch_dtype="auto",  
            quantization_config=BitsAndBytesConfig(load_in_4bit=True),
            trust_remote_code=True,
            # attn_implementation="flash_attention_2"
        )
        self.tokenizer = AutoTokenizer.from_pretrained(model_name)
        

    def __call__(self, prompt, max_tokens=512, temperature=0.0, **kwargs) -> str:
        do_sample = True if temperature - 0 > 0.001 else False
        self.generation_args = { 
            "max_new_tokens": max_tokens, 
            "temperature": temperature, 
            "do_sample": do_sample, 
        }

        self.messages = [
            {"role": "system", "content": "you are a helpful AI."},
        ]
        with torch.no_grad():
            token_sentence = self.tokenizer.apply_chat_template(self.messages+[{"role": "user", "content": prompt}], tokenize=False, add_generation_prompt=True)
            input_token = self.tokenizer(token_sentence, return_tensors='pt').to('cuda')
            output_token = self.model.generate(**input_token, **self.generation_args)
            decode_output = self.tokenizer.batch_decode(output_token)
            output_list = decode_output[-1].split('<|assistant|>')
        
        res_text = output_list[-1].replace('<|end|>', '')
        return res_text


if __name__ == "__main__":
    print("Loading model, please wait...")
    agent = Phi3Chat()
    print("Model loaded. Ready to process input.")

    # Keep the Python script running to listen for input continuously
    while True:
        try:
            input_string = input()  # Read input continuously from stdin
            if not input_string:
                continue
            output_string = agent(input_string)
            print(output_string, flush=True)  # Output response back to stdout
        except EOFError:
            break  # Exit on EOF (end of file), which could happen if input is piped or script is killed

    print('sample.py exit accidently...')