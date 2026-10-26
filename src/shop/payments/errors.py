class PaymentError(Exception):
    """Base class for the reasons a cart payment cannot be started."""


class CartNotFound(PaymentError):
    pass


class CartNotPayable(PaymentError):
    pass


class EmptyCart(PaymentError):
    pass


class InvalidCartTotal(PaymentError):
    pass


class PaymentMethodNotFound(PaymentError):
    pass


class PaymentConflict(PaymentError):
    pass


class IdempotencyKeyReused(PaymentError):
    pass
