"""Turns request data into pydantic models. Invalid data becomes a 400 response."""

from flask import request
from pydantic import BaseModel, ValidationError

from shop.web.errors import InvalidRequest


def validate[M: BaseModel](model: type[M], data: object) -> M:
    try:
        return model.model_validate(data)
    except ValidationError as error:
        raise InvalidRequest(_describe(error)) from None


def parse_json_body[M: BaseModel](model: type[M]) -> M:
    """The request's JSON body as `model`. An empty body counts as {}."""
    body = request.get_data()
    try:
        return model.model_validate_json(body) if body else model.model_validate({})
    except ValidationError as error:
        raise InvalidRequest(_describe(error)) from None


def _describe(error: ValidationError) -> str:
    """E.g. "payment_method_id: Input should be a valid UUID"."""
    return "; ".join(
        f"{'.'.join(map(str, detail['loc'])) or 'body'}: {detail['msg']}"
        for detail in error.errors()
    )
