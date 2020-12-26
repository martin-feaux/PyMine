from __future__ import annotations

__all__ = ('Packet',)


class Packet:
    """Base Packet class.

    :param int id: Packet identifaction number. Defaults to -0x1.
    :attr id:
    """

    id_ = None
    to = None

    def __init__(self) -> None:
        self.id_ = self.__class__.id_
        self.to = self.__class__.to
