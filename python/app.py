"""
sandbox/python/app.py — Rendu MDX 100% natif PyQt5.

Démontre que le moteur AST est complètement découplé du rendu :
chaque AstNode est traduit en widget Qt natif, sans HTML ni WebEngine.

Usage :
    pip install PyQt5 matplotlib
    python app.py
"""

import sys
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QSplitter, QTextEdit,
    QScrollArea, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QSizePolicy, QStatusBar, QShortcut, QLayout
)
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QFont, QKeySequence, QColor, QPalette
from typing import Optional

import toaq_mdx
from toaq_mdx.qt_renderer import QtRenderer


# ══════════════════════════════════════════════════════════════════════════════
#  Éditeur MDX
# ══════════════════════════════════════════════════════════════════════════════

class MDXEditor(QTextEdit):
    def __init__(self, parent=None):
        super().__init__(parent)
        font = QFont("JetBrains Mono", 10)
        font.setStyleHint(QFont.Monospace)
        self.setFont(font)
        self.setAcceptRichText(False)
        self.setStyleSheet(
            "QTextEdit{background:#1e1e2e;color:#cdd6f4;border:none;"
            "padding:16px;selection-background-color:#45475a;}"
        )


# ══════════════════════════════════════════════════════════════════════════════
#  Fenêtre principale
# ══════════════════════════════════════════════════════════════════════════════

class MDXWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("MDX Renderer — PyQt5 natif")
        self.resize(1280, 820)
        self._renderer = QtRenderer()
        self._debounce = QTimer(singleShot=True, interval=800)
        self._debounce.timeout.connect(self._render)
        self._build_ui()
        self._render()

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── Toolbar ───────────────────────────────────────────────────────────
        toolbar = QWidget()
        toolbar.setFixedHeight(44)
        toolbar.setStyleSheet("background:#13131f;border-bottom:1px solid #2d2d3f;")
        tbl = QHBoxLayout(toolbar)
        tbl.setContentsMargins(16, 0, 16, 0)
        tbl.setSpacing(10)

        title = QLabel("⚡ MDX Renderer")
        title.setStyleSheet("color:#a78bfa;font-weight:600;font-size:14px;")
        badge = QLabel("PyQt5 · Rust · 0 HTML")
        badge.setStyleSheet(
            "color:#64748b;font-size:11px;background:#1e1e2e;"
            "padding:2px 10px;border-radius:10px;"
        )
        btn = QPushButton("▶  Render  Ctrl+↵")
        btn.setFixedHeight(28)
        btn.setCursor(Qt.PointingHandCursor)
        btn.setStyleSheet("""
            QPushButton{background:#7c3aed;color:white;border:none;
                        border-radius:5px;padding:0 14px;font-size:12px;font-weight:500;}
            QPushButton:hover{background:#6d28d9;}
            QPushButton:pressed{background:#5b21b6;}
        """)
        btn.clicked.connect(self._render)
        tbl.addWidget(title); tbl.addWidget(badge); tbl.addStretch(); tbl.addWidget(btn)
        root.addWidget(toolbar)

        # ── Splitter ──────────────────────────────────────────────────────────
        splitter = QSplitter(Qt.Horizontal)
        splitter.setHandleWidth(1)
        splitter.setStyleSheet("QSplitter::handle{background:#2d2d3f;}")

        # Panneau éditeur
        ep = QWidget(); ep.setStyleSheet("background:#1e1e2e;")
        el = QVBoxLayout(ep); el.setContentsMargins(0,0,0,0); el.setSpacing(0)
        el_lbl = QLabel("  ✏️  Éditeur MDX")
        el_lbl.setFixedHeight(32)
        el_lbl.setStyleSheet(
            "background:#13131f;color:#475569;font-size:11px;"
            "font-weight:600;letter-spacing:.05em;border-bottom:1px solid #2d2d3f;"
        )
        self.editor = MDXEditor()
        self.editor.setPlainText(DEFAULT_MDX)
        self.editor.textChanged.connect(lambda: self._debounce.start())
        el.addWidget(el_lbl); el.addWidget(self.editor)

        # Panneau preview (scroll area)
        pp = QWidget(); pp.setStyleSheet("background:#f8fafc;")
        pl = QVBoxLayout(pp); pl.setContentsMargins(0,0,0,0); pl.setSpacing(0)
        pl_lbl = QLabel("  🧩  Rendu natif PyQt5")
        pl_lbl.setFixedHeight(32)
        pl_lbl.setStyleSheet(
            "background:#f1f5f9;color:#475569;font-size:11px;"
            "font-weight:600;letter-spacing:.05em;border-bottom:1px solid #e2e8f0;"
        )
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setStyleSheet(
            "QScrollArea{border:none;background:#f8fafc;}"
            "QScrollBar:vertical{background:#e2e8f0;width:8px;border-radius:4px;}"
            "QScrollBar::handle:vertical{background:#94a3b8;border-radius:4px;}"
        )
        placeholder = QWidget()
        placeholder.setStyleSheet("background:#f8fafc;")
        self.scroll.setWidget(placeholder)
        pl.addWidget(pl_lbl); pl.addWidget(self.scroll)

        splitter.addWidget(ep); splitter.addWidget(pp)
        splitter.setSizes([480, 800])
        root.addWidget(splitter)

        # ── Status bar ────────────────────────────────────────────────────────
        self.status = QStatusBar()
        self.status.setStyleSheet(
            "background:#13131f;color:#475569;font-size:11px;"
            "border-top:1px solid #2d2d3f;"
        )
        self.setStatusBar(self.status)
        QShortcut(QKeySequence("Ctrl+Return"), self, self._render)

    def _is_likely_complete(self, mdx: str) -> bool:
        """
        Vérification légère avant d'envoyer au parser Rust :
        - les balises JSX ouvertes ont une fermeture correspondante
        - pas de tag ouvert en cours de frappe (ex: "<Note" sans ">")
        """
        import re
        # Tag ouvert mais pas encore fermé (utilisateur en train de taper)
        if re.search(r'<[A-Z][^>]*$', mdx, re.MULTILINE):
            return False
        # Compter les ouvertures/fermetures JSX (composants uppercase)
        opens  = len(re.findall(r'<([A-Z][a-zA-Z]*)[^/]', mdx))
        closes = len(re.findall(r'</([A-Z][a-zA-Z]*)>', mdx))
        selfcl = len(re.findall(r'<[A-Z][^>]*/>', mdx))
        return (opens - selfcl) <= closes

    def _render(self):
        mdx = self.editor.toPlainText()
        # Ne pas tenter le parse si le MDX est visiblement incomplet
        if not self._is_likely_complete(mdx):
            self.status.showMessage("⏳  En cours de saisie...")
            return
        try:
            ast = toaq_mdx.parse(mdx)

            wrapper = QWidget()
            wrapper.setStyleSheet("background:#f8fafc;")
            wrapper.setMinimumWidth(400)
            wl = QVBoxLayout(wrapper)
            wl.setContentsMargins(32, 24, 32, 32)
            wl.setSpacing(0)
            wl.addWidget(self._renderer.render(ast, parent=wrapper))

            self.scroll.setWidget(wrapper)
            self.status.showMessage(
                f"✅  Rendu OK — {len(ast)} nœuds racine, 0 HTML généré"
            )
        except Exception as e:
            import traceback; traceback.print_exc()
            err = QLabel(f"❌  Erreur de parsing :\n{e}")
            err.setStyleSheet(
                "background:#fef2f2;color:#991b1b;padding:16px;"
                "border-radius:6px;font-family:monospace;"
            )
            err.setWordWrap(True)
            w = QWidget(); wl = QVBoxLayout(w)
            wl.addWidget(err); wl.addStretch()
            self.scroll.setWidget(w)
            self.status.showMessage(f"❌  Erreur : {e}")


