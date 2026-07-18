from .academic_style import find_missing_citations
from .persian_fix import analyze_persian_latex
from .sdk import (
    PLUGIN_API_VERSION,
    MathFixerPlugin,
    PluginContext,
    PluginDiagnostic,
    PluginManager,
)
from .template_adapter import TemplateAdapter, load_template_adapter
from .thesis import THESIS_PROFILES, ThesisProfile

__all__ = [
    "THESIS_PROFILES",
    "PLUGIN_API_VERSION",
    "MathFixerPlugin",
    "PluginContext",
    "PluginDiagnostic",
    "PluginManager",
    "TemplateAdapter",
    "ThesisProfile",
    "analyze_persian_latex",
    "find_missing_citations",
    "load_template_adapter",
]
