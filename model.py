from dataclasses import dataclass
from typing import Dict, Any


@dataclass
class DANEResponse:
    state: int
    message: str

    def to_json(self) -> Dict[str, Any]:
        return {"state": self.state, "message": self.message}


@dataclass
class DownloadResult:
    download_file_path: str
    dane_response: DANEResponse
    already_downloaded: bool
    file_info: Dict[str, Any]
