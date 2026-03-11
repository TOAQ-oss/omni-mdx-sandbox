"""
sandbox/python/ast_explorer.py — Exploration et analyse de l'AST MDX.

Cas démontré : un pipeline d'analyse de cours qui extrait automatiquement
la structure, les formules mathématiques, les composants utilisés et
génère un résumé exploitable (JSON) depuis un document MDX.

Usage : python ast_explorer.py
"""

import json
import toaq_mdx
from toaq_mdx.ast import AstNode
from typing import List, Dict, Any


MDX_COURS = """
# Mécanique classique

## Lois de Newton

La **première loi de Newton** stipule qu'un objet reste en repos ou en mouvement
uniforme à moins qu'une force extérieure n'agisse sur lui.

La deuxième loi établit que :

$$ F = ma $$

Où $F$ est la force en Newtons, $m$ la masse en kilogrammes et $a$ l'accélération.

<Note type="warning" title="Attention aux unités">
  Vérifiez toujours que $F$ est en Newtons, $m$ en kg et $a$ en $m/s^2$.
</Note>

## Énergie cinétique

L'énergie cinétique d'un objet de masse $m$ se déplaçant à vitesse $v$ est :

$$ E_k = \\frac{1}{2}mv^2 $$

<Details title="Démonstration par intégration">
  On part du travail $W = \\int F \\cdot dx$ et on applique $F = ma$ :
  $$ W = \\int ma \\cdot dx = m \\int a \\cdot dx $$
  Ce qui donne bien $E_k = \\frac{1}{2}mv^2$.
</Details>

## Quantité de mouvement

<Table
  caption="Grandeurs fondamentales"
  headers={["Grandeur", "Symbole", "Unité"]}
  data={[
    ["Force", "F", "Newton (N)"],
    ["Masse", "m", "Kilogramme (kg)"],
    ["Accélération", "a", "m/s²"],
    ["Énergie", "E", "Joule (J)"]
  ]}
/>

La quantité de mouvement est définie par $p = mv$.

## Conclusion

Ces trois lois forment la base de la **mécanique classique** et permettent
de décrire le mouvement de tout objet macroscopique.
"""


# ── Analyse ───────────────────────────────────────────────────────────────────

def extract_headings(nodes: List[AstNode]) -> List[Dict[str, Any]]:
    """Extrait la table des matières."""
    headings = []
    def walk(nodes):
        for node in nodes:
            if node.is_heading:
                level = int(node.node_type[1])
                headings.append({"level": level, "text": node.text_content()})
            walk(node.children)
    walk(nodes)
    return headings


def extract_math(nodes: List[AstNode]) -> Dict[str, List[str]]:
    """Extrait toutes les formules inline et block."""
    inline, block = [], []
    def walk(nodes):
        for node in nodes:
            if node.is_inline_math:
                inline.append(node.content or "")
            elif node.is_block_math:
                block.append(node.content or "")
            walk(node.children)
    walk(nodes)
    return {"inline": inline, "block": block}


def extract_components(nodes: List[AstNode]) -> List[Dict[str, Any]]:
    """Extrait les composants JSX utilisés avec leurs attributs texte."""
    components = []
    def walk(nodes):
        for node in nodes:
            if node.is_component:
                components.append({
                    "type": node.node_type,
                    "attrs": {
                        k: v.text for k, v in node.attributes.items() if v.is_text
                    },
                    "has_children": len(node.children) > 0,
                    "self_closing": node.self_closing,
                })
            walk(node.children)
    walk(nodes)
    return components


def count_words(nodes: List[AstNode]) -> int:
    """Compte les mots dans le texte brut (hors math et composants)."""
    total = 0
    def walk(nodes):
        nonlocal total
        for node in nodes:
            if node.is_text and node.content:
                total += len(node.content.split())
            if not node.is_component:
                walk(node.children)
    walk(nodes)
    return total


def build_summary(nodes: List[AstNode]) -> Dict[str, Any]:
    """Construit un résumé complet du document."""
    headings   = extract_headings(nodes)
    math       = extract_math(nodes)
    components = extract_components(nodes)
    words      = count_words(nodes)

    return {
        "table_of_contents": headings,
        "stats": {
            "word_count":        words,
            "inline_math_count": len(math["inline"]),
            "block_math_count":  len(math["block"]),
            "component_count":   len(components),
            "section_count":     sum(1 for h in headings if h["level"] == 2),
        },
        "formulas": math,
        "components": components,
    }


# ── Main ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("╔══════════════════════════════════════════╗")
    print("║         AST Explorer — MDX Parser        ║")
    print("╚══════════════════════════════════════════╝\n")

    ast = toaq_mdx.parse(MDX_COURS)

    summary = build_summary(ast)

    # ── Table des matières ────────────────────────────────────────────────────
    print("📑 Table des matières")
    print("─" * 40)
    for h in summary["table_of_contents"]:
        indent = "  " * (h["level"] - 1)
        print(f"{indent}{'#' * h['level']} {h['text']}")

    # ── Stats ─────────────────────────────────────────────────────────────────
    print("\n📊 Statistiques")
    print("─" * 40)
    s = summary["stats"]
    print(f"  Mots           : {s['word_count']}")
    print(f"  Sections (h2)  : {s['section_count']}")
    print(f"  Formules inline: {s['inline_math_count']}")
    print(f"  Formules block : {s['block_math_count']}")
    print(f"  Composants JSX : {s['component_count']}")

    # ── Formules ──────────────────────────────────────────────────────────────
    print("\n∑ Formules mathématiques")
    print("─" * 40)
    for f in summary["formulas"]["block"]:
        print(f"  [block]  $$ {f.strip()} $$")
    for f in summary["formulas"]["inline"]:
        print(f"  [inline] $ {f} $")

    # ── Composants ────────────────────────────────────────────────────────────
    print("\n🧩 Composants JSX")
    print("─" * 40)
    for c in summary["components"]:
        attrs = ", ".join(f"{k}={v!r}" for k, v in c["attrs"].items())
        closing = "/>" if c["self_closing"] else f">...</{c['type']}>"
        print(f"  <{c['type']} {attrs} {closing}")

    # ── Export JSON ───────────────────────────────────────────────────────────
    out_path = "ast_summary.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    print(f"\n✅ Résumé exporté → {out_path}")