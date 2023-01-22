from rich.console import Console

console = Console(log_path=False, log_time=False, emoji_variant="emoji")
error_console = Console(stderr=True, log_time=False, log_path=False)
minimal_output_console = Console(
    log_path=False,
    log_time=False,
    highlight=False,
    markup=False,
    emoji=False,
    quiet=True,
)
json_output_console = Console(
    log_path=False,
    log_time=False,
    highlight=False,
    markup=False,
    emoji=False,
    quiet=True,
)
