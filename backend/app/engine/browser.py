"""Browser configuration - use local Chrome installation."""
import os

# Local Chrome path (macOS)
CHROME_PATH = os.getenv(
    "CHROME_PATH",
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
)


def get_launch_args() -> dict:
    """Get Playwright launch args for local Chrome."""
    return {
        "executable_path": CHROME_PATH,
        "headless": False,
        "args": ["--disable-blink-features=AutomationControlled"],
    }


def get_launch_args_headless() -> dict:
    """Get Playwright launch args for headless mode (tests)."""
    return {
        "executable_path": CHROME_PATH,
        "headless": True,
        "args": ["--disable-blink-features=AutomationControlled"],
    }
