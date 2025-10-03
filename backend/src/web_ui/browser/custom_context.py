from browser_use.browser.browser import Browser
from browser_use.browser.context import (
    BrowserContext,
    BrowserContextConfig,
    BrowserContextState,
)

from web_ui.utils.logging_config import get_logger

logger = get_logger(__name__)


class CustomBrowserContext(BrowserContext):
    def __init__(
        self,
        browser: "Browser",
        config: BrowserContextConfig | None = None,
        state: BrowserContextState | None = None,
    ):
        super(CustomBrowserContext, self).__init__(
            browser=browser, config=config, state=state
        )
