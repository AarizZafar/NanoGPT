import torch
from app.core.model import BigramLanguageModel
from app.utils.tokenizer import Tokenizer

class Generator:
    def __init__(self, model: BigramLanguageModel, tokenizer: Tokenizer, device: str):
        self.model     = model
        self.tokenizer = tokenizer
        self.device    = device

    def generate(self, max_new_tokens: int = 500) -> str:
        self.model.eval()
        idx    = torch.zeros((1, 1), dtype=torch.long, device=self.device)
        output = self.model.generate(idx, max_new_tokens)
        return self.tokenizer.decode(output[0].tolist())