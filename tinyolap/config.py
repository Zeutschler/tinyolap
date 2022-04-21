from typing import Final


class Config:
    """Provides access to configuration and meta data of the TinyOlap library."""
    VERSION: Final = "0.8.16"
    LOWEST_COMPATIBLE_VERSION: Final = "0.8.9"
    BUILTIN_VALUE_TYPES: Final = {'str': str, 'int': int, "float": float, 'bool': bool, 'complex': complex,
                               'list': list, 'tuple': tuple, 'range': range, 'dict': dict, 'set': set,
                               'bytes': bytes, 'bytearray': bytearray,}

    class ContentTypes:
        ATTRIBUTES: Final = "TinyOlap.Attributes"
        ATTRIBUTE: Final = "TinyOlap.Attribute"
        DIMENSIONS: Final = "TinyOlap.Dimensions"
        DIMENSION: Final = "TinyOlap.Dimension"
        SUBSETS: Final = "TinyOlap.Subsets"
        SUBSET: Final = "TinyOlap.Subset"
        RULES: Final = "TinyOlap.Rules"
        RULE: Final = "TinyOlap.Rule"
