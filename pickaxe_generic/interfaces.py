"""
Contains interfaces for major datatypes in Pickaxe-Generic.

Classes:


"""

import abc
import collections.abc
import dataclasses
import typing

import rdkit
import rdkit.Chem
import rdkit.Chem.rdChemReactions

T = typing.TypeVar("T")
T_ci = typing.TypeVar("T_ci", contravariant=False)
T_data = typing.TypeVar("T_data", bound="DataUnit")
T_id = typing.TypeVar("T_id", bound="Identifier")
T_int = typing.TypeVar("T_int", bound=int)


MolIndex = typing.NewType("MolIndex", int)
OpIndex = typing.NewType("OpIndex", int)
RxnIndex = typing.NewType("RxnIndex", int)


class Identifier(collections.abc.Hashable, typing.Protocol):
    """
    Orderable, hashable object used as unique identifier.

    This value is ideally immutable using public methods.

    Methods
    -------
    __hash__
    __eq__
    __lt__
    """

    def __hash__(self) -> int:
        """
        Hashes object to integer.

        Returns
        -------
        int
            Integer representing hashed value of object.  Should be
            (effectively) unique.
        """

    def __eq__(self, other: object) -> bool:
        """
        Compare object to others of similar type.  Enables hashtables.

        Arguments
        ---------
        other : object
            Object to be compared.

        Returns
        -------
        bool
            True if object is equivalent to other, False otherwise.
        """

    def __lt__(self, other) -> bool:
        """
        Compare object to others of similar type.  Allows sorting.

        Arguments
        ---------
        other
            Object to be compared.

        Returns
        -------
        bool
            True if object is after self when ordered, False otherwise.
        """


class DataUnit(abc.ABC):
    """
    Basic data storage object.

    Object which provides a unique, hashable identifier, a method of ordering,
    and can serve up a binary form of the object.

    Attributes
    ----------
    blob : bytes
        Binary representation of object.
    uid : Identifier
        Unique identifier of object.
    """

    __slots__ = ()

    @property
    @abc.abstractmethod
    def blob(self) -> bytes:
        """
        Binary representation of object.

        Must be able to initialize object when passed to __setstate__ method of
        any subclass of same type (viz. initialize a MolDatBasicV2, even if
        obtained from a MolDatBasicV1).
        """

    @classmethod
    @abc.abstractmethod
    def from_bytes(
        cls: type[T_ci], data: bytes, engine: "NetworkEngine"
    ) -> T_ci:
        """
        Produce object from bytestring.

        Bytestring should be derived from the .blob property, and should be
        able to initialize any object directly derived from the parent class.
        """

    @property
    @abc.abstractmethod
    def uid(self) -> Identifier:
        """
        Unique identifier of object.

        Must be hashable in order to facilitate lookup tables utilizing hashes.
        """

    @typing.final
    def __getstate__(self) -> bytes:
        return self.blob


class MolDatBase(DataUnit):
    """
    Interface representing molecule data.

    Classes implementing this interface manage information about a single
    molecule, allowing for memory management and lumped molecule frameworks.

    Attributes
    ----------
    WORK IN PROGRESS
    """

    __slots__ = ()


