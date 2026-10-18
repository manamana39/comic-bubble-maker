"""
gui.bubble_item
~~~~~~~~~~~~~~~
Interactive QGraphicsObject for speech bubbles with draggable position,
selection bounding boxes, and an interactive draggable tail control handle.
"""

from typing import Optional, Tuple
from PySide6.QtCore import Qt, QRectF, QPointF, Signal
from PySide6.QtGui import QPainter, QPen, QBrush, QColor, QCursor
from PySide6.QtWidgets import QGraphicsObject, QGraphicsItem, QStyleOptionGraphicsItem, QWidget

from comic_bubble.models import BubbleConfig
from .bubble_renderer import render_single_bubble_local, pil_to_qpixmap


class TailHandleItem(QGraphicsObject):
    """Draggable handle for adjusting speech bubble tail direction and length."""
    
    tail_moved = Signal(QPointF)

    def __init__(self, parent: "BubbleGraphicsItem"):
        super().__init__(parent)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable, True)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges, True)
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.setZValue(100)
        self.radius = 7.0
        self.is_hovered = False
        self.setAcceptHoverEvents(True)

    def boundingRect(self) -> QRectF:
        r = self.radius + 3
        return QRectF(-r, -r, r * 2, r * 2)

    def paint(self, painter: QPainter, option: QStyleOptionGraphicsItem, widget: Optional[QWidget] = None):
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        # Guide dashed line from bubble center to handle
        pen = QPen(QColor(255, 140, 0, 180), 1.5, Qt.PenStyle.DashLine)
        painter.setPen(pen)
        painter.drawLine(QPointF(0, 0) - self.pos(), QPointF(0, 0))

        # Handle circle
        fill = QColor(255, 165, 0, 240) if self.is_hovered else QColor(255, 120, 0, 220)
        painter.setBrush(QBrush(fill))
        painter.setPen(QPen(QColor(255, 255, 255), 2.0))
        painter.drawEllipse(QPointF(0, 0), self.radius, self.radius)

    def hoverEnterEvent(self, event):
        self.is_hovered = True
        self.update()
        super().hoverEnterEvent(event)

    def hoverLeaveEvent(self, event):
        self.is_hovered = False
        self.update()
        super().hoverLeaveEvent(event)

    def itemChange(self, change: QGraphicsItem.GraphicsItemChange, value):
        if change == QGraphicsItem.GraphicsItemChange.ItemPositionChange and self.scene():
            new_pos = value
            self.tail_moved.emit(new_pos)
        return super().itemChange(change, value)


class BubbleGraphicsItem(QGraphicsObject):
    """
    Interactive QGraphicsObject representing a comic speech bubble on canvas.
    Supports click selection, smooth dragging, tail handle manipulation, and live updates.
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

        # Enable dragging and selection
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable, True)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, True)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges, True)
        self.setCursor(QCursor(Qt.CursorShape.SizeAllCursor))

        # Tail handle
        self.tail_handle = TailHandleItem(self)
        self.tail_handle.tail_moved.connect(self._on_tail_handle_moved)

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
            self.tail_handle.setPos(60, 60)
            self.tail_handle.setVisible(False)

        self.update_rendering()

    def update_rendering(self):
        """Re-render bubble pixmap based on current config and tail position."""
        self.prepareGeometryChange()

        has_tail = self.tail_handle.isVisible() and self.config.type not in ("floating", "none", "sfx")
        tail_local = (int(self.tail_handle.x()), int(self.tail_handle.y())) if has_tail else None

        img, offset, body_size = render_single_bubble_local(
            self.config,
            img_h=self.canvas_h,
            scale=2,
            tail_local=tail_local
        )

        self.pixmap = pil_to_qpixmap(img)
        self.pixmap_offset = QPointF(offset[0], offset[1])
        self.body_size = body_size
        self.update()

    def _on_tail_handle_moved(self, local_pos: QPointF):
        """Called when user drags the tail handle."""
        # Update config tail in normalized coordinates
        abs_x = self.x() + local_pos.x()
        abs_y = self.y() + local_pos.y()
        self.config.tail = (abs_x / self.canvas_w, abs_y / self.canvas_h)
        self.update_rendering()
        self.changed.emit()

    def set_has_tail(self, enable: bool):
        """Enable or disable speech tail."""
        self.tail_handle.setVisible(enable)
        if enable:
            if not self.config.tail:
                # Default tail down-left towards character
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
        # Bounding rect covering pixmap and handles
        rect = QRectF(self.pixmap_offset.x(), self.pixmap_offset.y(), self.pixmap.width(), self.pixmap.height())
        if self.tail_handle.isVisible():
            handle_rect = self.tail_handle.mapRectToParent(self.tail_handle.boundingRect())
            rect = rect.united(handle_rect)
        return rect.adjusted(-5, -5, 5, 5)

    def paint(self, painter: QPainter, option: QStyleOptionGraphicsItem, widget: Optional[QWidget] = None):
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)

        # 1. Draw rasterized bubble pixmap
        if self.pixmap:
            painter.drawPixmap(self.pixmap_offset, self.pixmap)

        # 2. Draw selection indicator if selected
        if self.isSelected():
            bw, bh = self.body_size
            body_rect = QRectF(-bw / 2, -bh / 2, bw, bh)
            # Dashed blue bounding box around bubble body
            sel_pen = QPen(QColor(0, 120, 215, 200), 1.5, Qt.PenStyle.DashLine)
            painter.setPen(sel_pen)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRoundedRect(body_rect.adjusted(-4, -4, 4, 4), 6, 6)

            # Small corner anchors
            anchor_brush = QBrush(QColor(0, 120, 215, 240))
            painter.setPen(QPen(QColor(255, 255, 255), 1.0))
            for pt in [
                body_rect.topLeft() + QPointF(-4, -4),
                body_rect.topRight() + QPointF(4, -4),
                body_rect.bottomLeft() + QPointF(-4, 4),
                body_rect.bottomRight() + QPointF(4, 4),
            ]:
                painter.drawRect(QRectF(pt.x() - 3, pt.y() - 3, 6, 6))

    def itemChange(self, change: QGraphicsItem.GraphicsItemChange, value):
        if change == QGraphicsItem.GraphicsItemChange.ItemPositionChange and self.scene():
            self.sync_config()
            self.changed.emit()
        elif change == QGraphicsItem.GraphicsItemChange.ItemSelectedChange:
            is_sel = bool(value)
            self.selected_changed.emit(is_sel)
            self.update()
        return super().itemChange(change, value)
