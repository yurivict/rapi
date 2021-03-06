from .interface import rexec, rparse, reval, rprint, rlang, rcall, rsym, rstring, rcopy, robject
from .bootstrap import Machine
from .ipython_hook import register_hook


__all__ = [
    "rexec",
    "rparse",
    "reval",
    "rprint",
    "rlang",
    "rcall",
    "rsym",
    "rstring",
    "rcopy",
    "robject"
]

__version__ = '0.1.2'


def start(
        arguments=[
            "rapi",
            "--quiet",
            "--no-save",
            "--no-restore"
        ],
        verbose=True):

    m = Machine(verbose=verbose)
    m.start(arguments=arguments)
    register_hook()


def get_machine():
    return Machine.instance