class MolDatRDKit(MolDatBase):
    """
    Interface representing an RDKit molecule data object.

    Classes implementing this interface manage information about a single
    rdkit-compatible molecule.  Defines the constructor for this type of
    MolDat, and thus must be subclassed only by implementations with @typing.final.
    Default behavior for __lt__ is sorting by UID.

    Parameters
    ----------
    molecule : RDKitMol | str
        Sufficient information to generate molecule in the form of an RDKitMol
        or a SMILES string.
    sanitize : bool (default: True)
        Should be True when using input from non-sanitized sources.
    neutralize : bool (default: False)
        Should be True if you want hydrogens to be added/subtracted to
        neutralize a molecule and input is a SMILES string or non-neutralized
        molecule.

    Attributes
    ----------
    blob : bytes
        Binary representation of molecule.
    inchikey : str
        InChIKey of object.
    rdkitmol : RDKitMol
        RDKit molecule object.
    smiles : str
        SMILES string of object.
    uid : Identifier
        Unique identifier of object.
    """

    __slots__ = ()

    @abc.abstractmethod
    def __init__(
        self,
        molecule: rdkit.Chem.rdchem.Mol | str,
        sanitize: bool = True,
        neutralize: bool = False,
    ) -> None:
        pass

    @classmethod
    def from_bytes(
        cls,
        data: bytes,
        engine: "NetworkEngine",
    ) -> "MolDatRDKit":
        return engine.Mol(data)

    def __lt__(self, other: object) -> bool:
        if isinstance(other, MolDatRDKit):
            return self.uid < other.uid
        else:
            raise TypeError(
                f"Invalid comparison between objects of type {type(self)} and"
                f"type {type(other)}"
            )

    def __setstate__(self, in_val: bytes) -> None:
        rdkitmol: typing.Optional[rdkit.Chem.rdchem.Mol] = rdkit.Chem.Mol(
            in_val
        )
        if rdkitmol is None:
            raise ValueError("Invalid molecule bytestring")
        self._buildfrommol(rdkitmol)

    @abc.abstractmethod
    def _buildfrommol(self, in_val: rdkit.Chem.rdchem.Mol) -> None:
        pass

    @property
    @abc.abstractmethod
    def blob(self) -> bytes:
        """
        RDKit-generated bytestring.

        Enables quick regeneration of RDKitMol object.
        """

    @property
    @abc.abstractmethod
    def inchikey(self) -> str:
        """Return InChIKey hash of molecule."""

    @property
    @abc.abstractmethod
    def rdkitmol(self) -> rdkit.Chem.rdchem.Mol:
        """Return RDKit molecule object containing basic properties."""

    @property
    @abc.abstractmethod
    def smiles(self) -> str:
        """Return canonical SMILES string of molecule object."""

    def _processinput(
        self,
        molecule: rdkit.Chem.rdchem.Mol | str | bytes,
        sanitize: bool = True,
        neutralize: bool = False,
    ) -> rdkit.Chem.rdchem.Mol:
        if isinstance(molecule, bytes):
            rdkitmol = rdkit.Chem.Mol(molecule)
            # if sanitize:
            #    SanitizeMol(rdkitmol)
            #    AssignStereochemistry(rdkitmol, True, True, True)
            # if neutralize:
            #    raise NotImplementedError("No neutralize function coded")
        elif isinstance(molecule, rdkit.Chem.rdchem.Mol):
            rdkitmol = molecule
            # print(MolToSmiles(rdkitmol))
            if sanitize:
                rdkit.Chem.rdmolops.SanitizeMol(rdkitmol)
                rdkit.Chem.rdmolops.AssignStereochemistry(
                    rdkitmol, True, True, True
                )
            if neutralize:
                raise NotImplementedError("No neutralize function coded")
        elif isinstance(molecule, str):
            if sanitize:
                rdkitmol = rdkit.Chem.MolFromSmiles(molecule, sanitize=True)
            else:
                rdkitmol = rdkit.Chem.MolFromSmiles(molecule, sanitize=False)
            if neutralize:
                raise NotImplementedError("No neutralize function coded")
        else:
            raise TypeError("Invalid molecule type")
        if rdkitmol is None:
            raise TypeError("Invalid molecule information")
        return rdkitmol


class OpDatBase(DataUnit):
    """
    Interface representing operator data.

    Classes implementing this interface manage information about a single
    operator which acts on MolDatBase and can generate RxnDatBase objects.

    Methods
    -------
    compat
    __call__
    __len__
    """

    __slots__ = ()

    @abc.abstractmethod
    def compat(self, mol: MolDatBase, arg: int) -> bool:
        """
        Determine compatibility of MolDat object with operator argument.

        Parameters
        ----------
        mol : MolDatBase
            MolDat object which is to be compared.
        arg : int
            Index of argument which is to be compared.

        Returns
        -------
        bool
            True if MolDat may be passed as argument arg to operator.
        """

    @abc.abstractmethod
    def __call__(
        self, reactants: collections.abc.Sequence[MolDatBase]
    ) -> collections.abc.Iterable[collections.abc.Iterable[MolDatBase]]:
        """
        React a sequence of MolDat objects using internal operator.

        Return a sequence of RxnDat objects which contain metadata about
        potential results.

        Parameters
        ----------
        reactants : Sequence[MolDatBase]
            Reactants which match the arguments in the operator.

        Returns
        -------
        Iterable[RxnDatBase]
            Iterable of reactions which are produced by applying the operator.
        """

    @abc.abstractmethod
    def __len__(self) -> int:
        """Return number of arguments in operator."""


