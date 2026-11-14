#!/usr/bin/env python3
"""
Generador de árboles de derivación a partir de:
  1) un archivo de gramática (reglas)
  2) un archivo con la secuencia de pasos de derivación (una producción por línea)

El programa NO infiere producciones: solo aplica los pasos dados, comprobando
que cada uno pertenezca a la gramática, y construye el árbol correspondiente.

Uso:
  python3 derivador.py GRAMATICA.txt PASOS.txt --modo izq
  python3 derivador.py GRAMATICA.txt PASOS.txt --modo der

Cada línea de PASOS es una producción "A -> X Y Z". Opcionalmente puede llevar
el sufijo "@k" para indicar cuál no terminal (contando desde 0, de izquierda a
derecha, en la forma sentencial actual) se expande; si no se indica, se usa
--modo (izq = el más a la izquierda, der = el más a la derecha).
"""
import argparse
import sys

EPS = {"ε", "eps", "epsilon"}


class Nodo:
    """Nodo del árbol: símbolo, regla usada (si es no terminal) e hijos."""
    def __init__(self, simbolo):
        self.simbolo = simbolo
        self.regla = None      # (lhs, rhs) aplicada a este nodo
        self.hijos = []
        self.id = None


# ---------------------------------------------------------------- lectura
def leer_gramatica(ruta):
    inicio, reglas = None, {}
    with open(ruta, encoding="utf-8") as f:
        for linea in f:
            linea = linea.split("#")[0].strip()
            if not linea:
                continue
            if linea.startswith("inicio:"):
                inicio = linea.split(":", 1)[1].strip()
                continue
            izq, der = linea.split(" -> ", 1)   # solo la primera flecha separa la regla
            izq = izq.strip()
            for alt in der.split(" | "):
                cuerpo = tuple(s for s in alt.split() if s not in EPS)
                reglas.setdefault(izq, []).append(cuerpo)
    if inicio is None:
        sys.exit("Error: falta la línea 'inicio: S' en la gramática.")
    return inicio, reglas


def leer_pasos(ruta):
    pasos = []
    with open(ruta, encoding="utf-8") as f:
        for linea in f:
            linea = linea.split("#")[0].strip()
            if not linea:
                continue
            pos = None
            if "@" in linea:
                linea, k = linea.rsplit("@", 1)
                pos = int(k)
            izq, der = linea.split(" -> ", 1)
            cuerpo = tuple(s for s in der.split() if s not in EPS)
            pasos.append((izq.strip(), cuerpo, pos))
    return pasos


# ---------------------------------------------------------------- derivación
def derivar(inicio, reglas, pasos, modo):
    """Aplica los pasos y devuelve (raíz, formas sentenciales, pasos resueltos)."""
    raiz = Nodo(inicio)
    forma = [raiz]
    formas = [[n.simbolo for n in forma]]
    resueltos = []
    for num, (izq, cuerpo, pos) in enumerate(pasos, 1):
        idx_nt = [i for i, n in enumerate(forma) if n.simbolo in reglas]
        if not idx_nt:
            sys.exit(f"Paso {num}: no quedan no terminales por expandir.")
        if pos is None:
            i = idx_nt[0] if modo == "izq" else idx_nt[-1]
        else:
            i = idx_nt[pos]
        nodo = forma[i]
        if nodo.simbolo != izq:
            sys.exit(f"Paso {num}: se esperaba expandir '{nodo.simbolo}' pero la "
                     f"producción dada es de '{izq}'.")
        if cuerpo not in reglas[izq]:
            sys.exit(f"Paso {num}: '{izq} -> {' '.join(cuerpo)}' no pertenece a la gramática.")
        nodo.regla = (izq, cuerpo)
        nodo.hijos = [Nodo(s) for s in cuerpo]
        forma[i:i + 1] = nodo.hijos
        formas.append([n.simbolo for n in forma])
        resueltos.append((izq, cuerpo, i))
    return raiz, formas, resueltos


def hojas(nodo):
    if not nodo.hijos:
        return [nodo.simbolo] if nodo.regla is None else []
    return [h for c in nodo.hijos for h in hojas(c)]


