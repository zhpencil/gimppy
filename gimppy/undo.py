"""
Undo system — extracted from app/core/:
  gimpundo.c, gimpundostack.c, gimpimage-undo.c,
  gimpimage-undo-push.c.
Provides undo/redo with grouped operations.
"""

import time
import numpy as np
from typing import Optional, List, Any, Callable
from enum import Enum

from .exceptions import UndoError


class UndoType(Enum):
    LAYER_PIXELS = "layer-pixels"
    LAYER_PROPERTY = "layer-property"
    CHANNEL_PIXELS = "channel-pixels"
    CHANNEL_PROPERTY = "channel-property"
    IMAGE_PROPERTY = "image-property"
    ITEM_ADD = "item-add"
    ITEM_REMOVE = "item-remove"
    ITEM_REORDER = "item-reorder"
    SELECTION = "selection"
    FILTER = "filter"
    GROUP = "group"


class UndoStep:
    """A single undo step — from gimpundo.c."""

    def __init__(self, undo_type: UndoType, name: str,
                 undo_fn: Callable, redo_fn: Callable):
        self.undo_type = undo_type
        self.name = name
        self.undo_fn = undo_fn
        self.redo_fn = redo_fn
        self.timestamp = time.time()
        self.preview: Optional[np.ndarray] = None

    def undo(self) -> None:
        self.undo_fn()

    def redo(self) -> None:
        self.redo_fn()


class UndoGroup:
    """A group of undo steps treated as a single operation."""

    def __init__(self, name: str):
        self.name = name
        self.steps: List[UndoStep] = []

    def add_step(self, step: UndoStep) -> None:
        self.steps.append(step)

    def undo(self) -> None:
        for step in reversed(self.steps):
            step.undo()

    def redo(self) -> None:
        for step in self.steps:
            step.redo()


class UndoStack:
    """
    Undo stack — from gimpundostack.c, gimpimage-undo.c.
    Manages undo/redo history with configurable depth.
    """

    def __init__(self, max_steps: int = 50):
        self.max_steps = max_steps
        self._undo_stack: List = []
        self._redo_stack: List = []
        self._enabled = True
        self._frozen = False
        self._group_stack: List[UndoGroup] = []

    @property
    def can_undo(self) -> bool:
        return len(self._undo_stack) > 0

    @property
    def can_redo(self) -> bool:
        return len(self._redo_stack) > 0

    @property
    def undo_count(self) -> int:
        return len(self._undo_stack)

    @property
    def redo_count(self) -> int:
        return len(self._redo_stack)

    def push(self, step: UndoStep) -> None:
        if not self._enabled or self._frozen:
            return
        if self._group_stack:
            self._group_stack[-1].add_step(step)
            return
        self._undo_stack.append(step)
        self._redo_stack.clear()
        if len(self._undo_stack) > self.max_steps:
            self._undo_stack.pop(0)

    def undo(self) -> Optional[str]:
        if not self.can_undo:
            raise UndoError("Nothing to undo")
        step = self._undo_stack.pop()
        step.undo()
        self._redo_stack.append(step)
        return step.name if hasattr(step, 'name') else "Undo"

    def redo(self) -> Optional[str]:
        if not self.can_redo:
            raise UndoError("Nothing to redo")
        step = self._redo_stack.pop()
        step.redo()
        self._undo_stack.append(step)
        return step.name if hasattr(step, 'name') else "Redo"

    def enable(self) -> None:
        self._enabled = True

    def disable(self) -> None:
        self._enabled = False

    @property
    def is_enabled(self) -> bool:
        return self._enabled

    def freeze(self) -> None:
        self._frozen = True

    def thaw(self) -> None:
        self._frozen = False

    def begin_group(self, name: str) -> None:
        group = UndoGroup(name)
        self._group_stack.append(group)

    def end_group(self) -> None:
        if not self._group_stack:
            raise UndoError("No undo group to end")
        group = self._group_stack.pop()
        if group.steps:
            if self._group_stack:
                self._group_stack[-1].add_step(group)
            else:
                self._undo_stack.append(group)
                self._redo_stack.clear()

    def get_undo_names(self) -> List[str]:
        names = []
        for step in self._undo_stack:
            names.append(step.name if hasattr(step, 'name') else "Unknown")
        return names

    def get_redo_names(self) -> List[str]:
        names = []
        for step in self._redo_stack:
            names.append(step.name if hasattr(step, 'name') else "Unknown")
        return names

    def clear(self) -> None:
        self._undo_stack.clear()
        self._redo_stack.clear()
