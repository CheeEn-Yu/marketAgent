import sys
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig
import logging
import time

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    stream=sys.stderr  # Send all logs to stderr to separate from actual output
)
logger = logging.getLogger(__name__)

class Phi3Chat():
    def __init__(self, model_name='microsoft/Phi-3-mini-128k-instruct', **config) -> None:
        try:
            logger.info("Initializing Phi3Chat...")
            self.model_name = model_name
            self.model = AutoModelForCausalLM.from_pretrained( 
                'microsoft/Phi-3-mini-128k-instruct',  
                device_map="auto",  
                torch_dtype="auto",  
                quantization_config=BitsAndBytesConfig(load_in_4bit=True),
                trust_remote_code=True,
            )
            self.tokenizer = AutoTokenizer.from_pretrained(model_name)
            logger.info("Model initialization complete")
        except Exception as e:
            logger.error(f"Error during initialization: {str(e)}")
            raise

    def __call__(self, prompt, max_tokens=512, temperature=0.0, **kwargs) -> str:
        try:
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
                token_sentence = self.tokenizer.apply_chat_template(
                    self.messages+[{"role": "user", "content": prompt}], 
                    tokenize=False, 
                    add_generation_prompt=True
                )
                input_token = self.tokenizer(token_sentence, return_tensors='pt').to('cuda')
                output_token = self.model.generate(**input_token, **self.generation_args)
                decode_output = self.tokenizer.batch_decode(output_token)
                output_list = decode_output[-1].split('<|assistant|>')
            
            res_text = output_list[-1].replace('<|end|>', '')
            return res_text
        except Exception as e:
            logger.error(f"Error during inference: {str(e)}")
            return f"Error: {str(e)}"


if __name__ == "__main__":
    try:
        logger.info("Starting Python script...")
        logger.info("Loading model, please wait...")
        agent = Phi3Chat()
        logger.info("Model loaded. Ready to process input.")
        
        # Print a specific ready message that Node.js can detect
        print("PYTHON_READY", flush=True)
        
        while True:
            try:
                logger.info("Waiting for input...")
                input_string = sys.stdin.readline()
                
                if not input_string:
                    logger.info("Received empty input")
                    continue
                
                input_string = input_string.strip()
                if not input_string:
                    logger.info("Received blank line")
                    continue
                
                logger.info(f"Received input: {input_string}")
                output_string = agent(input_string)
                logger.info("Generated response, sending output...")
                
                # Print response with clear markers
                print("RESPONSE_START", flush=True)
                print(output_string, flush=True)
                print("RESPONSE_END", flush=True)
                sys.stdout.flush()
                logger.info("Response sent")
                
            except Exception as e:
                logger.error(f"Error in processing: {str(e)}")
                print("RESPONSE_START", flush=True)
                print(f"Error: {str(e)}", flush=True)
                print("RESPONSE_END", flush=True)
                sys.stdout.flush()

    except Exception as e:
        logger.error(f"Critical error: {str(e)}")
        sys.exit(1)