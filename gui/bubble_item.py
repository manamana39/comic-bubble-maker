"""
gui.bubble_item
~~~~~~~~~~~~~~~
Interactive QGraphicsObject for comic speech bubbles.
Supports:
1. Dragging position on canvas
2. Draggable tail handle (orange point) to direct speech tail to mouth/shoulder
3. Draggable corner resize handles to adjust bubble and font size directly on canvas
"""

import math
from typing import Optional, Tuple, Dict
from PySide6.QtCore import Qt, QRectF, QPointF, Signal
from PySide6.QtGui import QPainter, QPen, QBrush, QColor, QCursor
from PySide6.QtWidgets import QGraphicsObject, QGraphicsItem, QStyleOptionGraphicsItem, QWidget

from comic_bubble.models import BubbleConfig
from .bubble_renderer import render_single_bubble_local, pil_to_qpixmap


class TailHandleItem(QGraphicsObject):
    """Draggable handle for adjusting speech bubble tail direction and length."""

    def __init__(self, parent: "BubbleGraphicsItem"):
        super().__init__(parent)
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.setZValue(200)
        self.radius = 8.0
        self.is_hovered = False
        self.is_dragging = False
        self._drag_start = QPointF()
        self.setAcceptHoverEvents(True)

    def boundingRect(self) -> QRectF:
        r = self.radius + 6
        return QRectF(-r, -r, r * 2, r * 2)

    def paint(self, painter: QPainter, option: QStyleOptionGraphicsItem, widget: Optional[QWidget] = None):
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        # Guide dashed line from bubble center to handle
        pen = QPen(QColor(255, 140, 0, 200), 2.0, Qt.PenStyle.DashLine)
        painter.setPen(pen)
        painter.drawLine(QPointF(0, 0) - self.pos(), QPointF(0, 0))

        # Handle circle
        fill = QColor(255, 180, 0, 255) if (self.is_hovered or self.is_dragging) else QColor(255, 120, 0, 230)
        painter.setBrush(QBrush(fill))
        painter.setPen(QPen(QColor(255, 255, 255), 2.5))
        painter.drawEllipse(QPointF(0, 0), self.radius, self.radius)

    def hoverEnterEvent(self, event):
        self.is_hovered = True
        self.update()
        super().hoverEnterEvent(event)

    def hoverLeaveEvent(self, event):
        self.is_hovered = False
        self.update()
        super().hoverLeaveEvent(event)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.is_dragging = True
            self._drag_start = event.pos()
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self.is_dragging:
            delta = event.pos() - self._drag_start
            new_pos = self.pos() + delta
            self.setPos(new_pos)
            self.parentItem().on_tail_handle_moved(new_pos)
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and self.is_dragging:
            self.is_dragging = False
            self.parentItem().on_tail_handle_released(self.pos())
            event.accept()
            return
        super().mouseReleaseEvent(event)


class ResizeHandleItem(QGraphicsObject):
    """Draggable handle at corners of the bubble for resizing font size / bubble dimensions."""

    def __init__(self, parent: "BubbleGraphicsItem", corner: str):
        super().__init__(parent)
        self.corner = corner  # 'tl', 'tr', 'bl', 'br'
        self.size = 8.0
        self.is_hovered = False
        self.is_dragging = False
        self._initial_ratio = 0.024
        self._initial_dist = 100.0
        self.setZValue(150)
        self.setAcceptHoverEvents(True)

        if corner in ("br", "tl"):
            self.setCursor(QCursor(Qt.CursorShape.SizeFDiagCursor))
        else:
            self.setCursor(QCursor(Qt.CursorShape.SizeBDiagCursor))

    def boundingRect(self) -> QRectF:
        s = self.size + 4
        return QRectF(-s, -s, s * 2, s * 2)

    def paint(self, painter: QPainter, option: QStyleOptionGraphicsItem, widget: Optional[QWidget] = None):
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        fill = QColor(0, 160, 255, 255) if (self.is_hovered or self.is_dragging) else QColor(0, 120, 215, 230)
        painter.setBrush(QBrush(fill))
        painter.setPen(QPen(QColor(255, 255, 255), 1.5))
        painter.drawRect(QRectF(-self.size / 2, -self.size / 2, self.size, self.size))

    def hoverEnterEvent(self, event):
        self.is_hovered = True
        self.update()
        super().hoverEnterEvent(event)

    def hoverLeaveEvent(self, event):
        self.is_hovered = False
        self.update()
        super().hoverLeaveEvent(event)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.is_dragging = True
            parent = self.parentItem()
            self._initial_ratio = parent.config.font_size_ratio
            self._initial_dist = max(20.0, math.hypot(self.pos().x(), self.pos().y()))
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self.is_dragging:
            parent = self.parentItem()
            cur_local = self.mapToParent(event.pos())
            cur_dist = max(15.0, math.hypot(cur_local.x(), cur_local.y()))
            scale_factor = cur_dist / self._initial_dist
            new_ratio = max(0.010, min(0.090, self._initial_ratio * scale_factor))
            parent.on_resize_font_size(new_ratio, is_final=False)
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and self.is_dragging:
            self.is_dragging = False
            parent = self.parentItem()
            cur_local = self.mapToParent(event.pos())
            cur_dist = max(15.0, math.hypot(cur_local.x(), cur_local.y()))
            scale_factor = cur_dist / self._initial_dist
            new_ratio = max(0.010, min(0.090, self._initial_ratio * scale_factor))
            parent.on_resize_font_size(new_ratio, is_final=True)
            event.accept()
            return
        super().mouseReleaseEvent(event)