def derivacion_desde_arbol(raiz, reglas, modo):
    """Reconstruye la derivación (izq/der) leyendo solo el árbol."""
    forma, pasos = [raiz], []
    while True:
        idx = [i for i, n in enumerate(forma) if n.regla is not None]
        if not idx:
            return pasos
        i = idx[0] if modo == "izq" else idx[-1]
        n = forma[i]
        pasos.append(n.regla)
        forma[i:i + 1] = n.hijos


# ---------------------------------------------------------------- salida
def numerar(raiz):
    cont, orden = [1], []
    def rec(n):
        n.id = cont[0]; cont[0] += 1
        orden.append(n)
        for h in n.hijos:
            rec(h)
    rec(raiz)
    return orden


def imprimir_arbol(nodo, prefijo="", ultimo=True, raiz=True):
    """Árbol jerárquico textual (terminales y no terminales)."""
    etiqueta = nodo.simbolo + (f"   [{nodo.id}]" if nodo.id else "")
    if raiz:
        print(etiqueta)
    else:
        print(prefijo + ("└── " if ultimo else "├── ") + etiqueta)
    nuevo = "" if raiz else prefijo + ("    " if ultimo else "│   ")
    for i, h in enumerate(nodo.hijos):
        imprimir_arbol(h, nuevo, i == len(nodo.hijos) - 1, False)


def tabla_derivacion(inicio, formas, resueltos):
    print(f"{'Paso':<5}| {'Forma sentencial':<60}| Regla aplicada")
    print("-" * 5 + "+" + "-" * 61 + "+" + "-" * 30)
    print(f"{0:<5}| {' '.join(formas[0]):<60}| (símbolo inicial)")
    for k, (f, (izq, cuerpo, _)) in enumerate(zip(formas[1:], resueltos), 1):
        print(f"{k:<5}| {'⇒ ' + ' '.join(f):<60}| {izq} → {' '.join(cuerpo) or 'ε'}")


def tabla_arbol(orden):
    print(f"{'Nodo':<5}| {'Símbolo':<8}| {'Regla aplicada':<24}| Hijos (nodos)")
    print("-" * 5 + "+" + "-" * 9 + "+" + "-" * 25 + "+" + "-" * 20)
    for n in orden:
        regla = f"{n.regla[0]} → {' '.join(n.regla[1])}" if n.regla else "(terminal)"
        hijos = ", ".join(f"{h.simbolo}[{h.id}]" for h in n.hijos) or "—"
        print(f"{n.id:<5}| {n.simbolo:<8}| {regla:<24}| {hijos}")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument("gramatica")
    ap.add_argument("pasos")
    ap.add_argument("--modo", choices=["izq", "der"], default="izq")
    a = ap.parse_args()

    inicio, reglas = leer_gramatica(a.gramatica)
    pasos = leer_pasos(a.pasos)
    raiz, formas, resueltos = derivar(inicio, reglas, pasos, a.modo)
    orden = numerar(raiz)

    print(f"=== Derivación por la {'izquierda' if a.modo == 'izq' else 'derecha'} ===")
    tabla_derivacion(inicio, formas, resueltos)
    print("\n=== Árbol de derivación (jerárquico) ===")
    imprimir_arbol(raiz)
    print("\n=== Árbol de derivación (tabla) ===")
    tabla_arbol(orden)

    cadena = " ".join(hojas(raiz))
    print("\n=== Verificación ===")
    print("Cadena (hojas del árbol)  :", cadena)
    print("Forma sentencial final    :", " ".join(formas[-1]))
    print("Hojas == forma final      :", cadena == " ".join(formas[-1]))
    print("Sin no terminales pendientes:", all(s not in reglas for s in formas[-1]))
    dado = [(l, c) for l, c, _ in resueltos]
    for modo, nombre in (("izq", "izquierda"), ("der", "derecha")):
        rec = derivacion_desde_arbol(raiz, reglas, modo)
        print(f"Árbol reproduce la derivación por la {nombre} dada: {rec == dado}")


if __name__ == "__main__":
    main()
