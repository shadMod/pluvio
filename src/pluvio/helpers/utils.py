import xarray


def round_data_array(
    val_array: xarray.DataArray, n_digits: int, fail_silently: bool = True
) -> float | None:
    """Round a numpy array to n_digits.

    Args:
        val_array (xarray.DataArray): array to round.
        n_digits (int): Number of digits to round to.
        fail_silently (bool, optional): Raise exception if True. Defaults to True.

    Returns:
        float | None: Return round a numpy array. If rounding fails, return None if fail_silently is True,
                        otherwise raise.
    """
    try:
        return round(float(val_array), n_digits)
    except Exception:
        if fail_silently:
            return None
        raise
