from schema import TriageResponse
from pydantic import ValidationError as PydanticValidationError


def validate_triage_response(data: dict) -> tuple[TriageResponse | None, str | None]:
    """
    Attempt to validate a dict against TriageResponse.
    Returns (response, None) on success or (None, error_detail) on failure.
    """
    try:
        response = TriageResponse(**data)
        return response, None
    except PydanticValidationError as e:
        return None, str(e)
