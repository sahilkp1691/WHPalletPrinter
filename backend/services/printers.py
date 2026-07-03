import sys

if sys.platform == "win32":
    import ctypes
    from ctypes import wintypes

    _winspool = ctypes.WinDLL("winspool.drv")

    PRINTER_ENUM_LOCAL = 0x00000002
    PRINTER_ENUM_CONNECTIONS = 0x00000004

    class PRINTER_INFO_4W(ctypes.Structure):
        _fields_ = [
            ("pPrinterName", wintypes.LPWSTR),
            ("pServerName", wintypes.LPWSTR),
            ("Attributes", wintypes.DWORD),
        ]

    def list_printers() -> list[str]:
        flags = PRINTER_ENUM_LOCAL | PRINTER_ENUM_CONNECTIONS
        level = 4
        cb_needed = wintypes.DWORD(0)
        c_returned = wintypes.DWORD(0)

        # First call to determine required buffer size.
        _winspool.EnumPrintersW(
            flags, None, level, None, 0,
            ctypes.byref(cb_needed), ctypes.byref(c_returned),
        )
        if cb_needed.value == 0:
            return []

        buffer = ctypes.create_string_buffer(cb_needed.value)
        ok = _winspool.EnumPrintersW(
            flags, None, level, buffer, cb_needed.value,
            ctypes.byref(cb_needed), ctypes.byref(c_returned),
        )
        if not ok:
            return []

        info_array = ctypes.cast(
            buffer, ctypes.POINTER(PRINTER_INFO_4W * c_returned.value)
        ).contents
        names = [p.pPrinterName for p in info_array if p.pPrinterName]
        # De-duplicate while preserving order.
        seen = set()
        result = []
        for name in names:
            if name not in seen:
                seen.add(name)
                result.append(name)
        return result

    def get_default_printer() -> str | None:
        length = wintypes.DWORD(0)
        _winspool.GetDefaultPrinterW(None, ctypes.byref(length))
        if length.value == 0:
            return None
        buffer = ctypes.create_unicode_buffer(length.value)
        if _winspool.GetDefaultPrinterW(buffer, ctypes.byref(length)):
            return buffer.value or None
        return None

else:

    def list_printers() -> list[str]:
        return []

    def get_default_printer() -> str | None:
        return None
