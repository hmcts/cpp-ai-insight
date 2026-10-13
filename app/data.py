from datasets import Dataset


def prepare_dataset(data) -> Dataset:
    """Convert a dict or list into a HuggingFace Dataset."""
    rows = data if isinstance(data, list) else [data]
    return Dataset.from_list(rows)
