import torch
import torch.nn as nn
from torch.nn import functional as F
from app.core.embeddings import Embeddings
from app.core.layers import Block

class BigramLanguageModel(nn.Module):
    def __init__(self, vocab_size: int, n_embd: int, n_head: int, n_layer: int, block_size: int, dropout: float, device: str):
        super().__init__()
        self.block_size = block_size
        self.device     = device
        self.embeddings = Embeddings(vocab_size, n_embd, block_size, device)
        self.blocks     = nn.Sequential(*[Block(n_embd, n_head, block_size, dropout) for _ in range(n_layer)])
        self.ln_f       = nn.LayerNorm(n_embd)
        self.lm_head    = nn.Linear(n_embd, vocab_size)

    def forward(self, idx: torch.Tensor, targets: torch.Tensor = None):
        x      = self.embeddings(idx)
        x      = self.blocks(x)
        x      = self.ln_f(x)
        logits = self.lm_head(x)

        loss = None
        if targets is not None:
            B, T, C = logits.shape
            loss    = F.cross_entropy(logits.view(B * T, C), targets.view(B * T))
        return logits, loss

    def generate(self, idx: torch.Tensor, max_new_tokens: int) -> torch.Tensor:
        for _ in range(max_new_tokens):
            idx_cond     = idx[:, -self.block_size:]
            logits, _    = self(idx_cond)
            logits       = logits[:, -1, :]
            probs        = F.softmax(logits, dim=-1)
            idx_next     = torch.multinomial(probs, num_samples=1)
            idx          = torch.cat((idx, idx_next), dim=1)
        return idx