class OpDatRDKit(OpDatBase):
    """
    Interface representing an RDKit SMARTS operator.

    Agents are treated as arguments following reagent arguments.  Classes
    implementing this interface manage information about a single
    rdkit-compatible SMARTS operator.

    Attributes
    ----------
    smarts : str
        SMARTS string representing operator.
    rdkitrxn : RDKitRxn
        RDKit reaction object.
    """

    __slots__ = ()

    @abc.abstractmethod
    def __init__(self, operator: rdkit.Chem.rdchem.Mol | str | bytes):
        pass

    @typing.final
    @classmethod
    def from_bytes(
        cls,
        data: bytes,
        engine: "NetworkEngine",
    ) -> "OpDatRDKit":
        return engine.Op(data)

    @property
    @abc.abstractmethod
    def smarts(self) -> str:
        """Return SMARTS string encoding operator information."""

    @property
    @abc.abstractmethod
    def rdkitrxn(self) -> rdkit.Chem.rdChemReactions.ChemicalReaction:
        """Return RDKit reaction object."""


class RxnDatBase(DataUnit):
    """
    Interface representing reaction data.

    Class implementing this interface manage information about a single reaction
    between several molecules to produce several molecules, with an associated
    operator.

    Attributes
    ----------
    operator : Identifier
        Operator object ID.
    products : Iterable[Identifier]
        Products of reaction IDs.
    reactants : Iterable[Identifier]
        Reactants involved in reaction IDs.
    """

    __slots__ = ()

    @abc.abstractmethod
    def __init__(
        self,
        operator: typing.Optional[Identifier] = None,
        reactants: typing.Optional[collections.abc.Iterable[Identifier]] = None,
        products: typing.Optional[collections.abc.Iterable[Identifier]] = None,
        reaction: typing.Optional[bytes] = None,
    ) -> None:
        pass

    @typing.final
    @classmethod
    def from_bytes(
        cls,
        data: bytes,
        engine: "NetworkEngine",
    ) -> "RxnDatBase":
        return engine.Rxn(data)

    @property
    @abc.abstractmethod
    def operator(self) -> Identifier:
        """Return ID of operator involved in reaction."""

    @property
    @abc.abstractmethod
    def products(self) -> collections.abc.Iterable[Identifier]:
        """Return IDs of products involved in reaction."""

    @property
    @abc.abstractmethod
    def reactants(self) -> collections.abc.Iterable[Identifier]:
        """Return IDs of reactants involved in reaction."""


class ObjectLibrary(abc.ABC, typing.Generic[T_data]):
    """
    Interface representing library of data.

    Classes implementing this interface manage multiple instances of a hashable
    object, and may have responsibility for synchronization with external
    databases which may also manage this information (be volatile).  Contained
    objects must have a "uid" attribute which contains a hashable unique id.

    Current implementations assume that this library will never shrink or remove
    entries.
    """

    __slots__ = ()

    @abc.abstractmethod
    def add(
        self, obj: typing.Union[collections.abc.Iterable[T_data], T_data]
    ) -> None:
        """
        Add an object or multiple objects to the library.

        This function does not add the new item if it has the same UID as an
        item already in the library.

        Parameters
        ----------
        obj : Union[Iterable[DataUnit], DataUnit]
            Object(s) to be added.
        """

    @abc.abstractmethod
    def ids(self) -> collections.abc.Iterable[Identifier]:
        """
        Return a set of keys used in the library.

        Returns
        -------
        Iterable[Identifier]
            Ids of objects in the library.
        """

    @abc.abstractmethod
    def __contains__(self, item: T_data) -> bool:
        """
        Check if ObjectLibrary contains an object where object.uid == item.uid.

        Parameters
        ----------
        item : DataUnit
            Item to be checked against internal object list.

        Returns
        -------
        bool
            True if ObjectLibrary contains object with same UID.
        """

    @abc.abstractmethod
    def __getitem__(self, item: Identifier) -> T_data:
        """
        Return object where object.uid == item returns True.

        Parameters
        ----------
        item : Identifier
            Item to be checked against internal object list.

        Returns
        -------
        DataUnit
            Object where uid attribute is equal to item.
        """

    @abc.abstractmethod
    def __iter__(self) -> collections.abc.Iterator[T_data]:
        """
        Return an iterator over the objects contained in the ObjectLibrary.

        Returns
        -------
        Iterator[T_data]
            Iterator over objects contained in the ObjectLibrary.
        """

    @abc.abstractmethod
    def __len__(self) -> int:
        """
        Return the number of items contained in the ObjectLibrary.

        Returns
        -------
        int
            Number of items in ObjectLibrary.
        """


