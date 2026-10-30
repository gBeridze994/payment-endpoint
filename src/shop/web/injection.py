"""Dependency injection for Flask views."""

import functools
from collections.abc import Callable
from typing import Any


def inject[R](**providers: Callable[[], Any]) -> Callable[[Callable[..., R]], Callable[..., R]]:
    """Calls each provider when a request comes in and passes the result to the view.

    @blueprint.post("/carts/<uuid:cart_id>/payments")
    @inject(service=get_payment_service)
    def create_cart_payment(cart_id: uuid.UUID, service: PaymentService): ...
    """

    def decorator(view: Callable[..., R]) -> Callable[..., R]:
        @functools.wraps(view)
        def view_with_dependencies(*args: Any, **kwargs: Any) -> R:
            dependencies = {name: provide() for name, provide in providers.items()}
            return view(*args, **kwargs, **dependencies)

        return view_with_dependencies

    return decorator
