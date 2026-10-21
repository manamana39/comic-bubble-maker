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


class AnchorHandleItem(QGraphicsObject):
    """Draggable handle on the bubble outline that sets where the tail leaves the bubble."""

    def __init__(self, parent: "BubbleGraphicsItem"):
        super().__init__(parent)
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.setZValue(190)
        self.radius = 6.0
        self.is_hovered = False
        self.is_dragging = False
        self.setAcceptHoverEvents(True)

    def boundingRect(self) -> QRectF:
        r = self.radius + 5
        return QRectF(-r, -r, r * 2, r * 2)

    def paint(self, painter: QPainter, option: QStyleOptionGraphicsItem, widget: Optional[QWidget] = None):
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        fill = QColor(60, 220, 255, 255) if (self.is_hovered or self.is_dragging) else QColor(0, 180, 230, 230)
        painter.setBrush(QBrush(fill))
        painter.setPen(QPen(QColor(255, 255, 255), 2.0))
        painter.drawRect(QRectF(-self.radius, -self.radius, self.radius * 2, self.radius * 2))

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
            event.accept()
            return
        super().mousePressEvent(event)

    def _angle_from_event(self, event) -> float:
        cur = self.parentItem().mapFromItem(self, event.pos())
        return round(math.degrees(math.atan2(cur.x(), -cur.y())), 1)

    def mouseMoveEvent(self, event):
        if self.is_dragging:
            self.parentItem().on_tail_anchor_changed(self._angle_from_event(event), is_final=False)
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and self.is_dragging:
            self.is_dragging = False
            self.parentItem().on_tail_anchor_changed(self._angle_from_event(event), is_final=True)
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


class RotateHandleItem(QGraphicsObject):
    """Draggable handle connected to the top of the bubble for intuitive on-canvas rotation."""

    def __init__(self, parent: "BubbleGraphicsItem"):
        super().__init__(parent)
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.setZValue(180)
        self.radius = 7.0
        self.is_hovered = False
        self.is_dragging = False
        self.setAcceptHoverEvents(True)

    def boundingRect(self) -> QRectF:
        r = self.radius + 6
        return QRectF(-r, -r, r * 2, r * 2)

    def paint(self, painter: QPainter, option: QStyleOptionGraphicsItem, widget: Optional[QWidget] = None):
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        fill = QColor(0, 215, 110, 255) if (self.is_hovered or self.is_dragging) else QColor(0, 175, 80, 230)
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

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.is_dragging = True
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self.is_dragging:
            parent = self.parentItem()
            cur_local = parent.mapFromItem(self, event.pos())
            # Angle in degrees from center (0,0); 0 is straight up, positive clockwise
            angle_rad = math.atan2(cur_local.x(), -cur_local.y())
            angle_deg = math.degrees(angle_rad)
            if angle_deg > 180.0:
                angle_deg -= 360.0
            elif angle_deg < -180.0:
                angle_deg += 360.0
            parent.on_rotate_angle(round(angle_deg, 1), is_final=False)
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and self.is_dragging:
            self.is_dragging = False
            parent = self.parentItem()
            cur_local = parent.mapFromItem(self, event.pos())
            angle_rad = math.atan2(cur_local.x(), -cur_local.y())
            angle_deg = math.degrees(angle_rad)
            if angle_deg > 180.0:
                angle_deg -= 360.0
            elif angle_deg < -180.0:
                angle_deg += 360.0
            parent.on_rotate_angle(round(angle_deg, 1), is_final=True)
            event.accept()
            return
        super().mouseReleaseEvent(event)


