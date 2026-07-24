import torch
from typing import Callable
from app.core.model import BigramLanguageModel

class Trainer:
    def __init__(self, model: BigramLanguageModel, train_data: torch.Tensor, val_data: torch.Tensor,
                 block_size: int, batch_size: int, learning_rate: float, eval_iters: int, device: str):
        self.model        = model
        self.train_data   = train_data
        self.val_data     = val_data
        self.block_size   = block_size
        self.batch_size   = batch_size
        self.eval_iters   = eval_iters
        self.device       = device
        self.optimizer    = torch.optim.AdamW(model.parameters(), lr=learning_rate)

    def get_batch(self, split: str):
        data = self.train_data if split == 'train' else self.val_data
        ix   = torch.randint(len(data) - self.block_size, (self.batch_size,))
        x    = torch.stack([data[i:i+self.block_size] for i in ix])
        y    = torch.stack([data[i+1:i+self.block_size+1] for i in ix])
        return x.to(self.device), y.to(self.device)

    @torch.no_grad()
    def estimate_loss(self):
        print('Estimating loss')
        out = {}
        self.model.eval()
        for split in ['train', 'val']:
            losses = torch.zeros(self.eval_iters)
            for k in range(self.eval_iters):
                X, Y         = self.get_batch(split)
                _, loss      = self.model(X, Y)
                losses[k]    = loss.item()
            out[split] = losses.mean().item()
        self.model.train()
        return out

    '''
        on_eval: Callable[[int, float, float], None] = None
        expect a function that takes int, float, float as arguments and returns None
    '''
    def train(self, max_iters: int, eval_interval: int, on_eval: Callable[[int, float, float], None] = None):
        print('Training (trainer)')
        for i in range(max_iters):
            if i % eval_interval == 0:
                losses = self.estimate_loss()
                if on_eval:
                    print(f"epoch {i:>6} | train loss: {losses['train']:.4f} | val loss: {losses['val']:.4f}")
                    on_eval(i, losses['train'], losses['val'])

            xb, yb = self.get_batch('train')
            _, loss = self.model(xb, yb)
            self.optimizer.zero_grad(set_to_none=True)
            loss.backward()
            self.optimizer.step()