class ExpansionStrategy(abc.ABC):
    """
    Interface representing a network expansion strategy.

    Classes implementing this interface use information from a molecule and
    operator library to generate new reactions, which are then output to a
    reaction library.
    """

    __slots__ = ()

    @abc.abstractmethod
    def __init__(
        self,
        mol_lib: ObjectLibrary[MolDatBase],
        op_lib: ObjectLibrary[OpDatBase],
        rxn_lib: ObjectLibrary[RxnDatBase],
    ) -> None:
        pass

    @abc.abstractmethod
    def expand(
        self,
        max_rxns: typing.Optional[int] = None,
        max_mols: typing.Optional[int] = None,
        num_gens: typing.Optional[int] = None,
        custom_filter: typing.Optional[
            collections.abc.Callable[
                [
                    OpDatBase,
                    collections.abc.Sequence[MolDatBase],
                    collections.abc.Sequence[MolDatBase],
                ],
                bool,
            ]
        ] = None,
        custom_uid_prefilter: typing.Optional[
            collections.abc.Callable[
                [Identifier, collections.abc.Sequence[Identifier]], bool
            ]
        ] = None,
    ) -> None:
        """
        Expand molecule library.

        Parameters
        ----------
        max_rxns : Optional[int] (default: None)
            Limit of new reactions to add.  If None, no limit.
        max_mols : Optional[int] (default: None)
            Limit of new molecules to add.  If None, no limit.
        num_gens : Optional[int] (default: None)
            Maximum generations of reactions to enumerate.  If None, no limit.
        custom_filter: Optional[Callable[[OpDatBase, Sequence[MolDatBase],
                       Sequence[MolDatBase]], bool]] (default: None)
            Filter which selects which reactions to retain.
        custom_uid_prefilter: Optional[Callable[[Identifier,
                              Sequence[Identifier]], bool]]
            Filter which selects which operator UID and reactant UIDs to retain.
        """

    @abc.abstractmethod
    def refresh(self) -> None:
        """
        Refresh active molecules and operators from attached libraries.
        """


class ReactionFilter(abc.ABC):
    @abc.abstractmethod
    def __call__(
        self,
        operator: OpDatBase,
        reactants: collections.abc.Sequence[MolDatBase],
        products: collections.abc.Sequence[MolDatBase],
    ) -> bool:
        pass


class UIDPreFilter(abc.ABC):
    @abc.abstractmethod
    def __call__(
        self,
        operator: Identifier,
        reactants: collections.abc.Sequence[Identifier],
    ) -> bool:
        pass


@dataclasses.dataclass(frozen=True)
class MetaKeyPacket:
    operator_keys: frozenset = frozenset()
    molecule_keys: frozenset = frozenset()
    live_operator: bool = False
    live_molecule: bool = False

    def __add__(self, other: "MetaKeyPacket") -> "MetaKeyPacket":
        return MetaKeyPacket(
            self.operator_keys.union(other.operator_keys),
            self.molecule_keys.union(other.molecule_keys),
            self.live_operator or other.live_operator,
            self.live_molecule or other.live_molecule,
        )


class MolFilter(abc.ABC):
    __slots__ = ()

    @abc.abstractmethod
    def __call__(
        self,
        mol: MolDatBase,
        meta: typing.Optional[
            collections.abc.Mapping[collections.abc.Hashable, typing.Any]
        ] = None,
    ) -> bool:
        ...

    @property
    def meta_required(self) -> MetaKeyPacket:
        return MetaKeyPacket()

    @typing.final
    def __and__(self, other: "MolFilter") -> "MolFilter":
        return MolFilterAnd(self, other)

    @typing.final
    def __invert__(self) -> "MolFilter":
        return MolFilterInv(self)

    @typing.final
    def __or__(self, other: "MolFilter") -> "MolFilter":
        return MolFilterOr(self, other)

    @typing.final
    def __xor__(self, other: "MolFilter") -> "MolFilter":
        return MolFilterXor(self, other)


@dataclasses.dataclass(frozen=True)
class MolFilterAnd(MolFilter):
    __slots__ = ("_filter1", "_filter2")

    _filter1: MolFilter
    _filter2: MolFilter

    def __call__(
        self,
        mol: MolDatBase,
        meta: typing.Optional[
            collections.abc.Mapping[collections.abc.Hashable, typing.Any]
        ] = None,
    ) -> bool:
        return self._filter1(mol, meta) and self._filter2(mol, meta)

    @property
    def meta_required(self) -> MetaKeyPacket:
        return self._filter1.meta_required + self._filter2.meta_required


