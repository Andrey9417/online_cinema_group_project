class PaymentGatewayError(Exception):
    pass


class OrderNotFound(Exception):
    pass


class OrderNotPayable(Exception):
    pass


class EmptyOrder(Exception):
    pass


class MoviesAlreadyPurchased(Exception):
    pass
