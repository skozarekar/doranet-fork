from abc import ABC, abstractmethod
from typing import Iterable, Sequence

from rdkit.Chem.rdqueries import AtomNumEqualsQueryAtom

from pickaxe_generic.datatypes import MolDatBase, MolDatRDKit, OpDatBase


class ReactionFilter(ABC):
    @abstractmethod
    def __call__(
        self,
        operator: OpDatBase,
        reactants: Sequence[MolDatBase],
        products: Sequence[MolDatBase],
    ) -> bool:
        pass


class AlwaysTrueFilter(ReactionFilter):
    def __call__(operator, reactants, products):
        return True


class ChainFilter(ReactionFilter):
    def __init__(self, filters: Iterable[ReactionFilter]):
        self._filters = filters

    def __call__(self, operator, reactants, products):
        return all(
            (filter(operator, reactants, products) for filter in self._filters)
        )


class LessThanNElementTypeFilter(ReactionFilter):
    def __init__(self, n: int, proton_number: int):
        self._n = n
        self._q = AtomNumEqualsQueryAtom(proton_number)

    def __call__(self, operator, reactants, products):
        for mol in products:
            if isinstance(mol, MolDatRDKit):
                if len(mol.rdkitmol.GetAtomsMatchingQuery(self._q)) >= self._n:
                    return False
        return True
