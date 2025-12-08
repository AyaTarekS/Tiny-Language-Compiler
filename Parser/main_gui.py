import sys
import os
from pathlib import Path
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QTextEdit, QPushButton, QLabel, QFileDialog, QMessageBox, QSplitter
)
from PyQt5.QtGui import QPainter, QFont, QPen, QColor, QMouseEvent, QBrush
from PyQt5.QtCore import Qt, QRectF, QPointF, QEvent
from PyQt5.QtWidgets import QGraphicsScene, QGraphicsView, QGraphicsEllipseItem, QGraphicsRectItem, QGraphicsTextItem, QGraphicsLineItem, QFrame

# Import your parser module (ensure parser.py is in the same folder)
import parser as parser_module

# Visual constants
NODE_WIDTH = 120
NODE_HEIGHT = 80
# Gap between sibling statement chains (top-level spacing)
# Increased to give more room between major statements like 'repeat' and 'write'.
SIBLING_HORIZONTAL_GAP = 250 
# Gap specifically between a node's children (used to separate entire subtrees under a parent)
# Increased to ensure subtrees like 'repeat' and the subsequent 'write' don't overlap.
CHILD_HORIZONTAL_GAP = 250
# Vertical distance parent -> child
VERTICAL_PADDING = 200
TEXT_MARGIN = 6
DEFAULT_NODE_COLOR = QColor("#616161")  # grey
DEFAULT_LINE_COLOR = QColor("#4c4c4c")   # darker grey for bold lines


class SyntaxTreeView(QGraphicsView):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.zoom_factor = 1.15
        self.setRenderHints(
            QPainter.Antialiasing |
            QPainter.SmoothPixmapTransform |
            QPainter.TextAntialiasing
        )
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.AnchorUnderMouse)
        self.setDragMode(QGraphicsView.ScrollHandDrag)

        # Show scrollbars only when needed
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)

    def wheelEvent(self, event):
        # Zoom in / out
        if event.angleDelta().y() > 0:
            factor = self.zoom_factor
        else:
            factor = 1 / self.zoom_factor
        self.scale(factor, factor)

    def mousePressEvent(self, event):
        # Middle mouse button to pan
        if event.button() == Qt.MiddleButton:
            self.setDragMode(QGraphicsView.ScrollHandDrag)
            fake = QMouseEvent(QEvent.MouseButtonPress,
                               event.localPos(),
                               Qt.LeftButton,
                               Qt.LeftButton,
                               Qt.NoModifier)
            super().mousePressEvent(fake)
        else:
            super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MiddleButton:
            fake = QMouseEvent(QEvent.MouseButtonRelease,
                               event.localPos(),
                               Qt.LeftButton,
                               Qt.LeftButton,
                               Qt.NoModifier)
            super().mouseReleaseEvent(fake)
            self.setDragMode(QGraphicsView.NoDrag)
        else:
            super().mouseReleaseEvent(event)


