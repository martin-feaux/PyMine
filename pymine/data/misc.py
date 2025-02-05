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
__all__ = (
    "POSES",
    "DIRECTIONS",
    "SMELT_TYPES",
)

POSES = (
    "standing",
    "fall_flying",
    "sleeping",
    "swimming",
    "spin_attack",
    "sneaking",
    "dying",
)

DIRECTIONS = (
    "down",
    "up",
    "north",
    "south",
    "west",
    "east",
)

SMELT_TYPES = (
    "minecraft:smelting",
    "minecraft:blasting",
    "minecraft:smoking",
    "minecraft:campfire_cooking",
)
