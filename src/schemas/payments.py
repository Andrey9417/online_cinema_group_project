from pydantic import BaseModel


class CheckoutResponseSchema(BaseModel):
    session_id: str
    payment_url: str
