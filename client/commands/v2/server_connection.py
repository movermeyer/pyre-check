# Copyright (c) Facebook, Inc. and its affiliates.
#
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.

import contextlib
import hashlib
import io
import socket
from pathlib import Path
from typing import BinaryIO, Generator, TextIO, Tuple


def get_socket_path(root: Path, log_directory: Path) -> Path:
    """
    Determine where the server socket file is located. We can't directly use
    `log_directory` because of the ~100 character length limit on Unix socket
    file paths.

    Implementation needs to be kept in sync with the `socket_path_of` function
    in `pyre/new_server/start.ml`.
    """
    log_path_digest = hashlib.md5(
        str(log_directory.resolve(strict=False)).encode("utf-8")
    ).hexdigest()
    return root / f"pyre_server_{log_path_digest}.sock"


@contextlib.contextmanager
def connect(socket_path: Path) -> Generator[Tuple[BinaryIO, BinaryIO], None, None]:
    """
    Connect to the socket at given path. Once connected, create an input and
    an output stream from the socket. Both the input stream and the output
    stream are in raw binary mode: read/write APIs of the streams need to use
    `bytes` rather than `str`. The API is intended to be used like this:

    ```
    with connect(socket_path) as (input_stream, output_stream):
        # Read from input_stream and write into output_stream here
        ...
    ```

    Socket creation, connection, and closure will be automatically handled
    inside this context manager. If any of the socket operations fail, raise
    `OSError` just like what the underlying socket API would do.
    """
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as client_socket:
        client_socket.connect(str(socket_path))
        with client_socket.makefile(mode="rb") as input_channel, client_socket.makefile(
            mode="wb"
        ) as output_channel:
            yield (input_channel, output_channel)


@contextlib.contextmanager
def connect_in_text_mode(
    socket_path: Path,
) -> Generator[Tuple[TextIO, TextIO], None, None]:
    """
    This is a line-oriented higher-level API than `connect`. It can be used
    when the caller does not want to deal with the complexity of binary I/O.

    The behavior is the same as `connect`, except the streams that are created
    operates in text mode. Read/write APIs of the streams uses UTF-8 encoded
    `str` instead of `bytes`. Those operations are also line-buffered, meaning
    that the streams will automatically be flushed once the newline character
    is encountered.
    """
    with connect(socket_path) as (input_channel, output_channel):
        yield (
            io.TextIOWrapper(input_channel, encoding="utf-8", line_buffering=True),
            io.TextIOWrapper(output_channel, encoding="utf-8", line_buffering=True),
        )