@dataclasses.dataclass(frozen=True)
class MolFilterInv(MolFilter):
    __slots__ = ("_filter",)
    _filter: MolFilter

    def __call__(
        self,
        mol: MolDatBase,
        meta: typing.Optional[
            collections.abc.Mapping[collections.abc.Hashable, typing.Any]
        ] = None,
    ) -> bool:
        return not self._filter(mol, meta)

    @property
    def meta_required(self) -> MetaKeyPacket:
        return self._filter.meta_required


@dataclasses.dataclass(frozen=True)
class MolFilterOr(MolFilter):
    __slots__ = ("_filter1", "_filter2")
    _filter1: MolFilter
    _filter2: MolFilter

    def __call__(
        self,
        mol: MolDatBase,
        meta: typing.Optional[
            collections.abc.Mapping[collections.abc.Hashable, typing.Any]
        ] = None,
    ) -> bool:
        return self._filter1(mol, meta) or self._filter2(mol, meta)

    @property
    def meta_required(self) -> MetaKeyPacket:
        return self._filter1.meta_required + self._filter2.meta_required


@dataclasses.dataclass(frozen=True)
class MolFilterXor(MolFilter):
    __slots__ = ("_filter1", "_filter2")
    _filter1: MolFilter
    _filter2: MolFilter

    def __call__(
        self,
        mol: MolDatBase,
        meta: typing.Optional[
            collections.abc.Mapping[collections.abc.Hashable, typing.Any]
        ] = None,
    ) -> bool:
        return self._filter1(mol, meta) != self._filter2(mol, meta)

    @property
    def meta_required(self) -> MetaKeyPacket:
        return self._filter1.meta_required + self._filter2.meta_required


@dataclasses.dataclass(frozen=True)
class DataPacket(typing.Generic[T_data]):
    __slots__ = ("i", "item", "meta")
    i: int
    item: typing.Optional[T_data]
    meta: typing.Optional[collections.abc.Mapping]


@dataclasses.dataclass(frozen=True)
class DataPacketE(DataPacket, typing.Generic[T_data]):
    __slots__ = ("item",)
    item: T_data


@dataclasses.dataclass(frozen=True, order=True)
class Reaction:
    __slots__ = ("operator", "reactants", "products")
    operator: OpIndex
    reactants: tuple[MolIndex, ...]
    products: tuple[MolIndex, ...]


@dataclasses.dataclass(frozen=True, order=True)
class ReactionExplicit:
    __slots__ = (
        "operator",
        "reactants",
        "products",
        "reaction_meta",
    )
    operator: DataPacketE[OpDatBase]
    reactants: tuple[DataPacketE[MolDatBase], ...]
    products: tuple[DataPacketE[MolDatBase], ...]
    reaction_meta: typing.Optional[collections.abc.Mapping]

    @property
    def uid(
        self,
    ) -> tuple[Identifier, tuple[Identifier, ...], tuple[Identifier, ...]]:
        return (
            self.operator.item.uid,
            tuple(mol.item.uid for mol in self.reactants),
            tuple(mol.item.uid for mol in self.products),
        )


@dataclasses.dataclass(frozen=True)
class Recipe:
    __slots__ = ("operator", "reactants")
    operator: OpIndex
    reactants: tuple[MolIndex, ...]

    def __eq__(self, other: object) -> bool:
        if (
            isinstance(other, Recipe)
            and self.operator == other.operator
            and self.reactants == other.reactants
        ):
            return True
        return False

    def __lt__(self, other: "Recipe") -> bool:
        self_order = sorted(self.reactants, reverse=True)
        other_order = sorted(other.reactants, reverse=True)
        for val_self, val_other in zip(self_order, other_order):
            if val_self < val_other:
                return False
            elif val_other < val_self:
                return True
        if len(self.reactants) < len(other.reactants):
            return False
        elif len(other.reactants) < len(self.reactants):
            return True
        if self.operator < other.operator:
            return False
        elif other.operator < self.operator:
            return True
        return other.reactants < self.reactants


@dataclasses.dataclass(frozen=True)
class RecipeExplicit:
    __slots__ = ("operator", "reactants", "operator_meta", "reactants_meta")
    operator: DataPacket[OpDatBase]
    reactants: tuple[DataPacket[MolDatBase], ...]


