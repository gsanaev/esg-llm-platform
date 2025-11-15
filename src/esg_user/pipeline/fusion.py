from __future__ import annotations

import logging
from typing import Dict, List, Mapping, Any

from esg_user.types import ExtractorResultDict

logger = logging.getLogger(__name__)


def _pick_best(
    regex: ExtractorResultDict,
    nlp: ExtractorResultDict,
    table: ExtractorResultDict,
    llm: ExtractorResultDict,
) -> ExtractorResultDict:
    """
    Choose the best candidate based on confidence (and optionally source).
    """

    candidates: list[tuple[str, float, ExtractorResultDict]] = []

    def add(name: str, res: Mapping[str, Any]) -> None:
        conf = float(res.get("confidence", 0.0))
        if conf > 0:
            candidates.append((name, conf, ExtractorResultDict(
                value=res.get("value"),
                unit=res.get("unit"),
                confidence=conf,
                source=list(res.get("source", [])),
                raw_value=res.get("raw_value"),
                raw_unit=res.get("raw_unit"),
            )))

    add("regex", regex)
    add("nlp", nlp)
    add("table", table)
    add("llm", llm)

    if not candidates:
        return ExtractorResultDict(
            value=None,
            unit=None,
            confidence=0.0,
            source=[],
            raw_value=None,
            raw_unit=None,
        )

    # Sort by confidence desc, keep first
    candidates.sort(key=lambda t: t[1], reverse=True)
    _, _, best_res = candidates[0]

    return best_res


def fuse_all(
    regex_res: Mapping[str, ExtractorResultDict],
    nlp_res: Mapping[str, ExtractorResultDict],
    table_res: Mapping[str, ExtractorResultDict],
    llm_res: Mapping[str, ExtractorResultDict],
    kpi_codes: List[str],
) -> Dict[str, ExtractorResultDict]:
    """
    Fuse all extractor outputs per KPI into final ExtractorResultDict values.
    """

    final: Dict[str, ExtractorResultDict] = {}

    for code in kpi_codes:
        final[code] = _pick_best(
            regex_res.get(code, ExtractorResultDict()),
            nlp_res.get(code, ExtractorResultDict()),
            table_res.get(code, ExtractorResultDict()),
            llm_res.get(code, ExtractorResultDict()),
        )

    logger.debug("Fusion final results: %s", final)
    return final
