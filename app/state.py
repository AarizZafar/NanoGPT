from typing import Optional 
from app.core.model import BigramLanguageModel
from app.core.generator import Generator
from app.utils.tokenizer import Tokenizer

class AppState:
    tokenizer           : Optional[Tokenizer]            = None
    model               : Optional[BigramLanguageModel]  = None
    generator           : Optional[Generator]            = None
    training            : bool                           = False
    text                : Optional[str]                  = None

state = AppState()

'''
# Why `state.py` Exists

The purpose of `state.py` is to provide a single shared location for runtime
objects that need to be accessed across different parts of the FastAPI application.

FastAPI Process (single process, always running)

                +----------------------+
                |     FastAPI App      |
                +----------------------+
                 /        |         \\
                /         |          \\
         /train      /generate     /status
            |             |            |
            |             |            |
            +-------------+------------+
                          |
              Needs access to the same
              model, tokenizer, and
              application state

Without state.py:

    # /train
    model = BigramLanguageModel()    # Model A

    # /generate
    model = BigramLanguageModel()    # Model B

Each route creates its own model, so they do not share state.

With state.py:

    # state.py
    state = AppState()

    # /train
    from nanogpt.core.state import state
    state.model = BigramLanguageModel()

    # /generate
    from nanogpt.core.state import state
    state.model.generate(...)

Shared Runtime State

                     state.py
              +-------------------+
              |   state = AppState|
              +-------------------+
                      |
      +---------------+---------------+
      |               |               |
    model        tokenizer      is_training
      ^               ^               ^
      |               |               |
   /train        /generate        /status

Benefits:
- One shared model in memory.
- All routes operate on the same model.
- Shared tokenizer.
- Shared training status.
- Central location for runtime objects.
'''

