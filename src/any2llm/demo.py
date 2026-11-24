"""Source documents and questions for the bundled midterm demo."""

from importlib.resources import files
from pathlib import Path

QUESTIONS = {
    "en": "Which research design fits the measurement plan? Cite the Excel sheet for what was measured in each class "
          "and the original PDF page for the design definition.",
    "tr": "Ölçüm planı hangi araştırma desenine uyuyor? Her sınıfta neyin ölçüldüğünü Excel sayfasına, "
          "desenin tanımını da orijinal PDF’in sayfasına atıf yaparak açıkla.",
}


def copy_sources(lang: str, destination: Path) -> None:
    source = files(__package__).joinpath("demo_assets", lang)
    for resource in source.iterdir():
        if resource.is_file():
            (destination / resource.name).write_bytes(resource.read_bytes())
