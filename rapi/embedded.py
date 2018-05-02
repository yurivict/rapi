from __future__ import unicode_literals

import sys
from ctypes import c_int, c_size_t, c_char, c_char_p, c_void_p, cast, pointer
from ctypes import POINTER, CFUNCTYPE, PYFUNCTYPE, Structure

from .types import SEXP
from .utils import ccall
from .bootstrap import bootstrap
from . import defaults


callback = {
    "R_Suicide": None,
    "R_ShowMessage": defaults.R_ShowMessage,
    "R_ReadConsole": defaults.R_ReadConsole,
    "R_WriteConsole":  None,
    "R_WriteConsoleEx": defaults.R_WriteConsoleEx,
    "R_ResetConsole": None,
    "R_FlushConsole": None,
    "R_ClearerrConsole": None,
    "R_Busy": defaults.R_Busy,
    "R_CleanUp": None,
    "R_ShowFiles": None,
    "R_ChooseFile": None,
    "R_EditFile": None,
    "R_loadhistory": None,
    "R_savehistory": None,
    "R_addhistory": None,
    "R_EditFiles": None,
    "do_selectlist": None,
    "do_dataentry": None,
    "do_dataviewer": None,
    "R_ProcessEvents": None,
    "R_PolledEvents": defaults.R_PolledEvents,
    "YesNoCancel": defaults.YesNoCancel  # windows only
}

cb_sign = {
    "R_Suicide": CFUNCTYPE(None, c_char_p),
    "R_ShowMessage": CFUNCTYPE(None, c_char_p),
    "R_ReadConsole": CFUNCTYPE(c_int, c_char_p, POINTER(c_char), c_int, c_int),
    "R_WriteConsole":  CFUNCTYPE(None, c_char_p, c_int),
    "R_WriteConsoleEx": CFUNCTYPE(None, c_char_p, c_int, c_int),
    "R_ResetConsole": CFUNCTYPE(None),
    "R_FlushConsole": CFUNCTYPE(None),
    "R_ClearerrConsole": CFUNCTYPE(None),
    "R_Busy": CFUNCTYPE(None, c_int),
    "R_CleanUp": CFUNCTYPE(None, c_int, c_int, c_int),
    "R_ShowFiles": CFUNCTYPE(c_int, c_int, POINTER(c_char_p), POINTER(c_char_p), c_char_p, c_int, c_char_p),
    "R_ChooseFile": CFUNCTYPE(c_int, c_int, POINTER(c_char), c_int),
    "R_EditFile": CFUNCTYPE(c_int, c_char_p),
    "R_loadhistory": CFUNCTYPE(None, SEXP, SEXP, SEXP, SEXP),
    "R_savehistory": CFUNCTYPE(None, SEXP, SEXP, SEXP, SEXP),
    "R_addhistory": CFUNCTYPE(None, SEXP, SEXP, SEXP, SEXP),
    "R_EditFiles": CFUNCTYPE(c_int, POINTER(c_char_p), POINTER(c_char_p), POINTER(c_char_p)),
    "do_selectlist": CFUNCTYPE(SEXP, SEXP, SEXP, SEXP, SEXP),
    "do_dataentry": CFUNCTYPE(None, SEXP, SEXP, SEXP, SEXP),
    "do_dataviewer": CFUNCTYPE(None, SEXP, SEXP, SEXP, SEXP),
    "R_ProcessEvents": CFUNCTYPE(None),
    "R_PolledEvents": CFUNCTYPE(None),
    "YesNoCancel": CFUNCTYPE(c_int, c_char_p)  # windows only
}

callbackptr = []


def set_callback(name, func):
    if name not in callback:
        raise ValueError("method not found")
    callback["name"] = func


def start(libR, arguments=["rapi", "--quiet", "--no-save"], repl=False):
    argn = len(arguments)
    argv = (c_char_p * argn)()
    for i, a in enumerate(arguments):
        argv[i] = c_char_p(a.encode('utf-8'))

    if sys.platform.startswith("win"):
        setup_win32(libR)
        libR.R_set_command_line_arguments(argn, argv)
    else:
        setup_posix(libR)
        libR.Rf_initialize_R(argn, argv)

    libR.setup_Rmainloop()
    bootstrap(libR, rversion=None)
    if repl:
        libR.run_Rmainloop()


def get_cb_ptr(name):
    if callback[name]:
        return cb_sign[name](callback[name])
    else:
        return cast(None, cb_sign[name])


def set_posix_cb_ptr(libR, ptrname, name):
    if callback[name]:
        ptr_show_message = get_cb_ptr(name)
        # prevent gc
        callbackptr.append(ptr_show_message)
        c_void_p.in_dll(libR, ptrname).value = cast(ptr_show_message, c_void_p).value