class RecipeFilter(abc.ABC):
    __slots__ = ()

    @abc.abstractmethod
    def __call__(self, recipe: RecipeExplicit) -> bool:
        ...

    @property
    def meta_required(self) -> MetaKeyPacket:
        return MetaKeyPacket()

    @typing.final
    def __and__(self, other: "RecipeFilter") -> "RecipeFilter":
        return RecipeFilterAnd(self, other)

    @typing.final
    def __invert__(self) -> "RecipeFilter":
        return RecipeFilterInv(self)

    @typing.final
    def __or__(self, other: "RecipeFilter") -> "RecipeFilter":
        return RecipeFilterOr(self, other)

    @typing.final
    def __xor__(self, other: "RecipeFilter") -> "RecipeFilter":
        return RecipeFilterXor(self, other)


@dataclasses.dataclass(frozen=True)
class RecipeFilterAnd(RecipeFilter):
    __slots__ = ("_filter1", "_filter2")

    _filter1: RecipeFilter
    _filter2: RecipeFilter

    def __call__(self, recipe: RecipeExplicit) -> bool:
        return self._filter1(recipe) and self._filter2(recipe)

    @property
    def meta_required(self) -> MetaKeyPacket:
        return self._filter1.meta_required + self._filter2.meta_required


@dataclasses.dataclass(frozen=True)
class RecipeFilterInv(RecipeFilter):
    __slots__ = ("_filter",)
    _filter: RecipeFilter

    def __call__(self, recipe: RecipeExplicit) -> bool:
        return not self._filter(recipe)

    @property
    def meta_required(self) -> MetaKeyPacket:
        return self._filter.meta_required


@dataclasses.dataclass(frozen=True)
class RecipeFilterOr(RecipeFilter):
    __slots__ = ("_filter1", "_filter2")
    _filter1: RecipeFilter
    _filter2: RecipeFilter

    def __call__(self, recipe: RecipeExplicit) -> bool:
        return self._filter1(recipe) or self._filter2(recipe)

    @property
    def meta_required(self) -> MetaKeyPacket:
        return self._filter1.meta_required + self._filter2.meta_required


@dataclasses.dataclass(frozen=True)
class RecipeFilterXor(RecipeFilter):
    __slots__ = ("_filter1", "_filter2")
    _filter1: RecipeFilter
    _filter2: RecipeFilter

    def __call__(self, recipe: RecipeExplicit) -> bool:
        return self._filter1(recipe) != self._filter2(recipe)

    @property
    def meta_required(self) -> MetaKeyPacket:
        return self._filter1.meta_required + self._filter2.meta_required


class NetworkEngine(abc.ABC):
    """
    Interface representing an object which serves up other objects based on
    configuration parameters.

    Classes implementing this interface determine which type of network objects
    are constructed based on configuration options.
    """

    @property
    @abc.abstractmethod
    def speed(self) -> int:
        """
        Defined speed of engine configuration.
        """

    @abc.abstractmethod
    def Mol(
        self,
        molecule: typing.Union[rdkit.Chem.rdchem.Mol, str, bytes],
        sanitize: bool = True,
        neutralize: bool = False,
    ) -> MolDatRDKit:
        """
        Initializes a MolDatRDKit object of relevant type.
        """

    @abc.abstractmethod
    def Op(
        self,
        operator: typing.Union[
            rdkit.Chem.rdChemReactions.ChemicalReaction, str, bytes
        ],
        kekulize: bool = False,
    ) -> OpDatRDKit:
        """
        Initializes an OpDatRDKit object of relevant type.
        """

    @abc.abstractmethod
    def Rxn(
        self,
        operator: typing.Optional[Identifier] = None,
        reactants: typing.Optional[collections.abc.Iterable[Identifier]] = None,
        products: typing.Optional[collections.abc.Iterable[Identifier]] = None,
        reaction: typing.Optional[bytes] = None,
    ) -> RxnDatBase:
        """
        Initializes a RxnDatBase object of relevant type.
        """

    @abc.abstractmethod
    def Libs(
        self,
    ) -> tuple[
        ObjectLibrary[MolDatBase],
        ObjectLibrary[OpDatBase],
        ObjectLibrary[RxnDatBase],
    ]:
        """
        Initializes the three basic ObjectLibraries necessary to run a Strategy.
        """

    @abc.abstractmethod
    def CartesianStrategy(
        self,
        mol_lib: ObjectLibrary[MolDatBase],
        op_lib: ObjectLibrary[OpDatBase],
        rxn_lib: ObjectLibrary[RxnDatBase],
    ):
        """
        Initializes a CartesianStrategy of relevant type.
        """


