"""layout name -> renderer registry (see AppSpec.layout)."""

from __future__ import annotations

from . import base, gpay, paypal, paytm, phonepe, tabular

RENDERERS = {
    "gpay": gpay.render,
    "phonepe": phonepe.render,
    "paytm": paytm.render,
    "paypal": paypal.render,
    "tabular": tabular.render,     # cred / bhim / bank
}


def renderer_for(layout: str):
    return RENDERERS[layout]


__all__ = ["RENDERERS", "renderer_for", "base"]