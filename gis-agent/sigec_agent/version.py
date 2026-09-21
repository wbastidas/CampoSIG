# -*- coding: utf-8 -*-
"""Agent version and the contract version it speaks with the backend.

The contract is versioned separately because the agent and the backend are deployed
independently: the agent lives on the ArcMap machine, on Python 2.7 (ADR-008).
"""

from __future__ import unicode_literals

AGENT_VERSION = "0.1.0"

#: Bumped whenever the HTTP contract with the backend changes incompatibly. The
#: backend rejects an agent whose contract version it does not support.
CONTRACT_VERSION = 1