class BubbleGraphicsItem(QGraphicsObject):
    """
    Interactive QGraphicsObject representing a comic speech bubble on canvas.
    Supports click selection, smooth dragging, tail handle manipulation, and live resizing.
    """

    changed = Signal()
    selected_changed = Signal(bool)

    def __init__(self, config: BubbleConfig, canvas_w: int, canvas_h: int):
        super().__init__()
        self.config = config
        self.canvas_w = max(1, canvas_w)
        self.canvas_h = max(1, canvas_h)

        self.pixmap = None
        self.pixmap_offset = QPointF(0, 0)
        self.body_size = (100, 100)

        # Enable dragging and selection for the bubble body
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable, True)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, True)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges, True)
        self.setCursor(QCursor(Qt.CursorShape.SizeAllCursor))

        # Tail handle (orange circle)
        self.tail_handle = TailHandleItem(self)

        # 4 Corner Resize handles
        self.resize_handles: Dict[str, ResizeHandleItem] = {
            "tl": ResizeHandleItem(self, "tl"),
            "tr": ResizeHandleItem(self, "tr"),
            "bl": ResizeHandleItem(self, "bl"),
            "br": ResizeHandleItem(self, "br"),
        }

        # Initial placement
        if self.config.center:
            cx = self.config.center[0] * self.canvas_w if self.config.center[0] <= 1.0 else self.config.center[0]
            cy = self.config.center[1] * self.canvas_h if self.config.center[1] <= 1.0 else self.config.center[1]
            self.setPos(cx, cy)
        else:
            self.setPos(self.canvas_w * 0.5, self.canvas_h * 0.3)

        # Initial tail placement
        if self.config.tail and self.config.type not in ("floating", "none", "sfx"):
            tx = self.config.tail[0] * self.canvas_w if self.config.tail[0] <= 1.0 else self.config.tail[0]
            ty = self.config.tail[1] * self.canvas_h if self.config.tail[1] <= 1.0 else self.config.tail[1]
            local_tx = tx - self.x()
            local_ty = ty - self.y()
            self.tail_handle.setPos(local_tx, local_ty)
            self.tail_handle.setVisible(True)
        else:
            self.tail_handle.setPos(-40, 80)
            self.tail_handle.setVisible(False)

        self._update_resize_handles_visibility(False)
        self.update_rendering()

    def _update_resize_handles_visibility(self, visible: bool):
        for h in self.resize_handles.values():
            h.setVisible(visible)

    def _reposition_resize_handles(self):
        bw, bh = self.body_size
        hw = bw / 2.0 + 4
        hh = bh / 2.0 + 4
        self.resize_handles["tl"].setPos(-hw, -hh)
        self.resize_handles["tr"].setPos(hw, -hh)
        self.resize_handles["bl"].setPos(-hw, hh)
        self.resize_handles["br"].setPos(hw, hh)

    def update_rendering(self, scale: int = 2):
        """Re-render bubble pixmap based on current config and tail position."""
        self.prepareGeometryChange()

        has_tail = self.tail_handle.isVisible() and self.config.type not in ("floating", "none", "sfx")
        tail_local = (int(self.tail_handle.x()), int(self.tail_handle.y())) if has_tail else None

        img, offset, body_size = render_single_bubble_local(
            self.config,
            img_h=self.canvas_h,
            scale=scale,
            tail_local=tail_local
        )

        self.pixmap = pil_to_qpixmap(img)
        self.pixmap_offset = QPointF(offset[0], offset[1])
        self.body_size = body_size
        self._reposition_resize_handles()
        self.update()

    def on_tail_handle_moved(self, local_pos: QPointF):
        """Called live as user drags the tail handle."""
        abs_x = self.x() + local_pos.x()
        abs_y = self.y() + local_pos.y()
        self.config.tail = (abs_x / self.canvas_w, abs_y / self.canvas_h)
        # Fast update during drag
        self.update_rendering(scale=1)
        self.changed.emit()

    def on_tail_handle_released(self, local_pos: QPointF):
        """Called when user finishes dragging tail handle."""
        abs_x = self.x() + local_pos.x()
        abs_y = self.y() + local_pos.y()
        self.config.tail = (abs_x / self.canvas_w, abs_y / self.canvas_h)
        # High-res update on release
        self.update_rendering(scale=2)
        self.changed.emit()

    def on_resize_font_size(self, new_ratio: float, is_final: bool = False):
        """Called when user drags any corner resize handle."""
        self.config.font_size_ratio = new_ratio
        self.update_rendering(scale=2 if is_final else 1)
        self.changed.emit()

    def set_has_tail(self, enable: bool):
        """Enable or disable speech tail."""
        self.tail_handle.setVisible(enable)
        if enable:
            if not self.config.tail:
                self.tail_handle.setPos(-40, 80)
                abs_x = self.x() - 40
                abs_y = self.y() + 80
                self.config.tail = (abs_x / self.canvas_w, abs_y / self.canvas_h)
        else:
            self.config.tail = None
        self.update_rendering()
        self.changed.emit()

    def sync_config(self):
        """Sync canvas coordinates to config normalized coordinates."""
        self.config.center = (self.x() / self.canvas_w, self.y() / self.canvas_h)
        if self.tail_handle.isVisible():
            abs_tx = self.x() + self.tail_handle.x()
            abs_ty = self.y() + self.tail_handle.y()
            self.config.tail = (abs_tx / self.canvas_w, abs_ty / self.canvas_h)
        else:
            self.config.tail = None

    def boundingRect(self) -> QRectF:
        if not self.pixmap:
            return QRectF(-50, -50, 100, 100)
        rect = QRectF(self.pixmap_offset.x(), self.pixmap_offset.y(), self.pixmap.width(), self.pixmap.height())
        if self.tail_handle.isVisible():
            handle_rect = self.tail_handle.mapRectToParent(self.tail_handle.boundingRect())
            rect = rect.united(handle_rect)
        for h in self.resize_handles.values():
            if h.isVisible():
                rect = rect.united(h.mapRectToParent(h.boundingRect()))
        return rect.adjusted(-6, -6, 6, 6)

    def paint(self, painter: QPainter, option: QStyleOptionGraphicsItem, widget: Optional[QWidget] = None):
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)

        # 1. Draw rasterized bubble pixmap
        if self.pixmap:
            painter.drawPixmap(self.pixmap_offset, self.pixmap)

        # 2. Draw selection boundary if selected
        if self.isSelected():
            bw, bh = self.body_size
            body_rect = QRectF(-bw / 2, -bh / 2, bw, bh)
            sel_pen = QPen(QColor(0, 120, 215, 200), 1.5, Qt.PenStyle.DashLine)
            painter.setPen(sel_pen)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRoundedRect(body_rect.adjusted(-4, -4, 4, 4), 6, 6)

    def itemChange(self, change: QGraphicsItem.GraphicsItemChange, value):
        if change == QGraphicsItem.GraphicsItemChange.ItemPositionChange and self.scene():
            self.sync_config()
            self.changed.emit()
        elif change == QGraphicsItem.GraphicsItemChange.ItemSelectedChange:
            is_sel = bool(value)
            self._update_resize_handles_visibility(is_sel)
            self.selected_changed.emit(is_sel)
            self.update()
        return super().itemChange(change, value)