class BubbleGraphicsItem(QGraphicsObject):
    """
    Interactive QGraphicsObject representing a comic speech bubble on canvas.
    Supports click selection, smooth dragging, tail handle manipulation, live resizing, and rotation.
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

        # Tail anchor handle (cyan square on the outline)
        self.anchor_handle = AnchorHandleItem(self)
        self.anchor_handle.setVisible(False)
        self._handles_visible = False

        # Rotation handle (green circle)
        self.rotate_handle = RotateHandleItem(self)

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
        if self.config.tail and self.config.type not in ("floating", "none", "patch", "sfx"):
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
        # Rotate handle is visible for SFX and floating text when selected
        is_rotatable = self.config.type in ("sfx", "floating")
        self.rotate_handle.setVisible(visible and is_rotatable)
        self._handles_visible = visible
        self._update_anchor_handle()

    def _supports_anchor(self) -> bool:
        return self.config.type not in ("floating", "none", "patch", "sfx", "cloud", "scream", "box")

    def _anchor_angle_deg(self) -> float:
        """Current anchor angle (0=top, clockwise). Auto = direction toward the tail tip."""
        if self.config.tail_anchor is not None:
            return self.config.tail_anchor
        tp = self.tail_handle.pos()
        return math.degrees(math.atan2(tp.x(), -tp.y()))

    def _update_anchor_handle(self):
        show = self._handles_visible and self.tail_handle.isVisible() and self._supports_anchor()
        self.anchor_handle.setVisible(show)
        if not show:
            return
        bw, bh = self.body_size
        a = math.radians(self._anchor_angle_deg())
        dx, dy = math.sin(a), -math.cos(a)
        hw, hh = bw / 2.0, bh / 2.0
        if self.config.type == "oval":
            t = 1.0 / math.sqrt((dx / hw) ** 2 + (dy / hh) ** 2)
        else:
            t = min(hw / abs(dx) if abs(dx) > 1e-9 else 1e9, hh / abs(dy) if abs(dy) > 1e-9 else 1e9)
            # Rounded corners sit slightly inside the bounding rectangle
            t *= 0.93 if abs(abs(dx) * hh - abs(dy) * hw) < 0.35 * hw * hh / max(hw, hh) else 1.0
        self.anchor_handle.setPos(dx * t, dy * t)

    def _reposition_resize_handles(self):
        bw, bh = self.body_size
        hw = bw / 2.0 + 4
        hh = bh / 2.0 + 4
        self.resize_handles["tl"].setPos(-hw, -hh)
        self.resize_handles["tr"].setPos(hw, -hh)
        self.resize_handles["bl"].setPos(-hw, hh)
        self.resize_handles["br"].setPos(hw, hh)

        # Position rotation handle along rotated top axis
        dist = max(bh / 2.0 + 26.0, 36.0)
        rad = math.radians(self.config.angle)
        rx = dist * math.sin(rad)
        ry = -dist * math.cos(rad)
        self.rotate_handle.setPos(rx, ry)
        self._update_anchor_handle()


    def update_rendering(self, scale: int = 2):
        """Re-render bubble pixmap based on current config and tail position."""
        self.prepareGeometryChange()

        has_tail = self.tail_handle.isVisible() and self.config.type not in ("floating", "none", "patch", "sfx")
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

    def on_tail_anchor_changed(self, angle_deg: float, is_final: bool = False):
        """Called when user drags the anchor handle (where the tail leaves the bubble)."""
        self.config.tail_anchor = angle_deg
        self.update_rendering(scale=2 if is_final else 1)
        self.changed.emit()

    def reset_tail_anchor(self):
        """Return to automatic tail origin (nearest the tail tip)."""
        self.config.tail_anchor = None
        self.update_rendering()
        self.changed.emit()

    def flip_tail_horizontal(self) -> bool:
        """
        Flip the speech tail direction horizontally (left <-> right) relative to the bubble center.
        Returns True if the bubble has an active tail that was flipped.
        """
        if self.config.type in ("floating", "none", "patch", "sfx") or not self.tail_handle.isVisible():
            return False
        pos = self.tail_handle.pos()
        new_x = -pos.x() if abs(pos.x()) > 1.0 else 40.0
        self.tail_handle.setPos(new_x, pos.y())
        if self.config.tail_anchor is not None:
            self.config.tail_anchor = -self.config.tail_anchor
        self.sync_config()
        self.update_rendering()
        self.changed.emit()
        return True

    def set_tail_horizontal_dir(self, point_right: bool) -> bool:
        """
        Set the horizontal direction of the speech tail explicitly (point_right=True -> +X, False -> -X).
        Useful for 2-page spread alignment (inward / outward).
        """
        if self.config.type in ("floating", "none", "patch", "sfx") or not self.tail_handle.isVisible():
            return False
        pos = self.tail_handle.pos()
        mag_x = abs(pos.x()) if abs(pos.x()) >= 15.0 else 45.0
        new_x = mag_x if point_right else -mag_x
        self.tail_handle.setPos(new_x, pos.y())
        if self.config.tail_anchor is not None:
            mag_a = abs(self.config.tail_anchor)
            self.config.tail_anchor = mag_a if point_right else -mag_a
        self.sync_config()
        self.update_rendering()
        self.changed.emit()
        return True

    def on_resize_font_size(self, new_ratio: float, is_final: bool = False):
        """Called when user drags any corner resize handle."""
        self.config.font_size_ratio = new_ratio
        self.update_rendering(scale=2 if is_final else 1)
        self.changed.emit()

    def on_rotate_angle(self, new_angle: float, is_final: bool = False):
        """Called when user drags the rotation handle."""
        self.config.angle = new_angle
        self.update_rendering(scale=2 if is_final else 1)
        self.changed.emit()

    def set_has_tail(self, enable: bool):
        """Enable or disable speech tail."""
        self.tail_handle.setVisible(enable)
        self._update_anchor_handle()
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
        if self.anchor_handle.isVisible():
            rect = rect.united(self.anchor_handle.mapRectToParent(self.anchor_handle.boundingRect()))
        if self.rotate_handle.isVisible():
            r_rect = self.rotate_handle.mapRectToParent(self.rotate_handle.boundingRect())
            rect = rect.united(r_rect)
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

            # 3. Draw connector line to rotate handle if visible
            if self.rotate_handle.isVisible():
                rad = math.radians(self.config.angle)
                edge_dist = min(bw, bh) / 2.0
                start_pt = QPointF(edge_dist * math.sin(rad), -edge_dist * math.cos(rad))
                pen = QPen(QColor(0, 200, 100, 180), 1.5, Qt.PenStyle.DashLine)
                painter.setPen(pen)
                painter.drawLine(start_pt, self.rotate_handle.pos())

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
