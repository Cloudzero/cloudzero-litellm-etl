# SPDX-FileCopyrightText: Copyright (c), CloudZero, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

"""LiteLLM to CloudZero AnyCost ETL Tool."""

import importlib.metadata

try:
    __version__ = importlib.metadata.version("ll2cz")
except importlib.metadata.PackageNotFoundError:
    # Fallback for development environment
    __version__ = "0.4.0"

from .cli import app

__all__ = ["app", "__version__"]
