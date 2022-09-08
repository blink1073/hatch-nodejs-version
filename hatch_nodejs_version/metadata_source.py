# SPDX-FileCopyrightText: 2022-present Angus Hollands <goosey15@gmail.com>
#
# SPDX-License-Identifier: MIT
from __future__ import annotations

import json
import os.path
import re
import urllib.parse
from typing import Any

from hatchling.metadata.plugin.interface import MetadataHookInterface

AUTHOR_PATTERN = r"^([^<(]+?)?[ \t]*(?:<([^>(]+?)>)?[ \t]*(?:\(([^)]+?)\)|$)"
REPOSITORY_PATTERN = r"^(?:(gist|bitbucket|gitlab|github):)?(.*?)$"
REPOSITORY_TABLE = {
    "gitlab": "https://gitlab.com",
    "github": "https://github.com",
    "gist": "https://gist.github.com",
    "bitbucket": "https://bitbucket.org",
}


class NodeJSMetadataSource(MetadataHookInterface):
    PLUGIN_NAME = "nodejs"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.__path = None

    @property
    def path(self):
        if self.__path is None:
            version_file = self.config.get("path", "package.json")
            if not isinstance(version_file, str):
                raise TypeError(
                    "Option `path` for build hook `{}` must be a string".format(
                        self.PLUGIN_NAME
                    )
                )

            self.__path = version_file

        return self.__path

    def load_package_data(self):
        path = os.path.normpath(os.path.join(self.root, self.path))
        if not os.path.isfile(path):
            raise OSError(f"file does not exist: {self.path}")

        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)

    def _parse_bugs(self, bugs: str | dict[str, str]) -> str | None:
        if isinstance(bugs, str):
            return bugs

        if "url" not in bugs:
            return None

        return bugs["url"]

    def _parse_person(self, person: dict[str, str]) -> dict[str, str]:
        if {"url", "email"} & person.keys():
            result = {"name": person["name"]}
            if "email" in person:
                result["email"] = person["email"]
        else:
            match = re.match(AUTHOR_PATTERN, person["name"])
            if match is None:
                raise ValueError(f"Invalid author name: {person['name']}")
            name, email, _ = match.groups()
            result = {"name": name}
            if email is not None:
                result["email"] = email

        return result

    def _parse_repository(self, repository: str | dict[str, str]) -> str:
        if isinstance(repository, str):
            match = re.match(REPOSITORY_PATTERN, repository)
            if match is None:
                raise ValueError(f"Invalid repository string: {repository}")
            kind, identifier = match.groups()
            if kind is None:
                kind = "github"
            return urllib.parse.urljoin(REPOSITORY_TABLE[kind], identifier)

        return repository["url"]

    def update(self, metadata: dict[str, Any]):
        package = self.load_package_data()

        if "author" in package:
            metadata["author"] = self._parse_person(package["author"])

        if "contributors" in package:
            metadata["maintainers"] = [
                self._parse_person(p) for p in package["contributors"]
            ]

        if "keywords" in package:
            metadata["keywords"] = package["keywords"]

        if "description" in package:
            metadata["description"] = package["description"]

        if "license" in package:
            metadata["license"] = package["license"]

        # Construct URLs
        urls = {}
        if "homepage" in package:
            urls["homepage"] = package["homepage"]
        if "bugs" in package:
            bugs_url = self._parse_bugs(package["bugs"])
            if bugs_url is not None:
                urls["bug tracker"] = bugs_url
        if "repository" in package:
            urls["repository"] = self._parse_repository(package["repository"])

        # Write URLs
        if urls:
            metadata["urls"] = urls
