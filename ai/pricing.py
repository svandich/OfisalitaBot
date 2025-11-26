PRICING_PER_M_TOKENS = {
    # TODO: update this with newer OpenAI models
    # https://openai.com/api/pricing/
    "gpt-4o": {"input": 5, "output": 15},
    "gpt-4o-2024-05-13": {"input": 5, "output": 15},
    "gpt-3.5-turbo-0125": {"input": 0.5, "output": 1.5},
    "gpt-3.5-turbo-instruct": {"input": 1.5, "output": 2},
    # https://platform.claude.com/docs/en/about-claude/models/overview
    "claude-sonnet-4-5": {"input": 3, "output": 15},
    "claude-haiku-4-5": {"input": 1, "output": 5},
    "claude-opus-4-5": {"input": 5, "output": 25},
    "claude-opus-4-1": {"input": 15, "output": 75},
}


def get_model_pricing(model: str) -> dict:
    if model in PRICING_PER_M_TOKENS:
        return PRICING_PER_M_TOKENS[model]
    else:
        for key in PRICING_PER_M_TOKENS:
            if model.startswith(key):
                return PRICING_PER_M_TOKENS[key]
    raise ValueError(f"Pricing for model '{model}' not found")


def get_input_cost(model: str, input_tokens: int) -> float:
    return input_tokens * get_model_pricing(model)["input"] / 1000000


def get_output_cost(model: str, output_tokens: int) -> float:
    return output_tokens * get_model_pricing(model)["output"] / 1000000


def get_total_cost(model: str, input_tokens: int, output_tokens: int) -> float:
    return (
        get_input_cost(model, input_tokens)
        + get_output_cost(model, output_tokens) / 1000000
    )