class ValueQueryData(typing.Protocol[T_data, T_int]):
    @abc.abstractmethod
    def __contains__(self, item: typing.Union[Identifier, T_data]) -> bool:
        ...

    @typing.overload
    @abc.abstractmethod
    def __getitem__(self, item: slice) -> collections.abc.Sequence[T_data]:
        ...

    @typing.overload
    @abc.abstractmethod
    def __getitem__(self, item: typing.Union[T_int, Identifier]) -> T_data:
        ...

    @abc.abstractmethod
    def __getitem__(self, item: typing.Union[slice, T_int, Identifier]):
        ...

    @abc.abstractmethod
    def i(self, uid: Identifier) -> T_int:
        ...

    @abc.abstractmethod
    def keys(self) -> collections.abc.Collection[Identifier]:
        ...

    @abc.abstractmethod
    def uid(self, i: T_int) -> Identifier:
        ...

    @abc.abstractmethod
    def __len__(self) -> int:
        ...

    @abc.abstractmethod
    def __iter__(self) -> collections.abc.Iterator[T_data]:
        ...


class ValueQueryAssoc(typing.Protocol[T_id, T_int]):
    @typing.overload
    @abc.abstractmethod
    def __getitem__(self, item: slice) -> collections.abc.Sequence[T_id]:
        ...

    @typing.overload
    @abc.abstractmethod
    def __getitem__(self, item: T_int) -> T_id:
        ...

    @abc.abstractmethod
    def __getitem__(self, item: typing.Union[slice, T_int]):
        ...

    @abc.abstractmethod
    def i(self, item: T_id) -> T_int:
        ...

    @abc.abstractmethod
    def __len__(self) -> int:
        ...

    @abc.abstractmethod
    def __iter__(self) -> collections.abc.Iterator[T_id]:
        ...


class ChemNetwork(abc.ABC):
    __slots__ = ()

    @abc.abstractmethod
    def __init__(self) -> None:
        ...

    @property
    @abc.abstractmethod
    def mols(self) -> ValueQueryData[MolDatBase, MolIndex]:
        ...

    @property
    @abc.abstractmethod
    def ops(self) -> ValueQueryData[OpDatBase, OpIndex]:
        ...

    @property
    @abc.abstractmethod
    def rxns(self) -> ValueQueryAssoc[Reaction, RxnIndex]:
        ...

    @abc.abstractmethod
    def mol_meta(
        self, index: MolIndex, key: collections.abc.Hashable, value=None
    ):
        ...

    @abc.abstractmethod
    def op_meta(
        self, index: OpIndex, key: collections.abc.Hashable, value=None
    ):
        ...

    @abc.abstractmethod
    def rxn_meta(
        self, index: RxnIndex, key: collections.abc.Hashable, value=None
    ):
        ...

    @abc.abstractmethod
    def mol_metas(
        self,
        indices: typing.Optional[collections.abc.Sequence[MolIndex]] = None,
        keys: typing.Optional[
            collections.abc.Collection[collections.abc.Hashable]
        ] = None,
    ) -> collections.abc.Sequence[
        collections.abc.Mapping[collections.abc.Hashable, typing.Any]
    ]:
        ...

    @abc.abstractmethod
    def op_metas(
        self,
        indices: typing.Optional[collections.abc.Sequence[OpIndex]] = None,
        keys: typing.Optional[
            collections.abc.Collection[collections.abc.Hashable]
        ] = None,
    ) -> collections.abc.Sequence[
        collections.abc.Mapping[collections.abc.Hashable, typing.Any]
    ]:
        ...

    @abc.abstractmethod
    def rxn_metas(
        self,
        indices: typing.Optional[collections.abc.Sequence[RxnIndex]] = None,
        keys: typing.Optional[
            collections.abc.Collection[collections.abc.Hashable]
        ] = None,
    ) -> collections.abc.Sequence[
        collections.abc.Mapping[collections.abc.Hashable, typing.Any]
    ]:
        ...

    @abc.abstractmethod
    def compat_table(
        self, index: int
    ) -> collections.abc.Sequence[collections.abc.Sequence[MolIndex]]:
        ...

    @abc.abstractmethod
    def consumers(
        self, mol: typing.Union[int, MolDatBase, Identifier]
    ) -> collections.abc.Collection[RxnIndex]:
        ...

    @abc.abstractmethod
    def producers(
        self, mol: typing.Union[int, MolDatBase, Identifier]
    ) -> collections.abc.Collection[RxnIndex]:
        ...

    @abc.abstractmethod
    def add_mol(
        self,
        mol: MolDatBase,
        meta: typing.Optional[collections.abc.Mapping] = None,
        reactive: bool = True,
        custom_compat: typing.Optional[
            collections.abc.Collection[tuple[OpIndex, int]]
        ] = None,
    ) -> MolIndex:
        ...

    @abc.abstractmethod
    def add_op(
        self,
        mol: OpDatBase,
        meta: typing.Optional[collections.abc.Mapping] = None,
    ) -> OpIndex:
        ...

    @abc.abstractmethod
    def add_rxn(
        self,
        rxn: typing.Optional[Reaction] = None,
        op: typing.Optional[OpIndex] = None,
        reactants: typing.Optional[collections.abc.Sequence[MolIndex]] = None,
        products: typing.Optional[collections.abc.Sequence[MolIndex]] = None,
        meta: typing.Optional[collections.abc.Mapping] = None,
    ) -> RxnIndex:
        ...


