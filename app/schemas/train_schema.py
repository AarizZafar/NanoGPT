from pydantic import BaseModel, Field, model_validator

class TrainRequest(BaseModel):
    block_size:    int   = Field(32,   ge=8,    le=512)
    batch_size:    int   = Field(32,   ge=4,    le=256)
    max_iters:     int   = Field(5000, ge=100,  le=100000)
    eval_interval: int   = Field(200,  ge=50,   le=1000)
    learning_rate: float = Field(3e-3, ge=1e-5, le=1e-1)
    n_embd:        int   = Field(64,   ge=16,   le=512)
    n_head:        int   = Field(4,    ge=1,    le=16)
    n_layer:       int   = Field(4,    ge=1,    le=12)
    dropout:       float = Field(0.2,  ge=0.0,  le=0.5)
    max_new_tokens: int  = Field(500,  ge=50,   le=2000)

    @model_validator(mode='after')
    def check_n_embd_divisible(self) -> 'TrainRequest':
        if self.n_embd % self.n_head != 0:
            raise ValueError('n_embd must be divisible by n_head')
        return self

class LossEvent(BaseModel):
    epoch:      int
    train_loss: float
    val_loss:   float