"use client";
import { useEffect, useMemo, useState } from 'react';
import initWasm, { MDXViewer, parse_mdx_to_json } from '@toaq-oss/mdx-engine';
import { MDX_COMPONENTS } from './components/MDXComponents';
import "katex/dist/katex.min.css";

const markdownContent = `
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

Du texte avec **gras**, *italique*, ~~barré~~ et \`code inline\`.

> *"La simplicité est la sophistication suprême."*

## Liste

- Premier élément
- Deuxième élément
  - Sous-élément imbriqué
- Troisième élément

## Séparateur

---

Texte après le séparateur.
`;

const myConfig = {
  features: { math: true },
  components: MDX_COMPONENTS,
};

export default function TestPage() {
  const [isReady, setIsReady] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    initWasm()
      .then(() => setIsReady(true))
      .catch((err) => {
        console.error("Échec du chargement du moteur Rust:", err);
        setError("Impossible de charger le moteur de rendu.");
      });
  }, []);

  const { ast, parseError } = useMemo(() => {
    if (!isReady || !markdownContent) return { ast: null, parseError: null };

    try {
      const jsonAst = parse_mdx_to_json(markdownContent);
      return { 
        ast: JSON.parse(jsonAst), 
        parseError: null 
      };
    } catch (err) {
      return { 
        ast: null, 
        parseError: err instanceof Error ? err.message : String(err) 
      };
    }
  }, [isReady, markdownContent]);

  if (error || parseError) return <p className="p-8 text-red-600">Erreur : {error || parseError}</p>;
  if (!isReady || !ast) return <p className="p-8">Chargement du moteur Rust ultra-rapide...</p>;

  return (
    <main className="max-w-3xl mx-auto p-8">
      <MDXViewer ast={ast} config={{ features: { math: true }, components: MDX_COMPONENTS }} />
    </main>
  );
}