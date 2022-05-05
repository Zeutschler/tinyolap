from typing import Final


class Config:
    """Provides access to configuration and metadata of the TinyOlap engine."""
    VERSION: Final = "0.8.16"
    LOWEST_COMPATIBLE_VERSION: Final = "0.8.9"
    BUILTIN_VALUE_TYPES: Final = {'str': str, 'int': int, "float": float, 'bool': bool, 'complex': complex,
                               'list': list, 'tuple': tuple, 'range': range, 'dict': dict, 'set': set,
                               'bytes': bytes, 'bytearray': bytearray,}

    class ContentTypes:
        ATTRIBUTE: Final = "TinyOlap.Attribute"
        ATTRIBUTES: Final = "TinyOlap.Attributes"
        DIMENSION: Final = "TinyOlap.Dimension"
        DIMENSIONS: Final = "TinyOlap.Dimensions"
        SUBSET: Final = "TinyOlap.Subset"
        SUBSETS: Final = "TinyOlap.Subsets"
        RULE: Final = "TinyOlap.Rule"
        RULES: Final = "TinyOlap.Rules"
        VIEW: Final = "TinyOlap.View"
        VIEW_DEFINITION: Final = "TinyOlap.ViewDefinition"
        VIEWS: Final = "TinyOlap.Views"
