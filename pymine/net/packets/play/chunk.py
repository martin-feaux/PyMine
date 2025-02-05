# A flexible and fast Minecraft server software written completely in Python.
# Copyright (C) 2021 PyMine

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.
"""Contains packets relating to chunks."""

from __future__ import annotations

from pymine.types.packet import Packet
from pymine.types.buffer import Buffer
from pymine.types.chunk import Chunk
import pymine.types.nbt as nbt

__all__ = (
    "PlayUnloadChunk",
    "PlayChunkData",
    "PlayUpdateLight",
)


class PlayUnloadChunk(Packet):
    """Tells the client to unload a chunk column. Clientbound(Server => Client)"""

    id = 0x1C
    to = 1

    def __init__(self, chunk_x: int, chunk_z: int) -> None:
        super().__init__()

        self.chunk_x, self.chunk_z = chunk_x, chunk_z

    def encode(self) -> bytes:
        return Buffer.pack("i", self.chunk_x) + Buffer.pack("i", self.chunk_z)


class PlayChunkData(Packet):
    """Sends a chunk / its data to the client. (Server -> Client)

    :param Chunk chunk: The chunk to send the data for.
    :param bool full: Whether the chunk is "full" or not, see here: https://wiki.vg/Chunk_Format#Full_chunk
    :ivar int id: Unique packet ID.
    :ivar int to: Packet direction.
    :ivar chunk:
    :ivar full:
    """

    id = 0x20
    to = 1

    def __init__(self, chunk: Chunk, full: bool) -> None:
        super().__init__()

        self.chunk = chunk
        self.full = full

    def encode(self) -> bytes:
        out = Buffer.pack("i", self.chunk.x) + Buffer.pack("i", self.chunk.z) + Buffer.pack("?", self.full)

        mask = 0
        chunk_sections_buffer = Buffer()

        for y, section in self.chunk.sections.items():  # pack chunk columns into buffer and generate a bitmask
            if y >= 0:
                mask |= 1 << y
                chunk_sections_buffer.write(Buffer.pack_chunk_section_blocks(section))

        out += Buffer.pack_varint(mask) + Buffer.pack_nbt(
            nbt.TAG_Compound("", [self.chunk["Heightmaps"]["MOTION_BLOCKING"], self.chunk["Heightmaps"]["WORLD_SURFACE"]])
        )

        if self.full:
            out += Buffer.pack_varint(len(self.chunk["Biomes"])) + b"".join(
                [Buffer.pack_varint(n) for n in self.chunk["Biomes"]]
            )

        out += Buffer.pack_varint(len(chunk_sections_buffer)) + chunk_sections_buffer.read()

        # here we would pack the block entities, but we don't support them yet so we just send an array with length of 0
        out += Buffer.pack_varint(0)

        return out


class PlayUpdateLight(Packet):
    """Updates light levels for a chunk."""

    id = 0x23
    to = 1

    def __init__(self, chunk: Chunk) -> None:
        super().__init__()

        self.chunk = chunk

    def encode(self) -> bytes:
        return Buffer.pack_chunk_light(self.chunk)

    # def encode(self) -> bytes:
    #     out = Buffer.pack_varint(self.chunk.x) + Buffer.pack_varint(self.chunk.z) + Buffer.pack("?", True)
    #
    #     sky_light_mask = 0
    #     block_light_mask = 0
    #     empty_sky_light_mask = 0
    #     empty_block_light_mask = 0
    #
    #     sky_light_arrays = []
    #     block_light_arrays = []
    #
    #     for y, section in self.chunk.sections.items():
    #         if y >= 0:
    #             if section.sky_light is not None:
    #                 if len(section.sky_light.nonzero()) == 0:
    #                     empty_sky_light_mask |= 1 << y
    #                 else:
    #                     sky_light_mask |= 1 << y
    #
    #                     data = []
    #
    #                     for y in range(16):
    #                         for z in range(16):
    #                             for x in range(0, 16, 2):
    #                                 data.append(
    #                                     Buffer.pack("b", section.sky_light[x][y][z] | (section.sky_light[x + 1][y][z] << 4))
    #                                 )
    #
    #                     sky_light_arrays.append(b"".join(data))
    #
    #             if section.block_light is not None:
    #                 if len(section.block_light.nonzero()) == 0:
    #                     empty_block_light_mask |= 1 << y
    #                 else:
    #                     block_light_mask |= 1 << y
    #
    #                     data = []
    #
    #                     for y in range(16):
    #                         for z in range(16):
    #                             for x in range(0, 16, 2):
    #                                 data.append(
    #                                     Buffer.pack(
    #                                         "b", section.block_light[x][y][z] | (section.block_light[x + 1][y][z] << 4)
    #                                     )
    #                                 )
    #
    #                     block_light_arrays.append(b"".join(data))
    #
    #     return (
    #         out
    #         + Buffer.pack_varint(sky_light_mask)
    #         + Buffer.pack_varint(block_light_mask)
    #         + Buffer.pack_varint(empty_sky_light_mask)
    #         + Buffer.pack_varint(empty_block_light_mask)
    #         + Buffer.pack_varint(len(sky_light_arrays))
    #         + b"".join(sky_light_arrays)
    #         + Buffer.pack_varint(len(block_light_arrays))
    #         + b"".join(block_light_arrays)
    #     )
