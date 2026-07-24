import torch
import torch.nn as nn

class Embeddings(nn.Module):
    def __init__(self, vocab_size: int, n_embd: int, block_size: int, device: str):
        super().__init__()
        self.device                     = device
        self.token_embedding_table      = nn.Embedding(vocab_size, n_embd)
        self.positional_embedding_table = nn.Embedding(block_size, n_embd)

    def forward(self, idx: torch.Tensor) -> torch.Tensor:
        B, T                            = idx.shape
        tok_emb                         = self.token_embedding_table(idx)
        pos_emb                         = self.positional_embedding_table(torch.arange(T, device=self.device))
        return tok_emb + pos_emb