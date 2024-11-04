"""
MIT License

Copyright (c) 2017 - Present PythonistaGuild

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""

import inspect
from typing import Any

from twitchio.exceptions import TwitchioException


__all__ = (
    "CommandError",
    "ComponentLoadError",
    "CommandInvokeError",
    "CommandHookError",
    "CommandNotFound",
    "CommandExistsError",
    "PrefixError",
    "InputError",
    "ArgumentError",
    "GuardFailure",
    "ConversionError",
    "BadArgument",
    "MissingRequiredArgument",
    "ModuleAlreadyLoadedError",
    "ModuleLoadFailure",
    "ModuleNotLoadedError",
    "NoEntryPointError",
)


class CommandError(TwitchioException):
    """Base exception for command related errors.

    All commands.ext related exceptions inherit from this class.
    """


class ComponentLoadError(CommandError):
    """Exception raised when a :class:`.commands.Component` fails to load."""


class CommandInvokeError(CommandError):
    def __init__(self, msg: str | None = None, original: Exception | None = None) -> None:
        self.original: Exception | None = original
        super().__init__(msg)


class CommandHookError(CommandInvokeError): ...


class CommandNotFound(CommandError): ...


class CommandExistsError(CommandError): ...


class PrefixError(CommandError): ...


class InputError(CommandError): ...


class ArgumentError(InputError): ...


class UnexpectedQuoteError(ArgumentError):
    def __init__(self, quote: str) -> None:
        self.quote: str = quote
        super().__init__(f"Unexpected quote mark, {quote!r}, in non-quoted string")


class InvalidEndOfQuotedStringError(ArgumentError):
    def __init__(self, char: str) -> None:
        self.char: str = char
        super().__init__(f"Expected space after closing quotation but received {char!r}")


class ExpectedClosingQuoteError(ArgumentError):
    def __init__(self, close_quote: str) -> None:
        self.close_quote: str = close_quote
        super().__init__(f"Expected closing {close_quote}.")


class GuardFailure(CommandError):
    """Exception raised when a :func:`~.commands.guard` fails or blocks a command from executing."""

    def __init__(self, msg: str | None = None, *, guard: Any | None = None) -> None:
        self.guard: Any | None = guard
        super().__init__(msg or "")


class ConversionError(ArgumentError):
    """Base exception for conversion errors."""


class BadArgument(ConversionError):
    """Exception raised when a parsing or conversion failure is encountered on an argument to pass into a command."""

    def __init__(self, msg: str, *, name: str | None = None, value: str | None) -> None:
        self.name: str | None = name
        self.value: str | None = value
        super().__init__(msg)


class MissingRequiredArgument(ArgumentError):
    """Exception raised when parsing a command and a parameter that is required is not encountered."""

    def __init__(self, param: inspect.Parameter) -> None:
        self.param: inspect.Parameter = param
        super().__init__(f'"{param.name}" is a required argument which is missing.')


class ModuleError(TwitchioException):
    """Base exception for module related errors."""


class ModuleLoadFailure(ModuleError):
    """Exception raised when a module failed to load during execution or `setup` entry point."""

    def __init__(self, name: str, exc: Exception) -> None:
        super().__init__(name, exc)


class NoEntryPointError(ModuleError):
    """Exception raised when the module does not have a `setup` entry point coroutine."""

    def __init__(self, msg: str) -> None:
        super().__init__(msg)


class ModuleAlreadyLoadedError(ModuleError):
    """Exception raised when a module has already been loaded."""

    def __init__(self, msg: str) -> None:
        super().__init__(msg)


class ModuleNotLoadedError(ModuleError):
    """Exception raised when a module was not loaded."""

    def __init__(self, msg: str) -> None:
        super().__init__(msg)
