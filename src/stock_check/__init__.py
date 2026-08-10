"""Branch-local stock check / SA adjustment app."""

__all__ = ["get_stock_check_settings"]


def get_stock_check_settings():
    from src.stock_check.config import get_stock_check_settings as _get

    return _get()