def setup_posix(libR):

    set_posix_cb_ptr(libR, "ptr_R_Suicide", "R_Suicide")
    set_posix_cb_ptr(libR, "ptr_R_ShowMessage", "R_ShowMessage")
    set_posix_cb_ptr(libR, "ptr_R_ReadConsole", "R_ReadConsole")
    set_posix_cb_ptr(libR, "ptr_R_ReadConsole", "R_ReadConsole")
    set_posix_cb_ptr(libR, "ptr_R_WriteConsole", "R_WriteConsole")

    if callback["R_WriteConsoleEx"]:
        c_void_p.in_dll(libR, 'ptr_R_WriteConsole').value = None
    set_posix_cb_ptr(libR, "ptr_R_WriteConsoleEx", "R_WriteConsoleEx")

    set_posix_cb_ptr(libR, "ptr_R_ResetConsole", "R_ResetConsole")
    set_posix_cb_ptr(libR, "ptr_R_FlushConsole", "R_FlushConsole")
    set_posix_cb_ptr(libR, "ptr_R_ClearerrConsole", "R_ClearerrConsole")
    set_posix_cb_ptr(libR, "ptr_R_Busy", "R_Busy")

    if callback["R_CleanUp"]:
        ptr_R_CleanUp = c_void_p.in_dll(libR, 'ptr_R_CleanUp')
        orig_cleanup = PYFUNCTYPE(None, c_int, c_int, c_int)(ptr_R_CleanUp.value)

        def _handler(save_type, status, runlast):
            callback["R_CleanUp"](save_type, status, runlast)
            orig_cleanup(save_type, status, runlast)

        ptr_new_R_CleanUp = PYFUNCTYPE(None, c_int, c_int, c_int)(_handler)
        callbackptr.append(ptr_new_R_CleanUp)
        ptr_R_CleanUp.value = cast(ptr_new_R_CleanUp, c_void_p).value

    set_posix_cb_ptr(libR, "ptr_R_ShowFiles", "R_ShowFiles")
    set_posix_cb_ptr(libR, "ptr_R_ChooseFile", "R_ChooseFile")
    set_posix_cb_ptr(libR, "ptr_R_EditFile", "R_EditFile")
    set_posix_cb_ptr(libR, "ptr_R_loadhistory", "R_loadhistory")
    set_posix_cb_ptr(libR, "ptr_R_savehistory", "R_savehistory")
    set_posix_cb_ptr(libR, "ptr_R_addhistory", "R_addhistory")
    set_posix_cb_ptr(libR, "ptr_R_EditFiles", "R_EditFiles")
    set_posix_cb_ptr(libR, "ptr_do_selectlist", "do_selectlist")
    set_posix_cb_ptr(libR, "ptr_do_dataentry", "do_dataentry")
    set_posix_cb_ptr(libR, "ptr_do_dataviewer", "do_dataviewer")
    set_posix_cb_ptr(libR, "ptr_R_ProcessEvents", "R_ProcessEvents")
    set_posix_cb_ptr(libR, "ptr_do_dataviewer", "do_dataviewer")
    set_posix_cb_ptr(libR, "R_PolledEvents", "R_PolledEvents")


class RStart(Structure):
    _fields_ = [
        ('R_Quiet', c_int),
        ('R_Slave', c_int),
        ('R_Interactive', c_int),
        ('R_Verbose', c_int),
        ('LoadSiteFile', c_int),
        ('LoadInitFile', c_int),
        ('DebugInitFile', c_int),
        ('RestoreAction', c_int),
        ('SaveAction', c_int),
        ('vsize', c_size_t),
        ('nsize', c_size_t),
        ('max_vsize', c_size_t),
        ('max_nsize', c_size_t),
        ('ppsize', c_size_t),
        ('NoRenviron', c_int),
        ('rhome', POINTER(c_char)),
        ('home', POINTER(c_char)),
        ('ReadConsole', cb_sign["R_ReadConsole"]),
        ('WriteConsole', cb_sign["R_WriteConsole"]),
        ('CallBack', cb_sign["R_PolledEvents"]),
        ('ShowMessage', cb_sign["R_ShowMessage"]),
        ('YesNoCancel', cb_sign["YesNoCancel"]),
        ('Busy', cb_sign["R_Busy"]),
        ('CharacterMode', c_int),
        ('WriteConsoleEx', cb_sign["R_WriteConsoleEx"])
    ]


def setup_win32(libR):
    libR.R_setStartTime()
    rstart = RStart()
    libR.R_DefParams(pointer(rstart))
    rstart.rhome = ccall("get_R_HOME", libR, POINTER(c_char), [])
    rstart.home = ccall("getRUser", libR, POINTER(c_char), [])
    rstart.CharacterMode = 0
    rstart.ReadConsole = get_cb_ptr("R_ReadConsole")
    rstart.WriteConsole = get_cb_ptr("R_WriteConsole")
    rstart.WriteConsoleEx = get_cb_ptr("R_WriteConsoleEx")
    rstart.CallBack = get_cb_ptr("R_PolledEvents")
    rstart.ShowMessage = get_cb_ptr("R_ShowMessage")
    rstart.YesNoCancel = get_cb_ptr("YesNoCancel")
    rstart.Busy = get_cb_ptr("R_Busy")

    rstart.R_Quiet = 1
    rstart.R_Interactive = 1
    rstart.RestoreAction = 0  # or 1
    rstart.SaveAction = 3  # or 5

    libR.R_SetParams(pointer(rstart))

    # prevent gc
    RStart.rstart = rstart
