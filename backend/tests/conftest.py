"""Shared fixtures.

The whole suite runs twice in CI: once per data-model profile. Tests must therefore
never assume a particular profile's real names — if one does, it will fail under
alt-synthetic, which is exactly the early warning ADR-004 wants.
"""

from __future__ import annotations

import os

import pytest

from app.model_profile.amd import load_asset_model
from app.model_profile.profile import load_profile
from app.model_profile.resolver import ModelResolver

ALL_PROFILE_IDS = ["cnel-gye", "alt-synthetic"]


@pytest.fixture
def active_profile_id() -> str:
    """The profile under test, honouring SIGEC_PROFILE as CI sets it."""
    return os.environ.get("SIGEC_PROFILE", "cnel-gye")


@pytest.fixture
def resolver(active_profile_id: str) -> ModelResolver:
    return ModelResolver(load_profile(active_profile_id))


@pytest.fixture(params=ALL_PROFILE_IDS)
def any_resolver(request: pytest.FixtureRequest) -> ModelResolver:
    """Parametrised over every profile, for behaviour that must hold for all of them."""
    return ModelResolver(load_profile(request.param))


@pytest.fixture
def amd():
    return load_asset_model()
