from __future__ import annotations

import json
import time
from dataclasses import dataclass
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


USER_AGENT = "ScholarCheck/0.1 (mailto:foruniquelife@gmail.com)"


@dataclass(slots=True)
class JsonHttpClient:
    timeout_seconds: int = 20
    polite_delay_seconds: float = 0.2

    def get_json(self, url: str, params: dict[str, str | int] | None = None) -> dict:
        full_url = url
        if params:
            full_url = f"{url}?{urlencode(params)}"

        request = Request(
            full_url,
            headers={
                "Accept": "application/json",
                "User-Agent": USER_AGENT,
            },
        )

        try:
            with urlopen(request, timeout=self.timeout_seconds) as response:
                payload = response.read().decode("utf-8")
        except HTTPError as exc:
            raise RuntimeError(f"HTTP {exc.code} from {full_url}") from exc
        except URLError as exc:
            raise RuntimeError(f"Network error from {full_url}: {exc.reason}") from exc

        time.sleep(self.polite_delay_seconds)
        return json.loads(payload)
