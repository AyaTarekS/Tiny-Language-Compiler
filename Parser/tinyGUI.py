import sys
import os
from pathlib import Path
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QTextEdit, QPushButton, QLabel, QFileDialog, QMessageBox, QSplitter
)
from PyQt5.QtGui import QPainter, QFont
from PyQt5.QtCore import Qt, QRectF, QPointF
from PyQt5.QtWidgets import QGraphicsScene, QGraphicsView, QGraphicsEllipseItem, QGraphicsRectItem, QGraphicsTextItem, QGraphicsLineItem

# Import your parser module (ensure parser.py is in the same folder)
import parser as parser_module

# Visual constants
NODE_WIDTH = 120
NODE_HEIGHT = 40
HORIZONTAL_PADDING = 30
VERTICAL_PADDING = 70
TEXT_MARGIN = 6
class ASTRenderer:
    """
    Calculates positions for AST nodes and draws them into a QGraphicsScene.
    Handles sibling chains by drawing each sibling tree next to each other.
    """

    def __init__(self, scene):
        self.scene = scene
        self.node_positions = {}  # maps node.id -> (x_center, y_top)

    def clear(self):
        self.scene.clear()
        self.node_positions.clear()

    def _measure_tree_width(self, node):
        """
        Returns the width needed to draw this tree (including subtree).
        """
        if not node:
            return 0
        if not node.children:
            return NODE_WIDTH
        
        widths = [self._measure_tree_width(c) for c in node.children if c]
        if not widths:
            return NODE_WIDTH
        
        total = sum(widths) + (len(widths) - 1) * HORIZONTAL_PADDING
        return max(total, NODE_WIDTH)

    def _place_tree(self, node, x_left, y_top):
        """
        Place the root node's center at (x_center, y_top)
        Returns the center x coordinate and the rightmost x used by this tree.
        """
        if not node:
            return x_left, x_left

        # If no children, center this node in the available width region
        if not node.children:
            center_x = x_left + NODE_WIDTH / 2
            self.node_positions[node.id] = (center_x, y_top)
            return center_x, x_left + NODE_WIDTH

        # Measure widths for children
        child_widths = [self._measure_tree_width(c) for c in node.children]
        total_width = sum(child_widths) + (len(child_widths) - 1) * HORIZONTAL_PADDING
        
        # start placing children at child_x
        child_x = x_left
        child_centers = []
        for idx, child in enumerate(node.children):
            w = child_widths[idx]
            center_x, child_right = self._place_tree(child, child_x, y_top + VERTICAL_PADDING)
            child_centers.append(center_x)
            child_x = child_right + HORIZONTAL_PADDING

        # Parent center is midpoint between first and last child centers
        center_x = (child_centers[0] + child_centers[-1]) / 2.0
        self.node_positions[node.id] = (center_x, y_top)
        return center_x, x_left + total_width

    def draw_node_graphics(self, node):
        """
        Draws nodes and edges recursively based on positions in node_positions.
        """
        if not node:
            return

        # Draw node itself
        if node.id not in self.node_positions:
            return
        cx, y_top = self.node_positions[node.id]
        x_left = cx - NODE_WIDTH / 2
        rect = QRectF(x_left, y_top, NODE_WIDTH, NODE_HEIGHT)

        # Draw shape
        if getattr(node, "shape", "oval") == "rect":
            shape_item = QGraphicsRectItem(rect)
        else:
            shape_item = QGraphicsEllipseItem(rect)
        
        shape_item.setPen(Qt.black)
        # Ensure shape is behind text but in front of lines if needed, 
        # but usually standard add order works.
        self.scene.addItem(shape_item)

        # Node text (type + value)
        label = node.node_type
        if getattr(node, "value", None):
            label += " " + str(node.value)
        text_item = QGraphicsTextItem(label)
        font = QFont("Arial", 9)
        text_item.setFont(font)
        
        # Center text
        text_rect = text_item.boundingRect()
        text_item.setPos(cx - text_rect.width()/2, y_top + (NODE_HEIGHT - text_rect.height())/2)
        self.scene.addItem(text_item)

        # Draw lines to children (Vertical/Diagonal)
        for child in node.children:
            if not child or child.id not in self.node_positions:
                continue
            cx_child, y_child = self.node_positions[child.id]
            
            # line from bottom center of parent to top center of child
            p1 = QPointF(cx, y_top + NODE_HEIGHT)
            p2 = QPointF(cx_child, y_child)
            self.scene.addItem(QGraphicsLineItem(p1.x(), p1.y(), p2.x(), p2.y()))
            
            # recursive draw
            self.draw_node_graphics(child)

    def render_root_sequence(self, root):
        """
        Top-level entry: root may be first statement in a sibling chain.
        Each sibling's subtree is measured and placed horizontally next to each other.
        """
        self.clear()
        if not root:
            return

        # 1. Collect all top-level siblings into a list
        siblings = []
        cur = root
        while cur:
            siblings.append(cur)
            cur = cur.sibling

        # 2. Calculate positions (Placement)
        x_cursor = 0
        max_right = 0
        for sib in siblings:
            w = self._measure_tree_width(sib)
            # Place this sibling tree starting at x_cursor
            center_x, right_x = self._place_tree(sib, x_cursor, 0)
            x_cursor = right_x + HORIZONTAL_PADDING
            max_right = max(max_right, right_x)

        # 3. Draw the nodes and children connections
        for sib in siblings:
            self.draw_node_graphics(sib)

        # 4. NEW: Draw Horizontal Lines between siblings
        # We loop through the list and connect Sibling[i] to Sibling[i+1]
        for i in range(len(siblings) - 1):
            curr_node = siblings[i]
            next_node = siblings[i+1]

            if curr_node.id in self.node_positions and next_node.id in self.node_positions:
                # Get coordinates
                curr_cx, curr_y = self.node_positions[curr_node.id]
                next_cx, next_y = self.node_positions[next_node.id]

                # Calculate start point (Right side of current node)
                # Node center is at curr_cx, width is NODE_WIDTH
                start_x = curr_cx + (NODE_WIDTH / 2)
                start_y = curr_y + (NODE_HEIGHT / 2) # Mid-height

                # Calculate end point (Left side of next node)
                end_x = next_cx - (NODE_WIDTH / 2)
                end_y = next_y + (NODE_HEIGHT / 2)   # Mid-height

                # Draw the horizontal line
                line_item = QGraphicsLineItem(start_x, start_y, end_x, end_y)
                self.scene.addItem(line_item)

        # 5. Resize scene rect to fit contents
        scene_width = max_right + NODE_WIDTH
        max_y = 0
        for pos in self.node_positions.values():
            _, y = pos
            max_y = max(max_y, y)
        scene_height = max_y + NODE_HEIGHT + VERTICAL_PADDING

        self.scene.setSceneRect(0, 0, max(scene_width, 800), max(scene_height, 400))
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("TINY Tokens → Parser → AST Viewer")
        self.resize(1100, 700)

        # Main layout
        root_widget = QWidget()
        self.setCentralWidget(root_widget)
        main_layout = QVBoxLayout()
        root_widget.setLayout(main_layout)

        # Top controls area
        controls = QHBoxLayout()
        main_layout.addLayout(controls)

        self.load_btn = QPushButton("Load Tokens File")
        self.load_btn.clicked.connect(self.load_tokens_file)
        controls.addWidget(self.load_btn)

        self.parse_btn = QPushButton("Parse Tokens")
        self.parse_btn.clicked.connect(self.parse_tokens)
        controls.addWidget(self.parse_btn)

        self.save_json_btn = QPushButton("Save Parse JSON")
        self.save_json_btn.clicked.connect(self.save_parse_json)
        self.save_json_btn.setEnabled(False)
        controls.addWidget(self.save_json_btn)

        self.status_label = QLabel("Status: Ready")
        controls.addWidget(self.status_label)

        # Splitter: left = token input + errors, right = graphics view
        splitter = QSplitter(Qt.Horizontal)
        main_layout.addWidget(splitter)

        left_widget = QWidget()
        left_layout = QVBoxLayout()
        left_widget.setLayout(left_layout)

        left_layout.addWidget(QLabel("Token input (one per line: value,TYPE)"))
        self.token_text = QTextEdit()
        left_layout.addWidget(self.token_text)

        left_layout.addWidget(QLabel("Parser errors / log"))
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        left_layout.addWidget(self.log_text)

        splitter.addWidget(left_widget)

        # Graphics view
        self.scene = QGraphicsScene()
        self.view = QGraphicsView(self.scene)
        self.view.setRenderHints(QPainter.Antialiasing | QPainter.TextAntialiasing)
        splitter.addWidget(self.view)
        splitter.setSizes([350, 750])

        self.renderer = ASTRenderer(self.scene)
        self.last_parse_result = None
        self.last_tokens = None

    # ---------------------------
    # File / token helpers
    # ---------------------------
    def load_tokens_file(self):
        path, _ = QFileDialog.getOpenFileName(self, "Open tokens file", ".", "Text Files (*.txt);;All Files (*)")
        if not path:
            return
        try:
            content = open(path, 'r', encoding='utf-8').read()
        except Exception as e:
            QMessageBox.critical(self, "File Error", f"Failed to open file: {e}")
            return
        # Put the file content into the token box
        self.token_text.setPlainText(content)
        self.log_text.append(f"Loaded tokens from: {path}")

    def _parse_token_textarea(self, text):
        """
        Parses the token textarea into a flat list of (value, TYPE)
        Similar behavior to parser.load_tokens_from_file (handles commas in value).
        """
        tokens = []
        lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
        for ln in lines:
            parts = ln.split(',')
            if len(parts) >= 2:
                token_type = parts[-1].strip()
                token_val = ",".join(parts[:-1]).strip()
                tokens.append((token_val, token_type))
            else:
                # malformed line
                self.log_text.append(f"Skipping malformed token line: {ln}")
        return tokens

    # ---------------------------
    # Parsing / drawing
    # ---------------------------
    def parse_tokens(self):
        txt = self.token_text.toPlainText().strip()
        if not txt:
            QMessageBox.warning(self, "No Tokens", "Please provide tokens in the textbox or load a token file.")
            return

        tokens = self._parse_token_textarea(txt)
        if not tokens:
            QMessageBox.warning(self, "No Valid Tokens", "No valid tokens parsed from the input.")
            return

        # Set last tokens for save/inspect
        self.last_tokens = tokens

        # Run the parser
        parser = parser_module.Parser(tokens)
        result = parser.parse()
        self.last_parse_result = result

        # Update UI
        self.status_label.setText(f"Status: {result['status']}")
        self.log_text.clear()
        if result['errors']:
            self.log_text.append("Errors:")
            for e in result['errors']:
                self.log_text.append("  - " + e)
        else:
            self.log_text.append("No syntax errors detected.")

        # Enable save JSON button only if we have parse_result
        self.save_json_btn.setEnabled(True)

        # Draw tree if any root
        root = result.get("root")
        if root:
            self.renderer.render_root_sequence(root)
            # fit view
            self.view.fitInView(self.scene.sceneRect(), Qt.KeepAspectRatio)
        else:
            self.renderer.clear()
            QMessageBox.information(self, "Parse Result", "No AST produced (possibly due to errors). See log for details.")

    def save_parse_json(self):
        if not self.last_parse_result:
            QMessageBox.warning(self, "Nothing to save", "No parse result to save yet.")
            return
        path, _ = QFileDialog.getSaveFileName(self, "Save parse JSON", "parse_result.json", "JSON files (*.json);;All Files (*)")
        if not path:
            return

        # Use parser_module.save_tree_to_json if available; otherwise, write directly
        try:
            if hasattr(parser_module, "save_tree_to_json"):
                parser_module.save_tree_to_json(self.last_parse_result, path)
            else:
                # fallback: manually dump
                import json
                out = {
                    "status": self.last_parse_result.get("status"),
                    "root": self.last_parse_result.get("root").to_dict() if self.last_parse_result.get("root") else None,
                    "errors": self.last_parse_result.get("errors")
                }
                with open(path, 'w', encoding='utf-8') as f:
                    json.dump(out, f, indent=4)
            QMessageBox.information(self, "Saved", f"Parse result saved to: {path}")
        except Exception as e:
            QMessageBox.critical(self, "Save Error", f"Failed to save parse JSON: {e}")


def main():
    app = QApplication(sys.argv)
    win = MainWindow()
    win.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
