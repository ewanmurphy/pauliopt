from pauliopt.pauli.clifford_gates import CliffordGate
from pauliopt.pauli.pauli_gadget import PauliGadget

from pauliopt.topologies import Topology
import math
from pauliopt.pauli.utils import X, Y, Z, I
from pauliopt.utils import SVGBuilder
import numpy as np

LATEX_HEADER = """\documentclass[preview]{standalone}

\\usepackage{tikz}
\\usetikzlibrary{zx-calculus}
\\usetikzlibrary{quantikz}
\\usepackage{graphicx}

\\tikzset{
diagonal fill/.style 2 args={fill=#2, path picture={
\\fill[#1, sharp corners] (path picture bounding box.south west) -|
                         (path picture bounding box.north east) -- cycle;}},
reversed diagonal fill/.style 2 args={fill=#2, path picture={
\\fill[#1, sharp corners] (path picture bounding box.north west) |- 
                         (path picture bounding box.south east) -- cycle;}}
}

\\tikzset{
diagonal fill/.style 2 args={fill=#2, path picture={
\\fill[#1, sharp corners] (path picture bounding box.south west) -|
                         (path picture bounding box.north east) -- cycle;}}
}

\\tikzset{
pauliY/.style={
zxAllNodes,
zxSpiders,
inner sep=0mm,
minimum size=2mm,
shape=rectangle,
%fill=colorZxX
diagonal fill={colorZxX}{colorZxZ}
}
}

\\tikzset{
pauliX/.style={
zxAllNodes,
zxSpiders,
inner sep=0mm,
minimum size=2mm,
shape=rectangle,
fill=colorZxX
}
}

\\tikzset{
pauliZ/.style={
zxAllNodes,
zxSpiders,
inner sep=0mm,
minimum size=2mm,
shape=rectangle,
fill=colorZxZ
}
}

\\tikzset{
pauliPhase/.style={
zxAllNodes,
zxSpiders,
inner sep=0.5mm,
minimum size=2mm,
shape=rectangle,
fill=white
}
}
"""


