from enum import Enum

from shared.exceptions.cloudapi_value_error import CloudApiValueError


class PresentProofProtocolVersion(str, Enum):
    v1: str = "v1"
    v2: str = "v2"


class IssueCredentialProtocolVersion(str, Enum):
    v1: str = "v1"
    v2: str = "v2"


def pres_id_no_version(proof_id: str) -> str:
    if proof_id.startswith("v2-") or proof_id.startswith("v1-"):
        return proof_id[3:]
    else:
        raise CloudApiValueError("proof_id must start with prefix `v1-` or `v2-`.")