class RankValue(typing.Protocol):
    @abc.abstractmethod
    def __lt__(self, other: "RankValue") -> bool:
        ...


class RecipeRanker(typing.Protocol):
    @abc.abstractmethod
    def __call__(
        self,
        recipe: RecipeExplicit,
        min_rank: typing.Optional[RankValue] = None,
    ) -> typing.Optional[RankValue]:
        ...

    @property
    def meta_required(self) -> MetaKeyPacket:
        return MetaKeyPacket()


class PriorityQueueStrategy(abc.ABC):
    __slots__ = ()

    @abc.abstractmethod
    def __init__(
        self,
        network: ChemNetwork,
        num_procs: typing.Optional[int] = None,
        blacklist_key: typing.Optional[str] = None,
    ) -> None:
        ...

    @abc.abstractmethod
    def expand(
        self,
        max_recipes: typing.Optional[int] = None,
        heap_size: int = 1,
        batch_size: typing.Optional[int] = None,
        beam_size: typing.Optional[int] = 1,
        # mol_filter_local: Optional[MolFilter] = None,
        # mol_filter: Optional[MolFilter] = None,
        recipe_filter: typing.Optional[RecipeFilter] = None,
        recipe_ranker: typing.Optional[RecipeRanker] = None,
        # mc_local: Optional[MetaDataCalculatorLocal] = None,
        # mc_update: Optional[MetaDataUpdate] = DefaultMetaDataUpdate(),
    ) -> None:
        ...


class RxnTracker(abc.ABC):
    """
    Interface representing an object which analyzes rxn network connections.

    Classes implementing this interface are able to create retrosynthetic trees
    based on a precalculated reaction network tree.

    Parameters
    ----------
    target : Identifier
        Unique ID of target molecule.
    reagent_table : Sequence[Identifier] (default: tuple())
        Contains unique IDs of reagents which do not need to be synthesized.
    fail_on_unknown_reagent : bool (default: False)
        If True, do not return paths which require reagents not in
        reagent_table.
    """

    @abc.abstractmethod
    def getParentChains(
        self,
        target: Identifier,
        reagent_table: collections.abc.Sequence[Identifier] = tuple(),
        fail_on_unknown_reagent: bool = False,
    ) -> collections.abc.Iterable[
        collections.abc.Iterable[collections.abc.Iterable[Identifier]]
    ]:
        """
        Gets parent chains for a particular target molecule.

        Parameters
        ----------
        target : Identifier
            Unique id of target molecule.
        reagent_table : Sequence[Identifier]
            Sequence of reagents which are considered "basic" and which the tree
            search will consider leaf nodes.
        fail_on_unknown_reagent : bool
            If tree requires unlisted reagents, do not return.
        """


class MetaDataCalculatorLocal(typing.Protocol):
    @abc.abstractmethod
    def __call__(
        self, unit: typing.Union[ReactionExplicit, RecipeExplicit]
    ) -> None:
        ...

    @property
    @abc.abstractmethod
    def meta_required(self) -> MetaKeyPacket:
        ...


class MetaDataUpdate(typing.Protocol):
    @abc.abstractmethod
    def __call__(
        self, unit: ReactionExplicit, network: ChemNetwork
    ) -> collections.abc.Generator[
        tuple[
            typing.Optional[tuple[MolIndex, collections.abc.Hashable]],
            typing.Optional[tuple[OpIndex, collections.abc.Hashable]],
        ],
        None,
        None,
    ]:
        ...
