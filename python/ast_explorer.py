"""
python/ast_explorer.py — Exploration and analysis of AST MDX.

Demonstrated case: a price analysis pipeline that automatically extracts
the structure, mathematical formulas, components used, and
generates an actionable summary (JSON) from an MDX document.

Usage: python ast_explorer.py
"""

import json
import toaq_mdx
from toaq_mdx.ast import AstNode
from typing import List, Dict, Any


DEFAULT_MDX = """
# Classical Mechanics

## Newton's Laws

Newton's first law states that an object remains at rest or in uniform motion
unless an external force acts on it.

The second law states that:

$$ F = ma $$

Where $F$ is the force in Newtons, $m$ is the mass in kilograms, and $a$ is the acceleration.

<Note type="warning" title="Be careful with units">
  Always check that $F$ is in Newtons, $m$ is in kg, and $a$ is in $m/s^2$.
</Note>

## Kinetic energy

The kinetic energy of an object of mass $m$ moving at velocity $v$ is:

$$ E_k = \\frac{1}{2}mv^2 $$

<Details title="Demonstration by integration">
  We start with the work $W = \\int F \\cdot dx$ and apply $F = ma$:
  $$ W = \\int ma \\cdot dx = m \\int a \\cdot dx $$
  This gives $E_k = \\frac{1}{2}mv^2$.
</Details>

## Momentum

<Table
  caption="Fundamental quantities"
  headers={[“Quantity”, “Symbol”, “Unit”]}
  data={[
    [“Force”, 'F', “Newton (N)”],
    [“Mass”, 'm', “Kilogram (kg)”],
    [“Acceleration”, 'a', “m/s²”],
    [“Energy”, 'E', “Joule (J)”]
  ]}
/>

Momentum is defined by $p = mv$.

## Conclusion

These three laws form the basis of **classical mechanics** and allow
the motion of any macroscopic object to be described.
"""


def extract_headings(nodes: List[AstNode]) -> List[Dict[str, Any]]:
    """Extracts the table of contents."""
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
    """Extracts all inline and block formulas."""
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
    """Extracts the JSX components used with their text attributes."""
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
    """Counts the words in the plain text (excluding math and components)."""
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
    """Builds a comprehensive summary of the document."""
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



if __name__ == "__main__":
    ast = toaq_mdx.parse(DEFAULT_MDX)

    summary = build_summary(ast)

    print("─" * 40)
    for h in summary["table_of_contents"]:
        indent = "  " * (h["level"] - 1)
        print(f"{indent}{'#' * h['level']} {h['text']}")

    print("─" * 40)
    s = summary["stats"]
    print(f"  Mots           : {s['word_count']}")
    print(f"  Sections (h2)  : {s['section_count']}")
    print(f"  Formules inline: {s['inline_math_count']}")
    print(f"  Formules block : {s['block_math_count']}")
    print(f"  Composants JSX : {s['component_count']}")

    print("─" * 40)
    for f in summary["formulas"]["block"]:
        print(f"  [block]  $$ {f.strip()} $$")
    for f in summary["formulas"]["inline"]:
        print(f"  [inline] $ {f} $")

    print("─" * 40)
    for c in summary["components"]:
        attrs = ", ".join(f"{k}={v!r}" for k, v in c["attrs"].items())
        closing = "/>" if c["self_closing"] else f">...</{c['type']}>"
        print(f"  <{c['type']} {attrs} {closing}")

    out_path = "ast_summary.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)