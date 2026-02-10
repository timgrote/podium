"""Engineer data and standard rates for proposal generation."""

import json
import os

ENGINEERS = {
    "tim": {
        "name": "Tim Grote",
        "title": "P.E., Owner",
        "phone": "307.509.0238",
        "signature_file_id": "1XuFrwSBCubjvvxc4lqtYtSBSAr-0oNTr",
    },
    "ally": {
        "name": "Ally Liebow",
        "title": "Principal",
        "phone": "970.224.4797",
        "signature_file_id": "1BTI5wW56t2SZsxyZ3fob2fCqsqRi6cyA",
    },
    "matara": {
        "name": "Matara Liebow",
        "title": "Principal",
        "phone": "415.493.8567",
        "signature_file_id": "1zNBpQ9krthlpg-aUsmptwsmJhqLdWecq",
    },
}

RATES = {
    "pe": {"label": "Professional Engineer", "rate": 180},
    "technician": {"label": "Engineering Technician", "rate": 120},
    "designer": {"label": "Designer", "rate": 120},
}

_TASKS_PATH = os.path.join(os.path.dirname(__file__), "..", "templates", "default_tasks.json")


def load_default_tasks():
    with open(_TASKS_PATH) as f:
        tasks = json.load(f)
    # Ensure each task has an amount field
    for t in tasks:
        t.setdefault("amount", 0)
    return tasks


CHANGES_TASK = {
    "name": "Changes/On Call Coordination",
    "description": (
        "a. Changes and modifications to irrigation design beyond initial submittals.\n"
        "b. Answer irrigation-related RFIs during bidding.\n"
        "c. Additional site visits and coordination as requested."
    ),
    "amount": 0,
}
