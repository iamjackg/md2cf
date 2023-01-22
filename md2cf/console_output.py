from rich.console import Console

console = Console(log_path=False, log_time=False, emoji_variant="emoji")
error_console = Console(stderr=True, log_time=False, log_path=False)