class ASTRenderer:
    """
    Calculates positions for AST nodes and draws them into a QGraphicsScene.
    Fixed: Prevents infinite recursion by separating sibling-chain iteration 
    from single-node placement.
    """

    def __init__(self, scene):
        self.scene = scene
        self.node_positions = {}  # maps node.id -> (x_center, y_top)

    def clear(self):
        self.scene.clear()
        self.node_positions.clear()

    # -------------------------
    # Helpers for sibling chains
    # -------------------------
    def _collect_sibling_chain(self, node):
        """Return list of nodes in the sibling chain starting at node."""
        chain = []
        cur = node
        visited = set()
        while cur and id(cur) not in visited:
            chain.append(cur)
            visited.add(id(cur))
            cur = getattr(cur, "sibling", None)
        return chain

    def _measure_tree_width(self, node, visited=None):
        if not node: return 0
        if visited is None: visited = set()
        
        if id(node) in visited: return NODE_WIDTH 
        current_path_visited = visited.copy()
        current_path_visited.add(id(node))
        
        if getattr(node, "sibling", None):
            return self._measure_sibling_chain_width(node, current_path_visited)

        return self._measure_single_tree_width(node, current_path_visited)
    
    def _measure_single_tree_width(self, node, visited=None):
        if not node: return 0
        if visited is None: visited = set()
        
        if not getattr(node, "children", None):
            return NODE_WIDTH

        child_widths = [self._measure_tree_width(c, visited) for c in node.children if c]
        
        if not child_widths:
            return NODE_WIDTH
            
        total = sum(child_widths) + (len(child_widths) - 1) * CHILD_HORIZONTAL_GAP
        return max(total, NODE_WIDTH)
    
    def _measure_sibling_chain_width(self, node, visited=None):
        if visited is None: visited = set()
            
        chain = self._collect_sibling_chain(node)
        total_width = 0
        
        for i, stmt in enumerate(chain):
            stmt_full_width = self._measure_single_tree_width(stmt, visited.copy()) 
            total_width += stmt_full_width
            if i < len(chain) - 1:
                total_width += SIBLING_HORIZONTAL_GAP
                
        return total_width

    # -------------------------
    # FIXED Placement Logic
    # -------------------------
    def _place_subtree_with_siblings(self, node, left_x, y_top, visited=None):
        """
        Entry point: Determines if we are placing a single node or a chain.
        """
        if not node: return
        if visited is None: visited = set()

        # 1. If this is a chain, handle the horizontal layout here
        if getattr(node, "sibling", None):
            chain = self._collect_sibling_chain(node)

            # Measure full width of the entire chain
            widths = []
            total_width = 0
            for stmt in chain:
                w = self._measure_single_tree_width(stmt, visited.copy())
                widths.append(w)
                total_width += w
            total_width += SIBLING_HORIZONTAL_GAP * (len(chain) - 1)

            # Start at the given left_x (left edge of the chain)
            current_x = left_x

            # Place each sibling subtree left-to-right
            for stmt, w in zip(chain, widths):
                self._place_single_node_only(stmt, current_x, y_top, visited.copy())
                current_x += w + SIBLING_HORIZONTAL_GAP

            return
        # 2. If no sibling, just place this single node structure
        self._place_single_node_only(node, left_x, y_top, visited)

    def _place_single_node_only(self, node, left_x, y_top, visited):
        """
        Places a single node and recursively places its CHILDREN.
        Does NOT handle the node's siblings (handled by caller).
        """
        if id(node) in visited: return
        visited.add(id(node))

        # Use a copy of visited for children to track vertical path
        current_path_visited = visited.copy()

        # -- Logic to place node and children --
        
        # If no children → just center the node
        if not getattr(node, "children", None):
            self.node_positions[node.id] = (left_x + NODE_WIDTH / 2, y_top)
            return

        # 1. Measure children
        child_chains = [self._collect_sibling_chain(child) for child in node.children]
        
        # Measure widths (using the main measure function which handles child siblings)
        chain_widths = [
            self._measure_tree_width(chain[0], current_path_visited.copy()) if chain else 0 
            for chain in child_chains
        ]

        # 2. Calculate total width required by children
        num_chains = len(chain_widths)
        total_children_width = sum(chain_widths) + CHILD_HORIZONTAL_GAP * max(0, num_chains - 1)
        total_children_width = max(total_children_width, NODE_WIDTH) 

        # 3. Place parent node center
        center_x = left_x + total_children_width / 2
        self.node_positions[node.id] = (center_x, y_top)

        # 4. Symmetrically place children around parent center
        start_x = center_x - total_children_width / 2
        cursor = start_x

        for i, (chain, width) in enumerate(zip(child_chains, chain_widths)):
            if chain:
                left_x_child = cursor
                self._place_subtree_with_siblings(
                    chain[0],
                    left_x_child,
                    y_top + VERTICAL_PADDING,
                    current_path_visited
                )

                cursor += width
                if i < num_chains - 1:
                    cursor += CHILD_HORIZONTAL_GAP


    # -------------------------
    # Drawing helpers (Unchanged)
    # -------------------------
    def draw_node_graphics(self, node, visited=None):
        if not node: return
        if visited is None: visited = set()
        if id(node) in visited: return
        visited.add(id(node))

        # If sibling chain head, draw siblings
        if getattr(node, "sibling", None):
            chain = self._collect_sibling_chain(node)
            for i, n in enumerate(chain):
                self._draw_single_node_graphics(n)
                # connector between siblings: right-center of a -> left-center of b
                if i < len(chain) - 1:
                    a, b = chain[i], chain[i+1]
                    if (a.id in self.node_positions) and (b.id in self.node_positions):
                        ax, ay = self.node_positions[a.id]
                        bx, by = self.node_positions[b.id]
                        # Use center y for both, and right edge x for a and left edge x for b
                        y_center = ay + NODE_HEIGHT / 2
                        x_a_right = ax + NODE_WIDTH / 2
                        x_b_left = bx - NODE_WIDTH / 2
                        line = QGraphicsLineItem(x_a_right, y_center, x_b_left, y_center)
                        pen = QPen(DEFAULT_LINE_COLOR); pen.setWidth(3)
                        line.setPen(pen)
                        self.scene.addItem(line)

                # recurse children of this chain node (use a fresh visited for draw recursion)
                for child in getattr(n, "children", []) or []:
                    # use a fresh set for child recursion so drawing isn't blocked by siblings
                    self.draw_node_graphics(child, set())

            return
        else:
            # single node (no sibling chain)
            self._draw_single_node_graphics(node)
            for child in getattr(node, "children", []) or []:
                self.draw_node_graphics(child, set())


    def _draw_single_node_graphics(self, node):
        if node.id not in self.node_positions: return
        cx, y_top = self.node_positions[node.id]
        x_left = cx - NODE_WIDTH / 2
        rect = QRectF(x_left, y_top, NODE_WIDTH, NODE_HEIGHT)

        # Normalize shape: you can customize mapping here
        shape = getattr(node, "shape", "oval")


        if shape == "rect":
            shape_item = QGraphicsRectItem(rect)
        else:
            shape_item = QGraphicsEllipseItem(rect)

        pen = QPen(DEFAULT_NODE_COLOR); pen.setWidth(2)
        shape_item.setPen(pen)
        shape_item.setBrush(QBrush(QColor("#bdbdbd")))
        self.scene.addItem(shape_item)

        label = getattr(node, "node_type", "")
        if getattr(node, "value", None): label += " " + str(node.value)
        text_item = QGraphicsTextItem(label)
        font = QFont("Arial", 9); font.setBold(True)
        text_item.setFont(font)

        tr = text_item.boundingRect()
        text_item.setPos(cx - tr.width() / 2, y_top + (NODE_HEIGHT - tr.height()) / 2)
        self.scene.addItem(text_item)

        # Lines to children: parent bottom-center -> child top-center
        for child in getattr(node, "children", []) or []:
            if not child or child.id not in self.node_positions: continue
            cx_child, y_child = self.node_positions[child.id]
            p1 = QPointF(cx, y_top + NODE_HEIGHT)               # parent bottom-center
            p2 = QPointF(cx_child, y_child)                    # child top-center (y_child is top)
            conn = QGraphicsLineItem(p1.x(), p1.y(), p2.x(), p2.y())
            pen = QPen(DEFAULT_LINE_COLOR); pen.setWidth(3)
            conn.setPen(pen)
            self.scene.addItem(conn)


    def render_root_sequence(self, root):
        self.clear()
        if not root: return
        # ensure nodes have ids (in case parser didn't provide)
        self._ensure_node_ids(root)

        # Place the root (it handles its own siblings now correctly)
        root_total_width = self._measure_tree_width(root, set())
        self._place_subtree_with_siblings(root, -root_total_width / 2.0, 0, set())
        self.draw_node_graphics(root)
        
        # Safer scene rect: compute bounding box of positioned nodes + margin
        if self.node_positions:
            xs = [x for x, y in self.node_positions.values()]
            ys = [y for x, y in self.node_positions.values()]
            min_x, max_x = min(xs), max(xs)
            min_y, max_y = min(ys), max(ys)
            margin_x = NODE_WIDTH * 1.5
            margin_y = NODE_HEIGHT * 1.5
            width = max(1.0, (max_x - min_x) + margin_x * 2)
            height = max(1.0, (max_y - min_y) + margin_y * 2)
            self.scene.setSceneRect(min_x - margin_x, min_y - margin_y, width, height)
    
    def _ensure_node_ids(self, root):
        """Ensure every node reachable from root has a unique .id attribute."""
        counter = 0
        seen = set()
        def walk(n):
            nonlocal counter
            if not n or id(n) in seen:
                return
            seen.add(id(n))
            if not hasattr(n, "id") or n.id is None:
                n.id = f"__node_{counter}"
                counter += 1
            for c in getattr(n, "children", []) or []:
                walk(c)
            sib = getattr(n, "sibling", None)
            if sib:
                walk(sib)
        walk(root)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("TINY Tokens → Parser → AST Viewer")
        self.resize(1100, 700)

        # -----------------------
        # Main layout
        # -----------------------
        root_widget = QWidget()
        self.setCentralWidget(root_widget)
        main_layout = QVBoxLayout()
        root_widget.setLayout(main_layout)
        # --------------------------
        #    WELCOME BANNER
        # --------------------------
        banner = QFrame()
        banner.setObjectName("welcomeBanner")
        banner.setFixedHeight(100)

        banner_layout = QVBoxLayout()
        banner.setLayout(banner_layout)

        self.welcome_label = QLabel("Welcome to Parser Project!")
        self.welcome_label.setAlignment(Qt.AlignCenter)

        # Bigger italic fancy font
        banner_font = QFont("Georgia", 40)
        banner_font.setItalic(True)
        banner_font.setBold(True)
        self.welcome_label.setFont(banner_font)

        banner_layout.addWidget(self.welcome_label)
        main_layout.addWidget(banner)


        # -----------------------
        # Top controls + status
        # -----------------------
        controls_layout = QHBoxLayout()
        main_layout.addLayout(controls_layout)

        # Buttons
        self.load_btn = QPushButton("Load Tokens File")
        self.load_btn.clicked.connect(self.load_tokens_file)
        controls_layout.addWidget(self.load_btn)

        self.parse_btn = QPushButton("Parse Tokens")
        self.parse_btn.clicked.connect(self.parse_tokens)
        controls_layout.addWidget(self.parse_btn)

        self.save_json_btn = QPushButton("Save Parse JSON")
        self.save_json_btn.clicked.connect(self.save_parse_json)
        self.save_json_btn.setEnabled(False)
        controls_layout.addWidget(self.save_json_btn)

        self.status_frame = QFrame()
        self.status_frame.setFrameShape(QFrame.Box)
        self.status_frame.setFrameShadow(QFrame.Raised)
        self.status_frame.setLineWidth(2)
        self.status_frame.setMaximumHeight(50)

        # Label inside frame
        self.status_label = QLabel("Status: Ready")
        self.status_label.setAlignment(Qt.AlignCenter)
        status_font = QFont("Arial", 14, QFont.Bold)  # consistent font
        self.status_label.setFont(status_font)
        self.status_frame.setStyleSheet(f"background-color: {"#ffea00"}; border: 2px solid black;")
        self.status_label.setStyleSheet("color: black;")  # keep text readable

        # Layout for frame
        status_layout = QVBoxLayout()
        status_layout.addWidget(self.status_label)
        status_layout.setContentsMargins(5, 0, 5, 0)
        self.status_frame.setLayout(status_layout)

        # Add to controls
        controls_layout.addWidget(self.status_frame)
        
        # -----------------------
        # Splitter: left = tokens + log, right = graphics
        # -----------------------
        splitter = QSplitter(Qt.Horizontal)
        main_layout.addWidget(splitter)

        # Left panel
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
        splitter.setSizes([350, 750])            # Initial size
        splitter.setStretchFactor(0, 0)          # Left fixed/minimal
        splitter.setStretchFactor(1, 1)          # Right expands fully
        splitter.setCollapsible(0, True)         # Left collapsible
        splitter.setCollapsible(1, False)        # Right stays visible


        # Right panel: graphics view
        self.scene = QGraphicsScene()
        self.view = SyntaxTreeView(self.scene)
        self.view.setRenderHints(QPainter.Antialiasing | QPainter.TextAntialiasing)
        splitter.addWidget(self.view)
        splitter.setSizes([350, 750])

        self.renderer = ASTRenderer(self.scene)
        self.last_parse_result = None
        self.last_tokens = None
        # Lists for clearing drawn items
        self.node_items = []
        self.edge_items = []
    
    def clear_syntax_tree(self):
        self.scene.clear()
        self.scene.setSceneRect(QRectF())
        self.view.resetTransform()

        self.node_items.clear()
        self.edge_items.clear()


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
        self.clear_syntax_tree()
        self.token_text.setPlainText(content)
        self.log_text.clear()
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
        self.log_text.clear()

        try:
            txt = self.token_text.toPlainText().strip()
            if not txt:
                QMessageBox.warning(self, "No Tokens", "Please provide tokens in the textbox or load a token file.")
                return

            tokens = self._parse_token_textarea(txt)
            if not tokens:
                QMessageBox.warning(self, "No Valid Tokens", "No valid tokens parsed from the input.")
                return

            # Keep last tokens
            self.last_tokens = tokens

            # Run the parser
            parser = parser_module.Parser(tokens)
            result = parser.parse()
            self.last_parse_result = result

            status_text = result['status']
            self.status_label.setText(f"Status: {status_text}")

            # Dynamic status frame color
            if status_text == "Ready":
                color = "#ffea00"
            elif status_text == "Accepted":
                color = "#00ff00"
            else:
                color = "#ff4444"

            self.status_frame.setStyleSheet(
                f"background-color: {color}; border: 2px solid black;"
            )
            self.status_label.setStyleSheet("color: black;")

            # Log errors
            if result['errors']:
                self.log_text.append("Errors:")
                for e in result['errors']:
                    self.log_text.append("  - " + e)

                # ❌ DO NOT RENDER ANY AST IF THERE ARE ERRORS
                self.renderer.clear()
                self.clear_syntax_tree()
                self.save_json_btn.setEnabled(False)
                QMessageBox.information(self, "Parse Result",
                                        "Errors found. AST will not be rendered.")
                return

            else:
                self.log_text.append("No syntax errors detected.")
                self.save_json_btn.setEnabled(True)

            # At this point we know: NO ERRORS → safe to render
            root = result.get("root")
            if root:
                self.renderer.clear()
                self.clear_syntax_tree()
                self.renderer.render_root_sequence(root)
                # Do NOT auto-fit the scene to the view; allow scrollbars + zoom/pan
                # instead center the view on (0,0) or first node if you prefer
                try:
                    # center on first node if available
                    if self.renderer.node_positions:
                        first_pos = next(iter(self.renderer.node_positions.values()))
                        self.view.centerOn(first_pos[0], first_pos[1])
                    else:
                        self.view.centerOn(0, 0)
                except Exception:
                    self.view.centerOn(0, 0)
            else:
                self.renderer.clear()
                self.clear_syntax_tree()
                QMessageBox.information(self, "Parse Result",
                                        "No AST produced. See log for details.")

        except Exception as e:
            # Unexpected parsing failure (real exceptions)
            self.renderer.clear()
            self.clear_syntax_tree()
            self.save_json_btn.setEnabled(False)

            self.status_label.setText("Status: Error")
            self.status_frame.setStyleSheet(
                "background-color: #ff4444; border: 2px solid black;"
            )

            self.log_text.append("Unexpected error: " + str(e))


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
    app.setStyleSheet("""
    QWidget {
        background-color: #2b2b2b;       /* Dark grey */
        color: #e0e0e0;                  /* Light grey text */
        font-size: 14px;
    }
    QGraphicsView {
        background-color: #3b003b;       /* Deep purple background */
        border: 1px solid #6a1b9a;
    }
    QPushButton {
        background-color: #6a1b9a;       /* Purple */
        border-radius: 6px;
        padding: 6px 12px;
        color: white;
    }
    QPushButton:hover {
        background-color: #8e24aa;
    }
    QPushButton:pressed {
        background-color: #4a0072;
    }
    QLineEdit, QTextEdit {
        background-color: #1e1e1e;
        border: 1px solid #6a1b9a;
        border-radius: 4px;
        padding: 4px;
    }
    QScrollBar:vertical {
        background: #1e1e1e;
        width: 12px;
        margin: 0px;
    }
    QScrollBar::handle:vertical {
        background: #6a1b9a;
        min-height: 20px;
        border-radius: 4px;
    }
    QScrollBar::handle:vertical:hover {
        background: #8e24aa;
    }
    #welcomeBanner {
        border-radius: 20px;
        padding: 6px;
        margin-top: 12px;
        margin-bottom: 12px;

        /* Pretty purple gradient */
        background: qlineargradient(
            x1:0, y1:0,
            x2:1, y2:0,
            stop:0 #9b4dff,
            stop:1 #d785ff
        );
        border: 2px solid #e9b7ff;
    }

    #welcomeBanner QLabel {
        background: transparent;        
        color: white;
    }


""")

    win = MainWindow()
    win.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