class PauliPolynomial:
    def __init__(self, num_qubits):
        self.num_qubits = num_qubits
        self.pauli_gadgets = []

    def __irshift__(self, gadget: PauliGadget):
        if not len(gadget) == self.num_qubits:
            raise Exception(
                f"Pauli Polynomial has {self.num_qubits}, but Pauli gadget has: {len(gadget)}")
        self.pauli_gadgets.append(gadget)
        return self

    def __rshift__(self, pauli_polynomial):
        for gadget in pauli_polynomial.pauli_gadgets:
            self.pauli_gadgets.append(gadget)
        return self

    def __repr__(self):
        return '\n'.join(map(repr, self.pauli_gadgets))

    def __len__(self):
        return len(self.pauli_gadgets)

    @property
    def num_gadgets(self):
        return len(self.pauli_gadgets)

    def num_legs(self):
        legs = 0
        for gadget in self.pauli_gadgets:
            legs += gadget.num_legs()
        return legs

    def to_qiskit(self, topology=None):
        num_qubits = self.num_qubits
        if topology is None:
            topology = Topology.complete(num_qubits)
        try:
            from qiskit import QuantumCircuit
        except:
            raise Exception("Please install qiskit to export Clifford Regions")

        qc = QuantumCircuit(num_qubits)
        for gadget in self.pauli_gadgets:
            qc.compose(gadget.to_qiskit(topology), inplace=True)

        return qc

    def propagate(self, gate: CliffordGate):
        pp_ = PauliPolynomial(self.num_qubits)
        for gadget in self.pauli_gadgets:
            pp_ >>= gate.propagate_pauli(gadget)
        return pp_

    def copy(self):
        pp_ = PauliPolynomial(self.num_qubits)
        for gadget in self.pauli_gadgets:
            pp_ >>= gadget.copy()
        return pp_

    def two_qubit_count(self, topology, leg_cache=None):
        if leg_cache is None:
            leg_cache = {}
        count = 0
        for gadget in self.pauli_gadgets:
            count += gadget.two_qubit_count(topology, leg_cache=leg_cache)
        return count

    def commutes(self, col1, col2):
        gadet1 = self.pauli_gadgets[col1]
        gadet2 = self.pauli_gadgets[col2]
        return gadet1.commutes(gadet2)

    def mutual_legs(self, col1, col2):
        gadet1 = self.pauli_gadgets[col1]
        gadet2 = self.pauli_gadgets[col2]
        return gadet1.mutual_legs(gadet2)

    def to_svg(self, hscale: float = 1.0, vscale: float = 1.0, scale: float = 1.0,
               svg_code_only=False):
        vscale *= scale
        hscale *= scale

        x_color = "#CCFFCC"
        z_color = "#FF8888"
        y_color = "ycolor"

        num_qubits = self.num_qubits
        num_gadgets = self.num_gadgets

        # general width and height of a square
        square_width = int(math.ceil(20 * vscale))
        square_height = int(math.ceil(20 * vscale))

        # width of the text of the phases # TODO round floats (!!)
        text_width = int(math.ceil(50 * vscale))

        bend_degree = int(math.ceil(10))

        # margins between the angle and the legs
        margin_angle_x = int(math.ceil(20 * hscale))
        margin_angle_y = int(math.ceil(20 * hscale))

        # margins between each element
        margin_x = int(math.ceil(10 * hscale))
        margin_y = int(math.ceil(10 * hscale))

        font_size = int(10)

        width = num_gadgets * (
                square_width + margin_x + margin_angle_x + text_width) + margin_x
        height = (num_qubits) * (square_height + margin_y) + (
                square_height + margin_y + margin_angle_y)

        builder = SVGBuilder(width, height)
        builder = builder.add_diagonal_fill(x_color, z_color, y_color)

        prev_x = {qubit: 0 for qubit in range(num_qubits)}

        x = margin_x

        for gadget in self.pauli_gadgets:
            paulis = gadget.paulis
            y = margin_y
            text_coords = (square_width + margin_x + margin_angle_x + x, y)
            text_left_lower_corder = (text_coords[0], text_coords[1] + square_height)
            for qubit in range(num_qubits):
                if qubit == 0:
                    y += square_height + margin_y + margin_angle_y
                else:
                    y += square_height + margin_y
                center_coords = (x + square_width, y)
                if paulis[qubit] == I:
                    continue

                builder.line((prev_x[qubit], y + square_height // 2),
                             (x, y + square_height // 2))
                prev_x[qubit] = x + square_width
                builder.line_bend(text_left_lower_corder, center_coords,
                                  degree=qubit * bend_degree)
                if paulis[qubit] == X:
                    builder.square((x, y), square_width, square_height, x_color)
                elif paulis[qubit] == Y:
                    builder.square((x, y), square_width, square_height, y_color)
                elif paulis[qubit] == Z:
                    builder.square((x, y), square_width, square_height, z_color)

            builder = builder.text_with_square(text_coords, text_width, square_height,
                                               str(gadget.angle))
            x += square_width + margin_x + text_width + margin_angle_x
        y = margin_y
        for qubit in range(num_qubits):
            if qubit == 0:
                y += square_height + margin_y + margin_angle_y
            else:
                y += square_height + margin_y
            builder.line((prev_x[qubit], y + square_height // 2),
                         (width, y + square_height // 2))
        svg_code = repr(builder)

        if svg_code_only:
            return svg_code
        try:
            # pylint: disable = import-outside-toplevel
            from IPython.core.display import SVG  # type: ignore
        except ModuleNotFoundError as e:
            raise ModuleNotFoundError("You must install the 'IPython' library.") from e

        return SVG(svg_code)

    def _repr_svg_(self):
        """
            Magic method for IPython/Jupyter pretty-printing.
            See https://ipython.readthedocs.io/en/stable/api/generated/IPython.display.html
        """
        return self.to_svg(svg_code_only=True)

    def to_latex(self, file_name=None):
        out_str = LATEX_HEADER
        out_str += "\\begin{document}\n"
        out_str += "\\begin{ZX}\n"

        angle_line = "\zxNone{} \t\t&"

        angle_pad_max = max(
            [len(str(gadget.angle.repr_latex)) for gadget in self.pauli_gadgets])
        lines = {q: "\\zxNone{} \\rar \t&" for q in range(self.num_qubits)}
        for gadget in self.pauli_gadgets:
            assert isinstance(gadget, PauliGadget)
            pad_ = ''.join([' ' for _ in range(self.num_qubits + 26)])
            pad_angle = "".join([' ' for _ in range(angle_pad_max -
                                                    len(str(gadget.angle.repr_latex)))])
            angle_line += f" \\zxNone{{}}  {pad_}&" \
                          f" |[pauliPhase]| {gadget.angle.repr_latex} {pad_angle}&" \
                          f" \\zxNone{{}}      &"
            paulis = gadget.paulis
            for q in range(self.num_qubits):
                us = ''.join(['u' for _ in range(q)])

                pad_angle = "".join([' ' for _ in range(angle_pad_max)])
                if paulis[q] != I:
                    pad_ = ''.join([' ' for _ in range(self.num_qubits - q)])
                    lines[q] += f" |[pauli{paulis[q].value}]| " \
                                f"\\ar[ruu{us}, bend right] \\rar {pad_}&" \
                                f" \\zxNone{{}} \\rar {pad_angle} &" \
                                f" \\zxNone{{}} \\rar &"
                else:
                    pad_ = ''.join([' ' for _ in range(self.num_qubits + 22)])
                    lines[q] += f" \\zxNone{{}} \\rar {pad_}& " \
                                f"\\zxNone{{}} \\rar {pad_angle} & " \
                                f"\\zxNone{{}} \\rar &"
        out_str += angle_line + "\\\\ \n"
        out_str += "\\\\ \n"
        for q in range(self.num_qubits):
            out_str += lines[q] + "\\\\ \n"
        out_str += "\\end{ZX} \n"
        out_str += "\\end{document}\n"
        if file_name is not None:
            with open(f"{file_name}.tex", "w") as f:
                f.write(out_str)
        return out_str

    def swap_gadgets(self, col1, col2):
        self.pauli_gadgets[col1], self.pauli_gadgets[col2] = \
            self.pauli_gadgets[col2], self.pauli_gadgets[col1]


def remove_collapsed_pauli_gadegts(remaining_poly):
    return list(
        filter(lambda x: x.angle != 2 * np.pi and x.angle != 0, remaining_poly))


def find_machting_parity_right(idx, remaining_poly):
    gadget = remaining_poly[idx]
    for idx_right, gadget_right in enumerate(remaining_poly[idx + 1:]):
        if all([p_1 == p_2 for p_1, p_2 in zip(gadget.paulis, gadget_right.paulis)]):
            return idx + idx_right + 1
    return None


def is_commuting_region(idx, idx_right, remaining_poly):
    for k in range(idx, idx_right):
        if not remaining_poly[idx].commutes(remaining_poly[k]):
            return False
    return True


def propagate_phase_gadegts(remaining_poly):
    converged = True
    for idx, gadget in enumerate(remaining_poly):
        idx_right = find_machting_parity_right(idx, remaining_poly)
        if idx_right is None:
            continue
        if not is_commuting_region(idx, idx_right, remaining_poly):
            continue

        remaining_poly[idx_right].angle = remaining_poly[idx_right].angle + gadget.angle
        remaining_poly[idx].angle = 0.0
        converged = False
    return converged


def clamp(phase):
    new_phase = phase % 2
    if new_phase > 1:
        return new_phase - 2
    return phase


def simplify_pauli_polynomial(pp: PauliPolynomial):
    remaining_poly = [gadet.copy() for gadet in pp.pauli_gadgets]
    converged = False
    while not converged:
        remaining_poly = remove_collapsed_pauli_gadegts(remaining_poly)
        converged = propagate_phase_gadegts(remaining_poly)

    pp_ = PauliPolynomial(pp.num_qubits)
    for gadget in remaining_poly:
        pp_ >>= gadget
    return pp_
