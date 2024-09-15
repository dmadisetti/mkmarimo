import re
import shutil
import subprocess
import warnings
from pathlib import Path
import os

import markdown

from mkdocs.structure.pages import Page

from mkdocs.config import config_options
from mkdocs.plugins import BasePlugin

from .logging import get_logger

from mkdocs.structure.files import File, Files

log = get_logger(__name__)


class MarimoFile(File):
    """
    Wraps a regular File object to make .ipynb files appear as
    valid documentation files.
    """

    def __init__(self, file, use_directory_urls, site_dir, **config):
        self.file = file
        self.dest_path = self._get_dest_path(use_directory_urls)
        self.abs_dest_path = os.path.normpath(
            os.path.join(site_dir, self.dest_path)
        )
        self.url = self._get_url(use_directory_urls)
        self.config = config

    def __getattr__(self, item):
        return self.file.__getattribute__(item)

    def is_documentation_page(self):
        return True

    @property
    def content_bytes(self):
        quarto = self.config["quarto_path"]
        return subprocess.check_output([quarto, "render", self.abs_src_path,
                                  "--to=hugo-md", "-o", "-"])

    @property
    def content_string(self):
        data = self.content_bytes.decode("utf-8")
        print(data)
        return data


class MkQuartoDocsPlugin(BasePlugin):
    config_scheme = (
        ("quarto_path", config_options.Type(Path)),
        ("ignore", config_options.Type(str)),
        ("keep_output", config_options.Type(bool, default=False)),
    )

    def should_include(self, file):
        ext = os.path.splitext(str(file.abs_src_path))[-1]
        return ext in [".qmd"]

    def on_config(self, config, **kwargs):
        passed_path = self.config["quarto_path"]
        quarto = shutil.which(passed_path if passed_path else "quarto")
        self.config["quarto_path"] = quarto
        # self.ignores = [re.compile(x) for x in self.config["ignore"]]

        if self.config["ignore"]:
            self.ignores = [re.compile(self.config["ignore"])]
        else:
            self.ignores = []

        return config

    def _filter_ignores(self, paths):
        out = []
        for x in paths:
            if not any(re.fullmatch(pattern, x) for pattern in self.ignores):
                out.append(x)

        return out

    def on_files(self, files, config):
        ret = Files(
            [
                MarimoFile(file, **{**self.config, **config})
                if self.should_include(file)
                else file
                for file in files
            ]
        )
        return ret