# ══════════════════════════════════════════════════════════════════════════════
#  Contenu par défaut
# ══════════════════════════════════════════════════════════════════════════════

DEFAULT_MDX = """\
# Mécanique classique

## Lois de Newton

La **deuxième loi de Newton** établit que la résultante des forces
est proportionnelle à l'*accélération* du système :

$$ F = ma $$

Où $F$ est la force en Newtons, $m$ la masse et $a$ l'accélération.

<Note type="warning" title="Attention aux unités">
  Vérifiez que $F$ est en Newtons, $m$ en kg et $a$ en $m/s^2$.
</Note>

## Énergie cinétique

L'énergie cinétique est donnée par :

$$ E_k = \\frac{1}{2}mv^2 $$

<Details title="Voir la démonstration">
  On part du travail $W = \\int F\\,dx$ et on substitue $F = ma$ :
  $$ W = m\\int a\\,dx = \\frac{1}{2}mv^2 $$
  Ce qui donne bien l'expression de l'énergie cinétique.
</Details>

## Formatage inline

Du texte avec **gras**, *italique*, ~~barré~~ et `code inline`.

> *"La simplicité est la sophistication suprême."*

## Liste

- Premier élément
- Deuxième élément
  - Sous-élément imbriqué
- Troisième élément

---

Texte après le séparateur.
"""


# ══════════════════════════════════════════════════════════════════════════════
#  Main
# ══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    palette = QPalette()
    palette.setColor(QPalette.Window,          QColor("#f8fafc"))
    palette.setColor(QPalette.WindowText,      QColor("#1a202c"))
    palette.setColor(QPalette.Base,            QColor("#ffffff"))
    palette.setColor(QPalette.Text,            QColor("#1a202c"))
    palette.setColor(QPalette.Button,          QColor("#f1f5f9"))
    palette.setColor(QPalette.ButtonText,      QColor("#1a202c"))
    palette.setColor(QPalette.Highlight,       QColor("#7c3aed"))
    palette.setColor(QPalette.HighlightedText, QColor("#ffffff"))
    app.setPalette(palette)
    window = MDXWindow()
    window.show()
    sys.exit(app.exec_())