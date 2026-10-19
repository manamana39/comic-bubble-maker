"""
gui.canvas
~~~~~~~~~~
Interactive canvas viewport for Manga Bubble Maker.
Supports smooth zooming, panning, drag-and-drop image loading,
and direct on-canvas bubble placement and selection.
"""

import os
from typing import Optional, List
from PIL import Image
from PySide6.QtCore import Qt, QPointF, Signal, QRectF
from PySide6.QtGui import (
    QPainter, QPixmap, QImage, QWheelEvent, QMouseEvent,
    QKeyEvent, QDragEnterEvent, QDropEvent, QContextMenuEvent
)
from PySide6.QtWidgets import QGraphicsView, QGraphicsScene, QGraphicsPixmapItem, QMenu

from comic_bubble.models import BubbleConfig
from .bubble_item import BubbleGraphicsItem
from .bubble_renderer import pil_to_qpixmap


class ComicCanvasView(QGraphicsView):
    """
    Main interactive editing canvas.
    Handles image display, zoom/pan navigation, and bubble item interactions.
    """

    bubble_selected = Signal(object)      # BubbleGraphicsItem or None
    scene_modified = Signal()
    image_loaded = Signal(str, int, int)  # path, width, height

    def __init__(self, parent=None):
        super().__init__(parent)
        self.scene = QGraphicsScene(self)
        self.setScene(self.scene)

        # Rendering hints for ultra-smooth display
        self.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        self.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.ViewportAnchor.AnchorViewCenter)
        self.setDragMode(QGraphicsView.DragMode.NoDrag)
        self.setBackgroundBrush(Qt.GlobalColor.darkGray)

        # State
        self.base_pil_image: Optional[Image.Image] = None
        self.base_image_path: Optional[str] = None
        self.bg_item: Optional[QGraphicsPixmapItem] = None
        self.bubble_items: List[BubbleGraphicsItem] = []
        self.current_selected_bubble: Optional[BubbleGraphicsItem] = None

        self._is_panning = False
        self._pan_start = QPointF()
        self._space_pressed = False

        self.setAcceptDrops(True)
        self.scene.selectionChanged.connect(self._on_scene_selection_changed)

    def load_image(self, image_path: str):
        """Load background image from file path."""
        if not os.path.isfile(image_path):
            return

        self.base_image_path = image_path
        self.base_pil_image = Image.open(image_path).convert("RGBA")
        w, h = self.base_pil_image.size

        # Clear existing items
        self.scene.clear()
        self.bubble_items.clear()
        self.current_selected_bubble = None

        # Add background image item
        qpix = pil_to_qpixmap(self.base_pil_image)
        self.bg_item = self.scene.addPixmap(qpix)
        self.bg_item.setZValue(0)
        self.scene.setSceneRect(0, 0, w, h)

        self.fit_in_view()
        self.image_loaded.emit(image_path, w, h)
        self.scene_modified.emit()

    def load_image_from_pil(self, pil_img: Image.Image, name_hint: str = "Pasted_Image"):
        """Load background image directly from PIL Image."""
        self.base_image_path = name_hint
        self.base_pil_image = pil_img.convert("RGBA")
        w, h = self.base_pil_image.size

        self.scene.clear()
        self.bubble_items.clear()
        self.current_selected_bubble = None

        qpix = pil_to_qpixmap(self.base_pil_image)
        self.bg_item = self.scene.addPixmap(qpix)
        self.bg_item.setZValue(0)
        self.scene.setSceneRect(0, 0, w, h)

        self.fit_in_view()
        self.image_loaded.emit(name_hint, w, h)
        self.scene_modified.emit()

    def fit_in_view(self):
        """Fit entire image neatly inside current viewport."""
        if self.bg_item:
            self.fitInView(self.scene.sceneRect(), Qt.AspectRatioMode.KeepAspectRatio)

    def reset_zoom(self):
        """Reset zoom to 100% 1:1 scale."""
        self.resetTransform()

    def add_bubble(self, config: Optional[BubbleConfig] = None, center_pos: Optional[QPointF] = None) -> BubbleGraphicsItem:
        """Add a new bubble onto canvas."""
        if not self.base_pil_image:
            return None

        w, h = self.base_pil_image.size
        if config is None:
            cx = (center_pos.x() / w) if center_pos else 0.5
            cy = (center_pos.y() / h) if center_pos else 0.3
            config = BubbleConfig(
                text="セリフを入力",
                type="capsule",
                font="kiwi",
                center=(cx, cy),
                tail=(cx - 0.1, cy + 0.15),
                font_size_ratio=0.024,
                border_color=(50, 45, 65, 220),
                text_color=(45, 35, 55, 255),
                bg_color=(255, 250, 245),
                visibility_mode="auto"
            )

        item = BubbleGraphicsItem(config, w, h)
        item.setZValue(len(self.bubble_items) + 10)
        self.scene.addItem(item)
        self.bubble_items.append(item)

        item.changed.connect(self._on_bubble_changed)

        # Select the newly created bubble
        self.scene.clearSelection()
        item.setSelected(True)
        self.scene_modified.emit()
        return item

    def remove_bubble(self, item: BubbleGraphicsItem):
        """Remove a bubble from canvas."""
        if item in self.bubble_items:
            self.bubble_items.remove(item)
            self.scene.removeItem(item)
            if self.current_selected_bubble == item:
                self.current_selected_bubble = None
                self.bubble_selected.emit(None)
            self.scene_modified.emit()

    def get_all_bubble_configs(self) -> List[BubbleConfig]:
        """Collect current configs for all bubbles in stacking order."""
        configs = []
        # Sort items by Z-value
        sorted_items = sorted(self.bubble_items, key=lambda it: it.zValue())
        for it in sorted_items:
            it.sync_config()
            configs.append(it.config)
        return configs

    def _on_scene_selection_changed(self):
        selected = self.scene.selectedItems()
        # Find if any BubbleGraphicsItem is selected
        target = None
        for item in selected:
            if isinstance(item, BubbleGraphicsItem):
                target = item
                break
            elif hasattr(item, "parentItem") and isinstance(item.parentItem(), BubbleGraphicsItem):
                target = item.parentItem()
                break

        self.current_selected_bubble = target
        self.bubble_selected.emit(target)

    def _on_bubble_changed(self):
        self.scene_modified.emit()

    # --- Mouse & Navigation Events ---

    def wheelEvent(self, event: QWheelEvent):
        """Zoom in/out with mouse wheel under cursor."""
        zoom_factor = 1.15
        if event.angleDelta().y() < 0:
            zoom_factor = 1.0 / zoom_factor
        self.scale(zoom_factor, zoom_factor)

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.MiddleButton or (event.button() == Qt.MouseButton.LeftButton and self._space_pressed):
            self._is_panning = True
            self._pan_start = event.position()
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent):
        if self._is_panning:
            delta = event.position() - self._pan_start
            self._pan_start = event.position()
            self.horizontalScrollBar().setValue(int(self.horizontalScrollBar().value() - delta.x()))
            self.verticalScrollBar().setValue(int(self.verticalScrollBar().value() - delta.y()))
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent):
        if self._is_panning:
            self._is_panning = False
            self.setCursor(Qt.CursorShape.ArrowCursor if not self._space_pressed else Qt.CursorShape.OpenHandCursor)
            event.accept()
            return
        super().mouseReleaseEvent(event)

    def mouseDoubleClickEvent(self, event: QMouseEvent):
        """Double click to add a new bubble at that location."""
        scene_pos = self.mapToScene(event.position().toPoint())
        if self.base_pil_image and self.scene.sceneRect().contains(scene_pos):
            # Check if clicked on empty background
            item = self.scene.itemAt(scene_pos, self.transform())
            if item == self.bg_item or item is None:
                self.add_bubble(center_pos=scene_pos)
                event.accept()
                return
        super().mouseDoubleClickEvent(event)

    def contextMenuEvent(self, event: QContextMenuEvent):
        """Right-click context menu for selected bubble or canvas background."""
        scene_pos = self.mapToScene(event.pos())
        clicked_item = self.scene.itemAt(scene_pos, self.transform())

        # Check if right-clicked on a bubble item or handle
        target_bubble = None
        if isinstance(clicked_item, BubbleGraphicsItem):
            target_bubble = clicked_item
        elif hasattr(clicked_item, "parentItem") and isinstance(clicked_item.parentItem(), BubbleGraphicsItem):
            target_bubble = clicked_item.parentItem()
        elif self.current_selected_bubble:
            if self.current_selected_bubble.sceneBoundingRect().contains(scene_pos):
                target_bubble = self.current_selected_bubble

        menu = QMenu(self)
        if target_bubble:
            if not target_bubble.isSelected():
                self.scene.clearSelection()
                target_bubble.setSelected(True)

            act_del = menu.addAction("🗑️ 削除 (Delete)")
            act_dup = menu.addAction("📋 複製 (Ctrl+D)")
            menu.addSeparator()
            act_front = menu.addAction("🔝 最前面へ移動")
            act_back = menu.addAction("🔙 最背面へ移動")

            act_reset_angle = None
            if target_bubble.config.type in ("sfx", "floating") or abs(target_bubble.config.angle) > 0.01:
                menu.addSeparator()
                act_reset_angle = menu.addAction("🔄 角度を0°にリセット")

            action = menu.exec(event.globalPos())
            if action == act_del:
                self.remove_bubble(target_bubble)
            elif action == act_dup:
                self._duplicate_bubble(target_bubble)
            elif action == act_front:
                self._bring_to_front(target_bubble)
            elif action == act_back:
                self._send_to_back(target_bubble)
            elif act_reset_angle and action == act_reset_angle:
                target_bubble.config.angle = 0.0
                target_bubble.update_rendering()
                target_bubble.changed.emit()
            event.accept()
            return
        else:
            # Right-clicked on empty canvas: quick-add options
            if self.base_pil_image:
                act_add_speech = menu.addAction("💬 ここに吹き出しを追加")
                act_add_mono = menu.addAction("💭 ここにモノローグを追加")
                act_add_sfx = menu.addAction("⚡ ここにオノマトペを追加")
                action = menu.exec(event.globalPos())
                if action == act_add_speech:
                    self.add_bubble(center_pos=scene_pos)
                elif action == act_add_mono:
                    w, h = self.base_pil_image.size
                    cfg = BubbleConfig(
                        text="心の声…",
                        type="floating",
                        font="mincho",
                        center=(scene_pos.x() / w, scene_pos.y() / h),
                        font_size_ratio=0.024
                    )
                    self.add_bubble(config=cfg)
                elif action == act_add_sfx:
                    w, h = self.base_pil_image.size
                    cfg = BubbleConfig(
                        text="ドキッ",
                        type="sfx",
                        font="bold",
                        center=(scene_pos.x() / w, scene_pos.y() / h),
                        font_size_ratio=0.035,
                        angle=-15.0
                    )
                    self.add_bubble(config=cfg)
                event.accept()
                return

        super().contextMenuEvent(event)

    def _duplicate_bubble(self, item: BubbleGraphicsItem):
        import copy
        new_cfg = copy.deepcopy(item.config)
        cx = new_cfg.center[0] + 0.04 if new_cfg.center else 0.5
        cy = new_cfg.center[1] + 0.04 if new_cfg.center else 0.5
        new_cfg.center = (cx, cy)
        if new_cfg.tail:
            new_cfg.tail = (new_cfg.tail[0] + 0.04, new_cfg.tail[1] + 0.04)
        return self.add_bubble(new_cfg)

    def _bring_to_front(self, item: BubbleGraphicsItem):
        max_z = max([it.zValue() for it in self.bubble_items], default=10)
        item.setZValue(max_z + 1)
        self.scene_modified.emit()

    def _send_to_back(self, item: BubbleGraphicsItem):
        min_z = min([it.zValue() for it in self.bubble_items], default=10)
        item.setZValue(max(1, min_z - 1))
        self.scene_modified.emit()


    def keyPressEvent(self, event: QKeyEvent):
        if event.key() == Qt.Key.Key_Space and not event.isAutoRepeat():
            self._space_pressed = True
            self.setCursor(Qt.CursorShape.OpenHandCursor)
        elif event.key() in (Qt.Key.Key_Delete, Qt.Key.Key_Backspace):
            if self.current_selected_bubble:
                self.remove_bubble(self.current_selected_bubble)
                event.accept()
                return
        super().keyPressEvent(event)

    def keyReleaseEvent(self, event: QKeyEvent):
        if event.key() == Qt.Key.Key_Space and not event.isAutoRepeat():
            self._space_pressed = False
            self.setCursor(Qt.CursorShape.ArrowCursor)
        super().keyReleaseEvent(event)

    # --- Drag & Drop Image Loading ---

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            urls = event.mimeData().urls()
            if any(u.toLocalFile().lower().endswith((".png", ".jpg", ".jpeg", ".webp", ".bmp")) for u in urls):
                event.acceptProposedAction()
                return
        super().dragEnterEvent(event)

    def dragMoveEvent(self, event):
        event.acceptProposedAction()

    def dropEvent(self, event: QDropEvent):
        if event.mimeData().hasUrls():
            for url in event.mimeData().urls():
                fpath = url.toLocalFile()
                if fpath.lower().endswith((".png", ".jpg", ".jpeg", ".webp", ".bmp")):
                    win = self.window()
                    if hasattr(win, "confirm_save_if_modified"):
                        if not win.confirm_save_if_modified():
                            event.ignore()
                            return
                    self.load_image(fpath)
                    event.acceptProposedAction()
                    return
        super().dropEvent(event)
